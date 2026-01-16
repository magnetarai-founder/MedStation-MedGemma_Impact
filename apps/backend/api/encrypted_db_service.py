"""
Compatibility Shim for Encrypted Database Service

The implementation now lives in the `api.security` package:
- api.security.encrypted_db: EncryptedDatabase, BackupCodesService

This shim maintains backward compatibility.

Note: Requires 'cryptography' package to be installed.
"""

try:
    from api.security.encrypted_db import (
        EncryptedDatabase,
        BackupCodesService,
        get_encrypted_database,
    )
except ImportError:
    EncryptedDatabase = None
    BackupCodesService = None
    get_encrypted_database = None

__all__ = [
    "EncryptedDatabase",
    "BackupCodesService",
    "get_encrypted_database",
]
