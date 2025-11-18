"""
Vault Encryption Helpers

Server-side encryption utilities for vault operations.
Note: Primary encryption happens client-side; these are supplementary helpers.
"""

import base64
import hashlib
import os
import secrets
from typing import Optional
from cryptography.fernet import Fernet


def get_encryption_key(passphrase: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Generate encryption key from passphrase using PBKDF2

    Args:
        passphrase: User passphrase for encryption
        salt: Optional salt for key derivation (generates default if not provided)

    Returns:
        tuple: (encryption_key, salt) - Both as bytes
    """
    # Use provided salt or generate new one
    if salt is None:
        salt = hashlib.sha256(b"elohimos_vault_salt_v1").digest()[:16]

    # Use PBKDF2 with 600,000 iterations (OWASP 2023 recommendation)
    key_material = hashlib.pbkdf2_hmac(
        'sha256',
        passphrase.encode('utf-8'),
        salt,
        600000,  # iterations
        dklen=32  # 256-bit key
    )
    key = base64.urlsafe_b64encode(key_material)
    return key, salt


def generate_file_key() -> bytes:
    """
    Generate a random 256-bit key for file-level encryption

    Returns:
        Base64-encoded 256-bit key
    """
    file_key = os.urandom(32)  # 256 bits
    return base64.urlsafe_b64encode(file_key)


def generate_share_token() -> str:
    """
    Generate secure random token for file sharing.

    Returns:
        URL-safe random token (32 bytes)
    """
    return secrets.token_urlsafe(32)
