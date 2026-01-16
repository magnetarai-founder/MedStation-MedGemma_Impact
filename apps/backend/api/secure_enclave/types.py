"""
Secure Enclave Types - Request/response models for keychain operations

Extracted from secure_enclave_service.py during P2 decomposition.
Contains:
- StoreKeyRequest model (store key in keychain)
- RetrieveKeyRequest model (retrieve key from keychain)
- KeyResponse model (keychain operation result)
"""

from typing import Optional

from pydantic import BaseModel


class StoreKeyRequest(BaseModel):
    """Request to store a key in the Secure Enclave/Keychain

    Attributes:
        key_id: Unique identifier for the key
        passphrase: User's passphrase for additional protection
    """
    key_id: str
    passphrase: str


class RetrieveKeyRequest(BaseModel):
    """Request to retrieve a key from the Secure Enclave/Keychain

    Attributes:
        key_id: Unique identifier for the key
        passphrase: User's passphrase to decrypt the key
    """
    key_id: str
    passphrase: str


class KeyResponse(BaseModel):
    """Response for keychain operations

    Attributes:
        success: Whether the operation succeeded
        key_exists: Whether the key exists in keychain
        message: Human-readable status message
        key_data: Base64 encoded key data (only on retrieve)
    """
    success: bool
    key_exists: bool
    message: str
    key_data: Optional[str] = None


__all__ = [
    "StoreKeyRequest",
    "RetrieveKeyRequest",
    "KeyResponse",
]
