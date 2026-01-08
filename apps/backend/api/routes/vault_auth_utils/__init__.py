"""
Vault Auth Utilities Package

Extracted utilities for vault authentication:
- models: Pydantic request/response models
- challenges: WebAuthn challenge management
- crypto: KEK derivation, wrapping, migration
- db: Database initialization
"""

from api.routes.vault_auth_utils.models import (
    BiometricSetupRequest,
    BiometricUnlockRequest,
    DualPasswordSetupRequest,
    UnlockResponse,
    ChallengeResponse,
)

from api.routes.vault_auth_utils.challenges import (
    generate_challenge,
    get_challenge,
    consume_challenge,
    cleanup_expired_challenges,
    CHALLENGE_TTL_SECONDS,
    webauthn_challenges,  # Internal state for testing
)

from api.routes.vault_auth_utils.crypto import (
    derive_kek_from_passphrase,
    wrap_kek,
    unwrap_kek,
    migrate_xor_to_aes_kw,
    PBKDF2_ITERATIONS,
    # Re-export internal crypto functions for test compatibility
    crypto_wrap_key,
    crypto_unwrap_key,
)

from api.routes.vault_auth_utils.db import init_vault_auth_db

# Underscore aliases for backwards compatibility with tests
_generate_challenge = generate_challenge
_get_challenge = get_challenge
_consume_challenge = consume_challenge
_cleanup_expired_challenges = cleanup_expired_challenges
_derive_kek_from_passphrase = derive_kek_from_passphrase
_wrap_kek = wrap_kek
_unwrap_kek = unwrap_kek
_migrate_xor_to_aes_kw = migrate_xor_to_aes_kw
_init_vault_auth_db = init_vault_auth_db

__all__ = [
    # Models
    "BiometricSetupRequest",
    "BiometricUnlockRequest",
    "DualPasswordSetupRequest",
    "UnlockResponse",
    "ChallengeResponse",
    # Challenges
    "generate_challenge",
    "get_challenge",
    "consume_challenge",
    "cleanup_expired_challenges",
    "CHALLENGE_TTL_SECONDS",
    "webauthn_challenges",
    # Crypto
    "derive_kek_from_passphrase",
    "wrap_kek",
    "unwrap_kek",
    "migrate_xor_to_aes_kw",
    "PBKDF2_ITERATIONS",
    "crypto_wrap_key",
    "crypto_unwrap_key",
    # Database
    "init_vault_auth_db",
    # Backwards compatibility aliases
    "_generate_challenge",
    "_get_challenge",
    "_consume_challenge",
    "_cleanup_expired_challenges",
    "_derive_kek_from_passphrase",
    "_wrap_kek",
    "_unwrap_kek",
    "_migrate_xor_to_aes_kw",
    "_init_vault_auth_db",
]
