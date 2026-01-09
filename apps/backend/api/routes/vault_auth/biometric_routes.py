"""
Vault Auth - Biometric Routes

WebAuthn/Touch ID authentication endpoints.
"""

import base64
import hashlib
import logging
import secrets
import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from api.auth_middleware import get_current_user, User
from api.config import get_settings
from api.rate_limiter import get_client_ip
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.services.webauthn_verify import verify_assertion
from api.utils import sanitize_for_log, get_user_id

from api.routes.vault_auth_utils import (
    BiometricSetupRequest,
    BiometricUnlockRequest,
    UnlockResponse,
    ChallengeResponse,
    generate_challenge,
    consume_challenge,
    cleanup_expired_challenges,
    derive_kek_from_passphrase,
    wrap_kek,
    unwrap_kek,
    migrate_xor_to_aes_kw,
    CHALLENGE_TTL_SECONDS,
)

# Import helpers for non-patchable operations (session, DB path)
from api.routes.vault_auth import helpers

logger = logging.getLogger(__name__)


def _get_pkg():
    """Runtime import to allow test patching at package level."""
    from api.routes import vault_auth as pkg
    return pkg

# WebAuthn configuration - loaded from settings (supports env vars)
_settings = get_settings()
WEBAUTHN_RP_ID = _settings.webauthn_rp_id
WEBAUTHN_ORIGIN = _settings.webauthn_origin

router = APIRouter()


