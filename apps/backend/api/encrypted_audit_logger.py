"""Backward Compatibility Shim - use api.audit instead."""

from api.audit.encrypted_logger import (
    EncryptedAuditLogger,
    get_encrypted_audit_logger,
)

__all__ = [
    "EncryptedAuditLogger",
    "get_encrypted_audit_logger",
]
