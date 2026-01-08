"""
Vault Authentication Routes

Handles biometric (WebAuthn/Touch ID) and decoy mode authentication for vault unlock.

Security model:
- KEK (Key Encryption Key) derived client-side via PBKDF2
- KEK wrapped with WebAuthn credential ID or passphrase
- Server stores only wrapped KEKs, never plaintext keys
- Rate limiting on unlock attempts (5 attempts → 5-minute lockout)
- Plausible deniability via dual-password mode (sensitive vs decoy vaults)

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import base64
import hashlib
import logging
import secrets
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from api.auth_middleware import get_current_user, User
from api.config import get_settings
from api.config_paths import get_config_paths
from api.rate_limiter import rate_limiter, get_client_ip
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.services.webauthn_verify import verify_assertion
from api.utils import sanitize_for_log, get_user_id

# Import extracted utilities
from api.routes.vault_auth_utils import (
    # Models
    BiometricSetupRequest,
    BiometricUnlockRequest,
    DualPasswordSetupRequest,
    UnlockResponse,
    ChallengeResponse,
    # Challenges
    generate_challenge,
    get_challenge,
    consume_challenge,
    cleanup_expired_challenges,
    CHALLENGE_TTL_SECONDS,
    webauthn_challenges,  # Re-exported for test compatibility
    # Crypto
    derive_kek_from_passphrase,
    wrap_kek,
    unwrap_kek,
    migrate_xor_to_aes_kw,
    PBKDF2_ITERATIONS,
    crypto_wrap_key,
    crypto_unwrap_key,
    # Database
    init_vault_auth_db,
    # Backwards compatibility aliases (underscore-prefixed)
    _generate_challenge,
    _get_challenge,
    _consume_challenge,
    _cleanup_expired_challenges,
    _derive_kek_from_passphrase,
    _wrap_kek,
    _unwrap_kek,
    _migrate_xor_to_aes_kw,
)

logger = logging.getLogger(__name__)

# WebAuthn configuration - loaded from settings (supports env vars)
_settings = get_settings()
WEBAUTHN_RP_ID = _settings.webauthn_rp_id  # Relying Party ID (domain)
WEBAUTHN_ORIGIN = _settings.webauthn_origin  # Expected origin

router = APIRouter(prefix="/api/v1/vault", tags=["vault-auth"])

# Database path
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


def _init_vault_auth_db() -> None:
    """Initialize vault auth database using module-level VAULT_DB_PATH.

    This wrapper exists for test compatibility - tests patch VAULT_DB_PATH
    and call this no-argument function.
    """
    init_vault_auth_db(VAULT_DB_PATH)


# In-memory session storage for unlocked vaults (KEK is kept in memory)
# Format: {(user_id, vault_id): {'kek': bytes, 'vault_type': str, 'unlocked_at': timestamp}}
vault_sessions: Dict[tuple, Dict[str, Any]] = {}

# Rate limiting for unlock attempts
UNLOCK_RATE_LIMIT = 5  # attempts
UNLOCK_WINDOW_SECONDS = 300  # 5 minutes

# Initialize database on module load
init_vault_auth_db(VAULT_DB_PATH)


# ===== Helper Functions =====

def _check_rate_limit(user_id: str, vault_id: str, client_ip: str) -> bool:
    """Check unlock rate limit (5 attempts per 5 minutes)"""
    rate_key = f"vault_unlock:{user_id}:{vault_id}:{client_ip}"
    return rate_limiter.check_rate_limit(rate_key, max_requests=UNLOCK_RATE_LIMIT, window_seconds=UNLOCK_WINDOW_SECONDS)


def _record_unlock_attempt(user_id: str, vault_id: str, success: bool, method: str) -> None:
    """Record unlock attempt for audit"""
    with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vault_unlock_attempts (id, user_id, vault_id, attempt_time, success, method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            secrets.token_urlsafe(16),
            user_id,
            vault_id,
            datetime.now().isoformat(),
            1 if success else 0,
            method
        ))
        conn.commit()


# ===== Endpoints =====

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
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
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
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(user_id, request.vault_id)] = {
            'kek': kek_real,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

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

    # Rate limit check
    if not _check_rate_limit(user_id, req.vault_id, client_ip):
        _record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
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
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT webauthn_credential_id, webauthn_public_key, wrapped_kek_real, salt_real, wrap_method, webauthn_counter
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, req.vault_id))

            row = cursor.fetchone()

            if not row:
                _record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
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
            _record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
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
            with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
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
            _record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
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
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(user_id, req.vault_id)] = {
            'kek': kek_real,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        _record_unlock_attempt(user_id, req.vault_id, True, 'biometric')
        logger.info("Biometric unlock successful", extra={"user_id": user_id})

        # Automatic migration: Upgrade XOR legacy vaults to AES-KW
        if wrap_method == "xor_legacy":
            migrate_xor_to_aes_kw(
                user_id=user_id,
                vault_id=req.vault_id,
                kek=kek_real,
                wrap_key=wrap_key,
                vault_type="real",
                vault_db_path=VAULT_DB_PATH
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
        _record_unlock_attempt(user_id, req.vault_id, False, 'biometric')
        logger.error("Biometric unlock failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unlock vault"
            ).model_dump()
        )


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Sensitive and decoy passwords must differ"
                ).model_dump()
            )

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
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
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
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(user_id, request.vault_id)] = {
            'kek': kek_sensitive,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to setup dual-password mode"
            ).model_dump()
        )


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

    if not _check_rate_limit(user_id, vault_id, client_ip):
        _record_unlock_attempt(user_id, vault_id, False, 'passphrase')
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Too many unlock attempts. Please wait 5 minutes."
            ).model_dump()
        )

    try:
        logger.info(
            "Passphrase unlock attempt",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(vault_id)}
        )

        # Fetch vault auth metadata
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT salt_real, wrapped_kek_real, salt_decoy, wrapped_kek_decoy, decoy_enabled, wrap_method
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (user_id, vault_id))

            row = cursor.fetchone()

            if not row:
                _record_unlock_attempt(user_id, vault_id, False, 'passphrase')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Vault not configured"
                    ).model_dump()
                )

            salt_real_hex, wrapped_kek_real_hex, salt_decoy_hex, wrapped_kek_decoy_hex, decoy_enabled, wrap_method = row
            wrap_method = wrap_method or "xor_legacy"

        # Derive KEK from passphrase
        salt_real = bytes.fromhex(salt_real_hex) if salt_real_hex else None

        if not salt_real:
            _record_unlock_attempt(user_id, vault_id, False, 'passphrase')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Vault not properly configured"
                ).model_dump()
            )

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
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(user_id, vault_id)] = {
            'kek': kek,
            'vault_type': vault_type,
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        _record_unlock_attempt(user_id, vault_id, True, 'passphrase')
        logger.info("Passphrase unlock successful", extra={"user_id": user_id})

        # Automatic migration: Upgrade XOR legacy vaults to AES-KW
        if wrap_method == "xor_legacy":
            migrate_xor_to_aes_kw(
                user_id=user_id,
                vault_id=vault_id,
                kek=kek,
                wrap_key=wrap_key,
                vault_type=vault_type,
                vault_db_path=VAULT_DB_PATH
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
        _record_unlock_attempt(user_id, vault_id, False, 'passphrase')
        logger.error("Passphrase unlock failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unlock vault"
            ).model_dump()
        )


@router.get(
    "/session/status",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Check session status",
    description="Check if vault is unlocked in current session (sessions expire after 1 hour)"
)
async def get_session_status(
    vault_id: str = Query(..., description="Vault UUID"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Check if vault is unlocked in current session"""
    user_id = get_user_id(current_user)
    session_key = (user_id, vault_id)

    if session_key in vault_sessions:
        session = vault_sessions[session_key]

        # Check if session is still valid (< 1 hour old)
        if time.time() - session['unlocked_at'] < 3600:
            return SuccessResponse(
                data={"unlocked": True, "session_id": session['session_id']},
                message="Vault is unlocked"
            )
        else:
            # Session expired
            del vault_sessions[session_key]

    return SuccessResponse(
        data={"unlocked": False, "session_id": None},
        message="Vault is locked"
    )


@router.post(
    "/session/lock",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Lock vault",
    description="Lock vault and clear session (KEK removed from memory)"
)
async def lock_vault(
    vault_id: str = Query(..., description="Vault UUID"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Lock vault (clear session)"""
    user_id = get_user_id(current_user)
    session_key = (user_id, vault_id)

    if session_key in vault_sessions:
        del vault_sessions[session_key]
        logger.info("Vault locked", extra={"user_id": user_id, "vault_id": vault_id})

    return SuccessResponse(
        data={"success": True},
        message="Vault locked successfully"
    )
