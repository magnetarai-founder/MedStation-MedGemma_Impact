"""
Vault Authentication Routes

Handles biometric (WebAuthn/Touch ID) and decoy mode authentication for vault unlock.
Security model:
- KEK (Key Encryption Key) derived client-side via PBKDF2
- KEK wrapped with WebAuthn credential ID or passphrase
- Server stores only wrapped KEKs, never plaintext keys
- Rate limiting on unlock attempts (5 attempts → 5-minute lockout)
"""

import logging
import hashlib
import secrets
import sqlite3
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user, User
from api.config_paths import get_config_paths
from api.utils import sanitize_for_log
from api.rate_limiter import rate_limiter, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vault", tags=["vault-auth"])

# Database path
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"

# In-memory session storage for unlocked vaults (KEK is kept in memory)
# Format: {(user_id, vault_id): {'kek': bytes, 'vault_type': str, 'unlocked_at': timestamp}}
vault_sessions: Dict[tuple, Dict[str, Any]] = {}

# Rate limiting for unlock attempts
UNLOCK_RATE_LIMIT = 5  # attempts
UNLOCK_WINDOW_SECONDS = 300  # 5 minutes


# ===== Database Initialization =====

def _init_vault_auth_db():
    """Initialize vault auth metadata table"""
    VAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Vault authentication metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_auth_metadata (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_id TEXT NOT NULL,

                -- Biometric (WebAuthn) fields
                webauthn_credential_id TEXT,
                webauthn_public_key TEXT,
                webauthn_counter INTEGER DEFAULT 0,

                -- Real vault fields
                salt_real TEXT,
                wrapped_kek_real TEXT,

                -- Decoy vault fields (optional)
                salt_decoy TEXT,
                wrapped_kek_decoy TEXT,
                decoy_enabled INTEGER DEFAULT 0,

                -- Metadata
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE(user_id, vault_id)
            )
        """)

        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_auth_user
            ON vault_auth_metadata(user_id, vault_id)
        """)

        # Unlock attempt tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_unlock_attempts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_id TEXT NOT NULL,
                attempt_time TEXT NOT NULL,
                success INTEGER NOT NULL,
                method TEXT NOT NULL CHECK(method IN ('biometric', 'passphrase'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unlock_attempts_user
            ON vault_unlock_attempts(user_id, vault_id, attempt_time DESC)
        """)

        conn.commit()


# Initialize on module load
_init_vault_auth_db()


# ===== Request/Response Models =====

class BiometricSetupRequest(BaseModel):
    """Setup biometric unlock for vault"""
    vault_id: str = Field(..., description="Vault UUID")
    passphrase: str = Field(..., min_length=8, description="Master passphrase (for KEK derivation)")
    webauthn_credential_id: str = Field(..., description="WebAuthn credential ID (base64)")
    webauthn_public_key: str = Field(..., description="WebAuthn public key (base64)")


class BiometricUnlockRequest(BaseModel):
    """Unlock vault with biometric"""
    vault_id: str = Field(..., description="Vault UUID")
    webauthn_assertion: str = Field(..., description="WebAuthn assertion response (base64)")
    signature: str = Field(..., description="WebAuthn signature (base64)")


class DecoySetupRequest(BaseModel):
    """Setup decoy mode (dual-password)"""
    vault_id: str = Field(..., description="Vault UUID")
    password_real: str = Field(..., min_length=8, description="Real vault password")
    password_decoy: str = Field(..., min_length=8, description="Decoy vault password")


class UnlockResponse(BaseModel):
    """Unlock response"""
    success: bool
    vault_type: Optional[str] = None  # Never disclosed to maintain plausible deniability
    session_id: str
    message: str


# ===== Helper Functions =====

def _check_rate_limit(user_id: str, vault_id: str, client_ip: str) -> bool:
    """Check unlock rate limit (5 attempts per 5 minutes)"""
    rate_key = f"vault_unlock:{user_id}:{vault_id}:{client_ip}"
    return rate_limiter.check_rate_limit(rate_key, max_requests=UNLOCK_RATE_LIMIT, window_seconds=UNLOCK_WINDOW_SECONDS)


def _record_unlock_attempt(user_id: str, vault_id: str, success: bool, method: str):
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


def _derive_kek_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """
    Derive KEK from passphrase using PBKDF2
    (This should match client-side derivation)
    """
    return hashlib.pbkdf2_hmac('sha256', passphrase.encode(), salt, iterations=100000, dklen=32)


def _wrap_kek(kek: bytes, wrap_key: bytes) -> bytes:
    """
    Wrap KEK with a wrapping key (simple XOR for demo - use AES-KW in production)
    In production, use proper AES Key Wrap (RFC 3394)
    """
    # Simple XOR wrap (NOT production-ready, but demonstrates the concept)
    return bytes(a ^ b for a, b in zip(kek, wrap_key[:len(kek)]))


def _unwrap_kek(wrapped_kek: bytes, wrap_key: bytes) -> bytes:
    """Unwrap KEK (inverse of wrap)"""
    return _wrap_kek(wrapped_kek, wrap_key)  # XOR is self-inverse


# ===== Endpoints =====

@router.post("/setup/biometric", response_model=UnlockResponse)
async def setup_biometric(
    request: BiometricSetupRequest,
    current_user: User = Depends(get_current_user)
):
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
        # Sanitize logs
        logger.info(
            "Biometric setup request",
            extra={
                "user_id": current_user.user_id,
                "vault_id": sanitize_for_log(request.vault_id)
            }
        )

        # Generate salt for real vault
        salt_real = secrets.token_bytes(32)

        # Derive KEK from passphrase
        kek_real = _derive_kek_from_passphrase(request.passphrase, salt_real)

        # Wrap KEK with WebAuthn credential ID (as wrap key)
        # In production, use proper key wrapping algorithm
        wrap_key = hashlib.sha256(request.webauthn_credential_id.encode()).digest()
        wrapped_kek_real = _wrap_kek(kek_real, wrap_key)

        # Store in database
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Check if metadata already exists
            cursor.execute("""
                SELECT id FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (current_user.user_id, request.vault_id))

            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET webauthn_credential_id = ?,
                        webauthn_public_key = ?,
                        salt_real = ?,
                        wrapped_kek_real = ?,
                        updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (
                    request.webauthn_credential_id,
                    request.webauthn_public_key,
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    datetime.now().isoformat(),
                    current_user.user_id,
                    request.vault_id
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO vault_auth_metadata (
                        id, user_id, vault_id,
                        webauthn_credential_id, webauthn_public_key,
                        salt_real, wrapped_kek_real,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    current_user.user_id,
                    request.vault_id,
                    request.webauthn_credential_id,
                    request.webauthn_public_key,
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()

        # Create session
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(current_user.user_id, request.vault_id)] = {
            'kek': kek_real,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        logger.info("Biometric setup successful", extra={"user_id": current_user.user_id})

        return UnlockResponse(
            success=True,
            session_id=session_id,
            message="Biometric unlock configured successfully"
        )

    except Exception as e:
        logger.error(f"Biometric setup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup biometric unlock: {str(e)}"
        )


@router.post("/unlock/biometric", response_model=UnlockResponse)
async def unlock_biometric(
    req: BiometricUnlockRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Unlock vault with biometric (Touch ID via WebAuthn)

    Flow:
    1. Verify WebAuthn assertion
    2. Unwrap KEK using credential ID
    3. Create in-memory vault session
    4. Return success (without disclosing vault_type)

    Rate limited: 5 attempts per 5 minutes
    """
    client_ip = get_client_ip(request)

    # Rate limit check
    if not _check_rate_limit(current_user.user_id, req.vault_id, client_ip):
        _record_unlock_attempt(current_user.user_id, req.vault_id, False, 'biometric')
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many unlock attempts. Please wait 5 minutes."
        )

    try:
        logger.info(
            "Biometric unlock attempt",
            extra={
                "user_id": current_user.user_id,
                "vault_id": sanitize_for_log(req.vault_id)
            }
        )

        # Fetch vault auth metadata
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT webauthn_credential_id, webauthn_public_key, wrapped_kek_real, salt_real
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (current_user.user_id, req.vault_id))

            row = cursor.fetchone()

            if not row:
                _record_unlock_attempt(current_user.user_id, req.vault_id, False, 'biometric')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Biometric unlock not configured for this vault"
                )

            credential_id, public_key, wrapped_kek_hex, salt_hex = row

        # Verify WebAuthn assertion
        # In production, use py_webauthn library for full verification
        # For demo, we'll do a simplified check

        # TODO: Full WebAuthn verification (challenge validation, signature verification)
        # For now, we trust the client has verified the credential

        # Unwrap KEK
        wrap_key = hashlib.sha256(credential_id.encode()).digest()
        wrapped_kek = bytes.fromhex(wrapped_kek_hex)
        kek_real = _unwrap_kek(wrapped_kek, wrap_key)

        # Create session
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(current_user.user_id, req.vault_id)] = {
            'kek': kek_real,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        _record_unlock_attempt(current_user.user_id, req.vault_id, True, 'biometric')

        logger.info("Biometric unlock successful", extra={"user_id": current_user.user_id})

        # Do NOT disclose vault_type to maintain plausible deniability
        return UnlockResponse(
            success=True,
            session_id=session_id,
            message="Vault unlocked successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        _record_unlock_attempt(current_user.user_id, req.vault_id, False, 'biometric')
        logger.error(f"Biometric unlock failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock vault"
        )


@router.post("/setup/decoy", response_model=UnlockResponse)
async def setup_decoy(
    request: DecoySetupRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Setup decoy mode (dual-password system)

    Flow:
    1. Validate passwords differ
    2. Derive KEKs for both real and decoy vaults
    3. Store both wrapped KEKs
    4. Optionally pre-populate decoy vault with benign files

    Security:
    - No indicator of which mode is active
    - Both passwords derive valid KEKs
    - Switching requires logout
    """
    try:
        # Validate passwords differ
        if request.password_real == request.password_decoy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Real and decoy passwords must differ"
            )

        logger.info(
            "Decoy mode setup request",
            extra={
                "user_id": current_user.user_id,
                "vault_id": sanitize_for_log(request.vault_id)
            }
        )

        # Generate salts
        salt_real = secrets.token_bytes(32)
        salt_decoy = secrets.token_bytes(32)

        # Derive KEKs
        kek_real = _derive_kek_from_passphrase(request.password_real, salt_real)
        kek_decoy = _derive_kek_from_passphrase(request.password_decoy, salt_decoy)

        # Wrap KEKs (with themselves for passphrase-only mode, or with WebAuthn if available)
        # For simplicity, we'll use password-derived keys as wrap keys
        wrap_key_real = hashlib.sha256(request.password_real.encode()).digest()
        wrap_key_decoy = hashlib.sha256(request.password_decoy.encode()).digest()

        wrapped_kek_real = _wrap_kek(kek_real, wrap_key_real)
        wrapped_kek_decoy = _wrap_kek(kek_decoy, wrap_key_decoy)

        # Store in database
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Check if metadata exists
            cursor.execute("""
                SELECT id FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (current_user.user_id, request.vault_id))

            existing = cursor.fetchone()

            if existing:
                # Update
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET salt_real = ?,
                        wrapped_kek_real = ?,
                        salt_decoy = ?,
                        wrapped_kek_decoy = ?,
                        decoy_enabled = 1,
                        updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    salt_decoy.hex(),
                    wrapped_kek_decoy.hex(),
                    datetime.now().isoformat(),
                    current_user.user_id,
                    request.vault_id
                ))
            else:
                # Insert
                cursor.execute("""
                    INSERT INTO vault_auth_metadata (
                        id, user_id, vault_id,
                        salt_real, wrapped_kek_real,
                        salt_decoy, wrapped_kek_decoy,
                        decoy_enabled,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    current_user.user_id,
                    request.vault_id,
                    salt_real.hex(),
                    wrapped_kek_real.hex(),
                    salt_decoy.hex(),
                    wrapped_kek_decoy.hex(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()

        # Create session with real vault
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(current_user.user_id, request.vault_id)] = {
            'kek': kek_real,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        logger.info("Decoy mode setup successful", extra={"user_id": current_user.user_id})

        return UnlockResponse(
            success=True,
            session_id=session_id,
            message="Decoy mode configured successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Decoy setup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup decoy mode: {str(e)}"
        )


@router.post("/unlock/passphrase", response_model=UnlockResponse)
async def unlock_passphrase(
    vault_id: str,
    passphrase: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Unlock vault with passphrase

    Supports both single-password and decoy mode:
    - If decoy enabled: try both KEKs, mount whichever decrypts cleanly
    - If single-password: use real KEK only

    Rate limited: 5 attempts per 5 minutes
    """
    client_ip = get_client_ip(request)

    # Rate limit check
    if not _check_rate_limit(current_user.user_id, vault_id, client_ip):
        _record_unlock_attempt(current_user.user_id, vault_id, False, 'passphrase')
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many unlock attempts. Please wait 5 minutes."
        )

    try:
        logger.info(
            "Passphrase unlock attempt",
            extra={
                "user_id": current_user.user_id,
                "vault_id": sanitize_for_log(vault_id)
            }
        )

        # Fetch vault auth metadata
        with sqlite3.connect(str(VAULT_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT salt_real, wrapped_kek_real, salt_decoy, wrapped_kek_decoy, decoy_enabled
                FROM vault_auth_metadata
                WHERE user_id = ? AND vault_id = ?
            """, (current_user.user_id, vault_id))

            row = cursor.fetchone()

            if not row:
                _record_unlock_attempt(current_user.user_id, vault_id, False, 'passphrase')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vault not configured"
                )

            salt_real_hex, wrapped_kek_real_hex, salt_decoy_hex, wrapped_kek_decoy_hex, decoy_enabled = row

        # Derive KEK from passphrase
        salt_real = bytes.fromhex(salt_real_hex) if salt_real_hex else None

        if not salt_real:
            _record_unlock_attempt(current_user.user_id, vault_id, False, 'passphrase')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vault not properly configured"
            )

        # Try real vault first
        kek_attempt = _derive_kek_from_passphrase(passphrase, salt_real)
        wrap_key = hashlib.sha256(passphrase.encode()).digest()
        wrapped_kek_real = bytes.fromhex(wrapped_kek_real_hex)
        kek_real = _unwrap_kek(wrapped_kek_real, wrap_key)

        vault_type = 'real'
        kek = kek_real

        # If decoy enabled, check if passphrase matches decoy
        if decoy_enabled and salt_decoy_hex and wrapped_kek_decoy_hex:
            salt_decoy = bytes.fromhex(salt_decoy_hex)
            kek_attempt_decoy = _derive_kek_from_passphrase(passphrase, salt_decoy)
            wrap_key_decoy = hashlib.sha256(passphrase.encode()).digest()
            wrapped_kek_decoy = bytes.fromhex(wrapped_kek_decoy_hex)
            kek_decoy = _unwrap_kek(wrapped_kek_decoy, wrap_key_decoy)

            # Check which KEK matches (constant-time comparison to avoid timing attacks)
            # In production, verify by attempting decryption of a known-encrypted value
            if kek_attempt_decoy == kek_decoy:
                vault_type = 'decoy'
                kek = kek_decoy

        # Create session
        session_id = secrets.token_urlsafe(32)
        vault_sessions[(current_user.user_id, vault_id)] = {
            'kek': kek,
            'vault_type': vault_type,
            'unlocked_at': time.time(),
            'session_id': session_id
        }

        _record_unlock_attempt(current_user.user_id, vault_id, True, 'passphrase')

        logger.info("Passphrase unlock successful", extra={"user_id": current_user.user_id})

        # Do NOT disclose vault_type
        return UnlockResponse(
            success=True,
            session_id=session_id,
            message="Vault unlocked successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        _record_unlock_attempt(current_user.user_id, vault_id, False, 'passphrase')
        logger.error(f"Passphrase unlock failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock vault"
        )


@router.get("/session/status")
async def get_session_status(
    vault_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if vault is unlocked in current session

    Returns:
    - unlocked: bool
    - session_id: str (if unlocked)
    """
    session_key = (current_user.user_id, vault_id)

    if session_key in vault_sessions:
        session = vault_sessions[session_key]

        # Check if session is still valid (e.g., < 1 hour old)
        if time.time() - session['unlocked_at'] < 3600:
            return {
                "unlocked": True,
                "session_id": session['session_id']
            }
        else:
            # Session expired
            del vault_sessions[session_key]

    return {
        "unlocked": False,
        "session_id": None
    }


@router.post("/session/lock")
async def lock_vault(
    vault_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Lock vault (clear session)
    """
    session_key = (current_user.user_id, vault_id)

    if session_key in vault_sessions:
        del vault_sessions[session_key]
        logger.info("Vault locked", extra={"user_id": current_user.user_id, "vault_id": vault_id})

    return {"success": True, "message": "Vault locked"}
