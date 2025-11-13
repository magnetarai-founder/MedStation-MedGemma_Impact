"""
Vault Encryption Helpers

Server-side encryption utilities for vault operations.
Note: Primary encryption happens client-side; these are supplementary helpers.
"""

import hashlib
import secrets
from cryptography.fernet import Fernet


def get_encryption_key(passphrase: str, salt: bytes = b'elohimos_vault_salt') -> bytes:
    """
    Generate encryption key from passphrase using PBKDF2.

    Args:
        passphrase: User passphrase
        salt: Salt for key derivation

    Returns:
        32-byte encryption key
    """
    key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), salt, 100000)
    return key


def generate_file_key() -> str:
    """
    Generate random 256-bit key for file-level encryption.

    Returns:
        Base64-encoded Fernet key
    """
    return Fernet.generate_key().decode('utf-8')


def generate_share_token() -> str:
    """
    Generate secure random token for file sharing.

    Returns:
        URL-safe random token (32 bytes)
    """
    return secrets.token_urlsafe(32)
