"""
Secure Enclave Package

macOS Keychain/Secure Enclave integration for ElohimOS:
- Hardware-backed key storage
- PBKDF2 + AES-256-GCM envelope encryption
- Passphrase-protected encryption keys
"""

from api.secure_enclave.types import (
    StoreKeyRequest,
    RetrieveKeyRequest,
    KeyResponse,
)
from api.secure_enclave.service import (
    SecureEnclaveService,
    get_secure_enclave_service,
    router,
    store_key_in_keychain,
    retrieve_key_from_keychain,
    delete_key_from_keychain,
    key_exists_in_keychain,
)

__all__ = [
    # Types
    "StoreKeyRequest",
    "RetrieveKeyRequest",
    "KeyResponse",
    # Service
    "SecureEnclaveService",
    "get_secure_enclave_service",
    # Router
    "router",
    # Functions
    "store_key_in_keychain",
    "retrieve_key_from_keychain",
    "delete_key_from_keychain",
    "key_exists_in_keychain",
]
