"""
Vault Authentication Cryptographic Utilities

KEK derivation, wrapping/unwrapping, and migration functions.
"""

import hashlib
import logging
import sqlite3
from pathlib import Path

from api.services.crypto_wrap import wrap_key as crypto_wrap_key, unwrap_key as crypto_unwrap_key
from api.utils import sanitize_for_log

logger = logging.getLogger(__name__)

# PBKDF2 iteration count - OWASP 2023 recommends 600,000 for SHA-256
# NOTE: Client-side derivation must use the same iteration count
PBKDF2_ITERATIONS = 600_000


def derive_kek_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """
    Derive KEK from passphrase using PBKDF2 with 600K iterations.

    Security note: Uses OWASP 2023 recommended iteration count.
    This must match client-side derivation (VaultService.swift).

    Migration: Existing vaults may use 100K iterations. Store iteration
    count in vault metadata for backwards compatibility if needed.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        passphrase.encode(),
        salt,
        iterations=PBKDF2_ITERATIONS,
        dklen=32
    )


def wrap_kek(kek: bytes, wrap_key: bytes, method: str = "aes_kw") -> bytes:
    """
    Wrap KEK with a wrapping key using AES-KW (RFC 3394)

    Args:
        kek: Key Encryption Key to wrap (32 bytes)
        wrap_key: Wrapping key (derived from WebAuthn credential or passphrase, 32 bytes)
        method: Wrapping method (aes_kw, xchacha20p, or xor_legacy)

    Returns:
        Wrapped KEK bytes
    """
    if method == "xor_legacy":
        # Legacy XOR wrap (kept for backward compatibility with existing vaults)
        return bytes(a ^ b for a, b in zip(kek, wrap_key[:len(kek)]))

    # Use crypto_wrap utilities (AES-KW or XChaCha20-Poly1305)
    return crypto_wrap_key(kek, wrap_key[:32], method=method)


def unwrap_kek(wrapped_kek: bytes, wrap_key: bytes, method: str = "aes_kw") -> bytes:
    """
    Unwrap KEK (inverse of wrap)

    Args:
        wrapped_kek: Wrapped KEK bytes
        wrap_key: Wrapping key (32 bytes)
        method: Wrapping method (aes_kw, xchacha20p, or xor_legacy)

    Returns:
        Unwrapped KEK bytes
    """
    if method == "xor_legacy":
        # Legacy XOR unwrap (XOR is self-inverse)
        return bytes(a ^ b for a, b in zip(wrapped_kek, wrap_key[:len(wrapped_kek)]))

    # Use crypto_wrap utilities
    return crypto_unwrap_key(wrapped_kek, wrap_key[:32], method=method)


def migrate_xor_to_aes_kw(
    user_id: str,
    vault_id: str,
    kek: bytes,
    wrap_key: bytes,
    vault_type: str,
    vault_db_path: Path
) -> bool:
    """
    Migrate vault from XOR legacy wrapping to AES-KW.

    Called automatically after successful unlock when wrap_method is 'xor_legacy'.
    This provides transparent upgrade to stronger key wrapping without user action.

    Args:
        user_id: User ID
        vault_id: Vault ID
        kek: Unwrapped KEK (from successful unlock)
        wrap_key: Wrap key derived from passphrase
        vault_type: 'real' or 'decoy' to indicate which KEK column to update
        vault_db_path: Path to vault database

    Returns:
        True if migration successful, False otherwise
    """
    from datetime import datetime

    try:
        # Re-wrap KEK with AES-KW
        wrapped_kek_new = wrap_kek(kek, wrap_key, method="aes_kw")
        wrapped_kek_hex = wrapped_kek_new.hex()

        with sqlite3.connect(str(vault_db_path)) as conn:
            cursor = conn.cursor()

            # Update the appropriate column based on vault type
            if vault_type == "real":
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET wrapped_kek_real = ?, wrap_method = 'aes_kw', updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (wrapped_kek_hex, datetime.now().isoformat(), user_id, vault_id))
            else:
                cursor.execute("""
                    UPDATE vault_auth_metadata
                    SET wrapped_kek_decoy = ?, wrap_method = 'aes_kw', updated_at = ?
                    WHERE user_id = ? AND vault_id = ?
                """, (wrapped_kek_hex, datetime.now().isoformat(), user_id, vault_id))

            conn.commit()

        logger.info(
            "Migrated vault from xor_legacy to aes_kw",
            extra={
                "user_id": user_id,
                "vault_id": sanitize_for_log(vault_id),
                "vault_type": vault_type
            }
        )
        return True

    except Exception as e:
        logger.warning(
            f"XOR to AES-KW migration failed (non-fatal): {e}",
            extra={"user_id": user_id, "vault_id": sanitize_for_log(vault_id)}
        )
        return False
