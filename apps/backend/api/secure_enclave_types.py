"""
Compatibility Shim for Secure Enclave Types

The implementation now lives in the `api.secure_enclave` package:
- api.secure_enclave.types: Request/response models

This shim maintains backward compatibility.
"""

from api.secure_enclave.types import (
    StoreKeyRequest,
    RetrieveKeyRequest,
    KeyResponse,
)

__all__ = [
    "StoreKeyRequest",
    "RetrieveKeyRequest",
    "KeyResponse",
]