@router.post(
    "/setup/biometric",
    response_model=SuccessResponse[UnlockResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Setup biometric unlock",
    description="Configure biometric (Touch ID/WebAuthn) authentication for vault"
)
async def setup_biometric(
    request: BiometricSetupRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UnlockResponse]:
    """
    Setup biometric unlock for vault

    Flow:
    1. Derive KEK from passphrase (client-side, sent here)
    2. Create WebAuthn credential (client-side)
    3. Wrap KEK with credential ID
    4. Store wrapped KEK reference in vault.db

    Note: Passphrase should NOT be sent over network in production.
    This is a demo - client should derive KEK locally and send only wrapped KEK.
    """
    try:
        user_id = get_user_id(current_user)

        logger.info(
            "Biometric setup request",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(request.vault_id)}
        )

        # Generate salt for real vault
        salt_real = secrets.token_bytes(32)

        # Derive KEK from passphrase
        kek_real = derive_kek_from_passphrase(request.passphrase, salt_real)

        # Wrap KEK with WebAuthn credential ID (as wrap key) using AES-KW
        wrap_key = hashlib.sha256(request.webauthn_credential_id.encode()).digest()
        wrapped_kek_real = wrap_kek(kek_real, wrap_key, method="aes_kw")

        # Store in database
        with sqlite3.connect(str(helpers.VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Check if metadata already exists
            cursor.execute("""
                SELECT id FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, request.vault_id))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET webauthn_credential_id = ?,
                        webauthn_public_key = ?,
                        salt_real = ?,
                        wrapped_kek_real = ?,
                        wrap_method = ?,
                        updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (
                    request.webauthn_credential_id,
                    request.webauthn_public_key,
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    "aes_kw",
                    datetime.now().isoformat(),
                    user_id,
                    request.vault_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO vault_auth_metadata (
                        id, user_id, vault_id,
                        webauthn_credential_id, webauthn_public_key,
                        salt_real, wrapped_kek_real,
                        wrap_method,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    user_id,
                    request.vault_id,
                    request.webauthn_credential_id,
                    request.webauthn_public_key,
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    "aes_kw",
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()

        # Create session
        session_id = helpers.create_session(user_id, request.vault_id, kek_real, 'real')

        logger.info("Biometric setup successful", extra={"user_id": user_id})

        return SuccessResponse(
            data=UnlockResponse(
                success=True,
                session_id=session_id,
                message="Biometric unlock configured successfully"
            ),
            message="Biometric authentication configured"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Biometric setup failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to setup biometric unlock"
            ).model_dump()
        )


@router.post(
    "/challenge/biometric",
    response_model=SuccessResponse[ChallengeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get WebAuthn challenge",
    description="Request a challenge for biometric unlock. Must be used within 5 minutes."
)
async def get_biometric_challenge(
    vault_id: str = Query(..., description="Vault ID to unlock"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[ChallengeResponse]:
    """
    Generate and return a WebAuthn challenge for biometric unlock.

    The challenge must be signed by the client's biometric credential
    and submitted to /unlock/biometric within 5 minutes.
    """
    user_id = get_user_id(current_user)

    # Cleanup expired challenges periodically
    cleanup_expired_challenges()

    # Generate new challenge
    challenge_bytes = generate_challenge(user_id, vault_id)
    challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=').decode('ascii')

    logger.info(
        "Generated biometric challenge",
        extra={"user_id": user_id, "vault_id": sanitize_for_log(vault_id)}
    )

    return SuccessResponse(
        data=ChallengeResponse(
            challenge=challenge_b64,
            timeout=CHALLENGE_TTL_SECONDS * 1000  # Convert to milliseconds
        ),
        message="Challenge generated"
    )


@router.post(
    "/unlock/biometric",
    response_model=SuccessResponse[UnlockResponse],
    status_code=status.HTTP_200_OK,
    summary="Unlock vault with biometric",
    description="Unlock vault using biometric authentication (Touch ID/WebAuthn). Rate limited: 5 attempts per 5 minutes."
)
async def unlock_biometric(
    req: BiometricUnlockRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UnlockResponse]:
    """
    Unlock vault with biometric (Touch ID via WebAuthn)

    Flow:
    1. Verify WebAuthn assertion
    2. Unwrap KEK using credential ID
    3. Create in-memory vault session
    4. Return success (without disclosing vault_type)

    Rate limited: 5 attempts per 5 minutes
    """
    user_id = get_user_id(current_user)
    client_ip = get_client_ip(request)

    # Rate limit check - use runtime import for test patching compatibility
    pkg = _get_pkg()
    if not pkg._check_rate_limit(user_id, req.vault_id, client_ip):
        pkg._record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Too many unlock attempts. Please wait 5 minutes."
            ).model_dump()
        )

    try:
        logger.info(
            "Biometric unlock attempt",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(req.vault_id)}
        )

        # Fetch vault auth metadata
        with sqlite3.connect(str(helpers.VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT webauthn_credential_id, webauthn_public_key, wrapped_kek_real, salt_real, wrap_method, webauthn_counter
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, req.vault_id))

            row = cursor.fetchone()

            if not row:
                pkg._record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Biometric unlock not configured for this vault"
                    ).model_dump()
                )

            credential_id, public_key, wrapped_kek_hex, salt_hex, wrap_method, stored_sign_count = row
            wrap_method = wrap_method or "xor_legacy"
            stored_sign_count = stored_sign_count or 0

        # Verify WebAuthn assertion with challenge validation
        challenge = consume_challenge(user_id, req.vault_id)
        if not challenge:
            pkg._record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="No valid challenge found. Please request a new challenge."
                ).model_dump()
            )

        try:
            # Verify the WebAuthn assertion cryptographically
            verified = verify_assertion(
                assert_response=req.webauthn_assertion,
                rp_id=WEBAUTHN_RP_ID,
                origin=WEBAUTHN_ORIGIN,
                public_key_pem=public_key,
                challenge=challenge,
                credential_id=credential_id,
                current_sign_count=stored_sign_count
            )

            # Update the sign count in DB to prevent replay attacks
            with sqlite3.connect(str(helpers.VAULT_DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET webauthn_counter = ?, updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (verified.sign_count, datetime.now().isoformat(), user_id, req.vault_id))
                conn.commit()

            logger.info(
                "WebAuthn assertion verified",
                extra={
                    "user_id": user_id,
                    "credential_id": credential_id[:16] + "...",
                    "old_sign_count": stored_sign_count,
                    "new_sign_count": verified.sign_count
                }
            )
        except Exception as e:
            pkg._record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
            logger.warning(f"WebAuthn verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="Biometric verification failed"
                ).model_dump()
            )

        # Unwrap KEK using the stored wrap method
        wrap_key = hashlib.sha256(credential_id.encode()).digest()
        wrapped_kek = bytes.fromhex(wrapped_kek_hex)
        kek_real = unwrap_kek(wrapped_kek, wrap_key, method=wrap_method)

        # Create session
        session_id = helpers.create_session(user_id, req.vault_id, kek_real, 'real')

        pkg._record_unlock_attempt(user_id, req.vault_id, True, 'biometric')
        logger.info("Biometric unlock successful", extra={"user_id": user_id})

        # Automatic migration: Upgrade XOR legacy vaults to AES-KW
        if wrap_method == "xor_legacy":
            migrate_xor_to_aes_kw(
                user_id=user_id,
                vault_id=req.vault_id,
                kek=kek_real,
                wrap_key=wrap_key,
                vault_type="real",
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
        pkg._record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
        logger.error("Biometric unlock failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unlock vault"
            ).model_dump()
        )
