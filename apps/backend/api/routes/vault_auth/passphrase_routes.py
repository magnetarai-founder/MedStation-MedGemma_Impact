"""
Vault Auth - Passphrase Routes

Password-based vault unlock and dual-password (decoy) setup.
"""

import hashlib
import logging
import secrets
import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from api.auth_middleware import get_current_user, User
from api.rate_limiter import get_client_ip
from api.routes.schemas import SuccessResponse
from api.errors import http_400, http_404, http_429, http_500
from api.utils import sanitize_for_log, get_user_id

from api.routes.vault_auth_utils import (
    DualPasswordSetupRequest,
    UnlockResponse,
    derive_kek_from_passphrase,
    wrap_kek,
    unwrap_kek,
    migrate_xor_to_aes_kw,
)

from api.routes.vault_auth import helpers

logger = logging.getLogger(__name__)


def _get_pkg():
    """Runtime import to allow test patching at package level."""
    from api.routes import vault_auth as pkg
    return pkg


router = APIRouter()


@router.post(
    "/setup/dual-password",
    response_model=SuccessResponse[UnlockResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Setup dual-password mode",
    description="Configure dual-password vault (sensitive + decoy for plausible deniability)"
)
async def setup_dual_password(
    request: DualPasswordSetupRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UnlockResponse]:
    """
    Setup dual-password mode (sensitive vs unsensitive vaults)

    Flow:
    1. Validate passwords differ
    2. Derive KEKs for both sensitive and unsensitive vaults
    3. Store both wrapped KEKs
    4. Optionally pre-populate unsensitive vault with benign files

    Security:
    - No indicator of which vault is active
    - Both passwords derive valid KEKs
    - Switching requires logout
    - Never discloses which password was used (plausible deniability)
    """
    try:
        if request.password_sensitive == request.password_unsensitive:
            raise http_400("Sensitive and decoy passwords must differ")

        user_id = get_user_id(current_user)

        logger.info(
            "Dual-password setup request",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(request.vault_id)}
        )

        # Generate salts
        salt_sensitive = secrets.token_bytes(32)
        salt_unsensitive = secrets.token_bytes(32)

        # Derive KEKs
        kek_sensitive = derive_kek_from_passphrase(request.password_sensitive, salt_sensitive)
        kek_unsensitive = derive_kek_from_passphrase(request.password_unsensitive, salt_unsensitive)

        # Wrap KEKs using AES-KW with password-derived wrap keys
        wrap_key_sensitive = hashlib.sha256(request.password_sensitive.encode()).digest()
        wrap_key_unsensitive = hashlib.sha256(request.password_unsensitive.encode()).digest()

        wrapped_kek_sensitive = wrap_kek(kek_sensitive, wrap_key_sensitive, method="aes_kw")
        wrapped_kek_unsensitive = wrap_kek(kek_unsensitive, wrap_key_unsensitive, method="aes_kw")

        # Store in database
        with sqlite3.connect(str(helpers.VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, request.vault_id))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET salt_real = ?,
                        wrapped_kek_real = ?,
                        salt_decoy = ?,
                        wrapped_kek_decoy = ?,
                        decoy_enabled = 1,
                        wrap_method = ?,
                        updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (
                    salt_sensitive.hex(),
                    wrapped_kek_sensitive.hex(),
                    salt_unsensitive.hex(),
                    wrapped_kek_unsensitive.hex(),
                    "aes_kw",
                    datetime.now().isoformat(),
                    user_id,
                    request.vault_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO vault_auth_metadata (
                        id, user_id, vault_id,
                        salt_real, wrapped_kek_real,
                        salt_decoy, wrapped_kek_decoy,
                        decoy_enabled,
                        wrap_method,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    user_id,
                    request.vault_id,
                    salt_sensitive.hex(),
                    wrapped_kek_sensitive.hex(),
                    salt_unsensitive.hex(),
                    wrapped_kek_unsensitive.hex(),
                    "aes_kw",
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()

        # Create session with sensitive vault
        session_id = helpers.create_session(user_id, request.vault_id, kek_sensitive, 'real')

        logger.info("Dual-password setup successful", extra={"user_id": user_id})

        return SuccessResponse(
            data=UnlockResponse(
                success=True,
                session_id=session_id,
                message="Dual-password vault configured successfully"
            ),
            message="Dual-password mode configured"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Dual-password setup failed", exc_info=True)
        raise http_500("Failed to setup dual-password mode")


# Backward compatibility alias
@router.post("/setup/decoy", response_model=SuccessResponse[UnlockResponse], include_in_schema=False)
async def setup_decoy_legacy(
    request: DualPasswordSetupRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UnlockResponse]:
    """Legacy endpoint - redirects to /setup/dual-password"""
    return await setup_dual_password(request, current_user)


@router.post(
    "/unlock/passphrase",
    response_model=SuccessResponse[UnlockResponse],
    status_code=status.HTTP_200_OK,
    summary="Unlock vault with passphrase",
    description="Unlock vault using passphrase. Supports dual-password mode. Rate limited: 5 attempts per 5 minutes."
)
async def unlock_passphrase(
    vault_id: str = Query(..., description="Vault UUID"),
    passphrase: str = Query(..., description="Vault passphrase"),
    request: Request = None,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UnlockResponse]:
    """
    Unlock vault with passphrase

    Supports both single-password and decoy mode:
    - If decoy enabled: try both KEKs, mount whichever decrypts cleanly
    - If single-password: use real KEK only

    Rate limited: 5 attempts per 5 minutes
    """
    user_id = get_user_id(current_user)
    client_ip = get_client_ip(request)

    # Rate limit check - use runtime import for test patching compatibility
    pkg = _get_pkg()
    if not pkg._check_rate_limit(user_id, vault_id, client_ip):
        pkg._record_unlock_attempt(user_id, vault_id, False, 'passphrase')
        raise http_429("Too many unlock attempts. Please wait 5 minutes.")

    try:
        logger.info(
            "Passphrase unlock attempt",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(vault_id)}
        )

        # Fetch vault auth metadata
        with sqlite3.connect(str(helpers.VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT salt_real, wrapped_kek_real, salt_decoy, wrapped_kek_decoy, decoy_enabled, wrap_method
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, vault_id))

            row = cursor.fetchone()

            if not row:
                pkg._record_unlock_attempt(user_id, vault_id, False, 'passphrase')
                raise http_404("Vault not configured", resource="vault")

            salt_real_hex, wrapped_kek_real_hex, salt_decoy_hex, wrapped_kek_decoy_hex, decoy_enabled, wrap_method = row
            wrap_method = wrap_method or "xor_legacy"

        # Derive KEK from passphrase
        salt_real = bytes.fromhex(salt_real_hex) if salt_real_hex else None

        if not salt_real:
            pkg._record_unlock_attempt(user_id, vault_id, False, 'passphrase')
            raise http_400("Vault not properly configured")

        # Try real vault first
        kek_attempt = derive_kek_from_passphrase(passphrase, salt_real)
        wrap_key = hashlib.sha256(passphrase.encode()).digest()
        wrapped_kek_real = bytes.fromhex(wrapped_kek_real_hex)
        kek_real = unwrap_kek(wrapped_kek_real, wrap_key, method=wrap_method)

        vault_type = 'real'
        kek = kek_real

        # If decoy enabled, check if passphrase matches decoy
        if decoy_enabled and salt_decoy_hex and wrapped_kek_decoy_hex:
            salt_decoy = bytes.fromhex(salt_decoy_hex)
            kek_attempt_decoy = derive_kek_from_passphrase(passphrase, salt_decoy)
            wrap_key_decoy = hashlib.sha256(passphrase.encode()).digest()
            wrapped_kek_decoy = bytes.fromhex(wrapped_kek_decoy_hex)
            kek_decoy = unwrap_kek(wrapped_kek_decoy, wrap_key_decoy, method=wrap_method)

            if kek_attempt_decoy == kek_decoy:
                vault_type = 'decoy'
                kek = kek_decoy

        # Create session
        session_id = helpers.create_session(user_id, vault_id, kek, vault_type)

        pkg._record_unlock_attempt(user_id, vault_id, True, 'passphrase')
        logger.info("Passphrase unlock successful", extra={"user_id": user_id})

        # Automatic migration: Upgrade XOR legacy vaults to AES-KW
        if wrap_method == "xor_legacy":
            migrate_xor_to_aes_kw(
                user_id=user_id,
                vault_id=vault_id,
                kek=kek,
                wrap_key=wrap_key,
                vault_type=vault_type,
                vault_db_path=helpers.VAULT_DB_PATH
            )

        return SuccessResponse(
            data=UnlockResponse(
                success=True,
                session_id=session_id,
                message="Vault unlocked successfully"
            ),
            message="Vault unlocked"
        )

    except HTTPException:
        raise
    except Exception as e:
        pkg._record_unlock_attempt(user_id, vault_id, False, 'passphrase')
        logger.error("Passphrase unlock failed", exc_info=True)
        raise http_500("Failed to unlock vault")
