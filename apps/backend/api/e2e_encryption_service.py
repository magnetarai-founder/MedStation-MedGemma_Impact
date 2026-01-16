"""
Compatibility Shim for E2E Encryption Service

The implementation now lives in the `api.security` package:
- api.security.e2e_encryption: E2EEncryptionService class

This shim maintains backward compatibility.

Note: Requires 'nacl' (PyNaCl) package to be installed.
"""

try:
    from api.security.e2e_encryption import (
        E2EEncryptionService,
        get_e2e_service,
    )
except ImportError:
    E2EEncryptionService = None
    get_e2e_service = None

__all__ = [
    "E2EEncryptionService",
    "get_e2e_service",
]
