"""
Key wrapping utilities for ElohimOS vault KEKs.

Provides two wrapping schemes:
- AES Key Wrap (RFC 3394) via cryptography
- XChaCha20-Poly1305 (libsodium/PyNaCl) as an AEAD fallback

Usage:
    wrapped = wrap_key(key_bytes, wrapping_key, method="aes_kw")
    key = unwrap_key(wrapped, wrapping_key, method="aes_kw")

Notes:
- AES-KW requires wrapping_key length of 16/24/32 bytes
- XChaCha20-Poly1305 prepends a 24-byte nonce to the ciphertext
"""

from __future__ import annotations

import os
from typing import Literal

from cryptography.hazmat.primitives.keywrap import aes_key_wrap, aes_key_unwrap
from cryptography.hazmat.backends import default_backend

try:
    from nacl.bindings import (
        crypto_aead_xchacha20poly1305_ietf_decrypt,
        crypto_aead_xchacha20poly1305_ietf_encrypt,
    )
    _XCHACHA_AVAILABLE = True
except Exception:
    _XCHACHA_AVAILABLE = False


WrapMethod = Literal["aes_kw", "xchacha20p"]


def wrap_key_aes_kw(key: bytes, wrapping_key: bytes) -> bytes:
    """Wrap key using AES Key Wrap (RFC 3394).

    Args:
        key: key material to wrap (e.g., 32-byte KEK)
        wrapping_key: AES key (16/24/32 bytes)
    Returns:
        Wrapped key bytes
    """
    if len(wrapping_key) not in (16, 24, 32):
        raise ValueError("wrapping_key must be 16/24/32 bytes for AES-KW")
    return aes_key_wrap(wrapping_key, key, backend=default_backend())


def unwrap_key_aes_kw(wrapped: bytes, wrapping_key: bytes) -> bytes:
    """Unwrap AES-KW wrapped key.

    Args:
        wrapped: wrapped key bytes
        wrapping_key: AES key (16/24/32 bytes)
    Returns:
        Unwrapped key material
    """
    if len(wrapping_key) not in (16, 24, 32):
        raise ValueError("wrapping_key must be 16/24/32 bytes for AES-KW")
    return aes_key_unwrap(wrapping_key, wrapped, backend=default_backend())


def wrap_key_xchacha(key: bytes, wrapping_key: bytes, aad: bytes | None = None) -> bytes:
    """Wrap key with XChaCha20-Poly1305 (nonce + ciphertext).

    Args:
        key: key material to wrap
        wrapping_key: 32-byte key (symmetric)
        aad: optional associated data
    Returns:
        24-byte nonce + ciphertext+auth_tag
    """
    if not _XCHACHA_AVAILABLE:
        raise RuntimeError("PyNaCl XChaCha20-Poly1305 not available")
    if len(wrapping_key) != 32:
        raise ValueError("wrapping_key must be 32 bytes for XChaCha20-Poly1305")
    nonce = os.urandom(24)
    ct = crypto_aead_xchacha20poly1305_ietf_encrypt(key, aad or b"", nonce, wrapping_key)
    return nonce + ct


def unwrap_key_xchacha(wrapped: bytes, wrapping_key: bytes, aad: bytes | None = None) -> bytes:
    """Unwrap XChaCha20-Poly1305 wrapped key (nonce + ciphertext).

    Args:
        wrapped: nonce+ciphertext bytes
        wrapping_key: 32-byte key
        aad: optional associated data
    Returns:
        Unwrapped key material
    """
    if not _XCHACHA_AVAILABLE:
        raise RuntimeError("PyNaCl XChaCha20-Poly1305 not available")
    if len(wrapping_key) != 32:
        raise ValueError("wrapping_key must be 32 bytes for XChaCha20-Poly1305")
    if len(wrapped) < 24:
        raise ValueError("wrapped input too short")
    nonce, ct = wrapped[:24], wrapped[24:]
    return crypto_aead_xchacha20poly1305_ietf_decrypt(ct, aad or b"", nonce, wrapping_key)


def wrap_key(key: bytes, wrapping_key: bytes, method: WrapMethod = "aes_kw") -> bytes:
    """Generic key wrap dispatcher."""
    if method == "aes_kw":
        return wrap_key_aes_kw(key, wrapping_key)
    if method == "xchacha20p":
        return wrap_key_xchacha(key, wrapping_key)
    raise ValueError(f"Unknown wrap method: {method}")


def unwrap_key(wrapped: bytes, wrapping_key: bytes, method: WrapMethod = "aes_kw") -> bytes:
    """Generic key unwrap dispatcher."""
    if method == "aes_kw":
        return unwrap_key_aes_kw(wrapped, wrapping_key)
    if method == "xchacha20p":
        return unwrap_key_xchacha(wrapped, wrapping_key)
    raise ValueError(f"Unknown wrap method: {method}")

