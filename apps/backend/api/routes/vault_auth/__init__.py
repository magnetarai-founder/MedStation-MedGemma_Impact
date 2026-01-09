"""
Vault Auth Package

Biometric (WebAuthn/Touch ID) and passphrase-based vault authentication.

This package provides:
- Biometric (Touch ID) setup and unlock
- Dual-password mode (decoy for plausible deniability)
- Passphrase-based unlock
- Session management (lock/unlock status)

Architecture:
- helpers.py: Session management, rate limiting, audit logging
- biometric_routes.py: WebAuthn setup and unlock endpoints
- passphrase_routes.py: Passphrase unlock and dual-password setup
- session_routes.py: Session status and lock endpoints

Security model:
- KEK (Key Encryption Key) derived client-side via PBKDF2
- KEK wrapped with WebAuthn credential ID or passphrase
- Server stores only wrapped KEKs, never plaintext keys
- Rate limiting on unlock attempts (5 attempts → 5-minute lockout)
"""

from fastapi import APIRouter

from api.config import get_settings
from api.config_paths import get_config_paths
from api.rate_limiter import rate_limiter

# Import sub-routers
from api.routes.vault_auth.biometric_routes import router as biometric_router
from api.routes.vault_auth.passphrase_routes import router as passphrase_router
from api.routes.vault_auth.session_routes import router as session_router

# Re-export helpers
from api.routes.vault_auth.helpers import (
    VAULT_DB_PATH,
    UNLOCK_RATE_LIMIT,
    UNLOCK_WINDOW_SECONDS,
    vault_sessions,
    check_rate_limit,
    record_unlock_attempt,
    get_session,
    create_session,
    delete_session,
    # Backwards compatibility aliases
    _check_rate_limit,
    _record_unlock_attempt,
)

# Re-export from vault_auth_utils for backwards compatibility
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
    webauthn_challenges,
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
    # Backwards compatibility aliases
    _generate_challenge,
    _get_challenge,
    _consume_challenge,
    _cleanup_expired_challenges,
    _derive_kek_from_passphrase,
    _wrap_kek,
    _unwrap_kek,
    _migrate_xor_to_aes_kw,
)

# Re-export endpoint functions for direct access
from api.routes.vault_auth.biometric_routes import (
    setup_biometric,
    get_biometric_challenge,
    unlock_biometric,
)
from api.routes.vault_auth.passphrase_routes import (
    setup_dual_password,
    setup_decoy_legacy,
    unlock_passphrase,
)
from api.routes.vault_auth.session_routes import (
    get_session_status,
    lock_vault,
)

# WebAuthn configuration - loaded from settings (supports env vars)
_settings = get_settings()
WEBAUTHN_RP_ID = _settings.webauthn_rp_id
WEBAUTHN_ORIGIN = _settings.webauthn_origin


def _init_vault_auth_db() -> None:
    """Initialize vault auth database using module-level VAULT_DB_PATH.

    This wrapper exists for test compatibility - tests patch VAULT_DB_PATH
    and call this no-argument function.
    """
    init_vault_auth_db(VAULT_DB_PATH)


# Create main router
router = APIRouter(prefix="/api/v1/vault", tags=["vault-auth"])

# Compose sub-routers
router.include_router(biometric_router)
router.include_router(passphrase_router)
router.include_router(session_router)

# Initialize database on module load
init_vault_auth_db(VAULT_DB_PATH)


# Export all public symbols
__all__ = [
    # Router
    "router",
    # Rate limiter
    "rate_limiter",
    # Helpers
    "VAULT_DB_PATH",
    "UNLOCK_RATE_LIMIT",
    "UNLOCK_WINDOW_SECONDS",
    "vault_sessions",
    "check_rate_limit",
    "record_unlock_attempt",
    "get_session",
    "create_session",
    "delete_session",
    "_check_rate_limit",
    "_record_unlock_attempt",
    # WebAuthn config
    "WEBAUTHN_RP_ID",
    "WEBAUTHN_ORIGIN",
    # From vault_auth_utils
    "BiometricSetupRequest",
    "BiometricUnlockRequest",
    "DualPasswordSetupRequest",
    "UnlockResponse",
    "ChallengeResponse",
    "generate_challenge",
    "get_challenge",
    "consume_challenge",
    "cleanup_expired_challenges",
    "CHALLENGE_TTL_SECONDS",
    "webauthn_challenges",
    "derive_kek_from_passphrase",
    "wrap_kek",
    "unwrap_kek",
    "migrate_xor_to_aes_kw",
    "PBKDF2_ITERATIONS",
    "crypto_wrap_key",
    "crypto_unwrap_key",
    "init_vault_auth_db",
    "_init_vault_auth_db",
    "_generate_challenge",
    "_get_challenge",
    "_consume_challenge",
    "_cleanup_expired_challenges",
    "_derive_kek_from_passphrase",
    "_wrap_kek",
    "_unwrap_kek",
    "_migrate_xor_to_aes_kw",
    # Endpoints
    "setup_biometric",
    "get_biometric_challenge",
    "unlock_biometric",
    "setup_dual_password",
    "setup_decoy_legacy",
    "unlock_passphrase",
    "get_session_status",
    "lock_vault",
]
