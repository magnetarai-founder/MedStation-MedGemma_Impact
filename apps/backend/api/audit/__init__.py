"""
Audit Logging Package

Provides secure, always-on audit logging for sensitive operations.

Components:
- AuditLogger: Core audit logging with SQLite storage
- EncryptedAuditLogger: AES-256-GCM encrypted audit logs
- AuditAction: Standard action type constants
- AuditEntry: Pydantic model for log entries
- record_audit_event: Simplified audit recording helper
"""

from api.audit.actions import AuditEntry, AuditAction
from api.audit.logger import (
    get_audit_logger,
    AuditLogger,
    audit_log,
    audit_log_sync,
)
from api.audit.helper import record_audit_event
from api.audit.encrypted_logger import (
    EncryptedAuditLogger,
    get_encrypted_audit_logger,
)

__all__ = [
    # Core classes
    "AuditLogger",
    "EncryptedAuditLogger",
    # Models and constants
    "AuditEntry",
    "AuditAction",
    # Functions
    "get_audit_logger",
    "get_encrypted_audit_logger",
    "audit_log",
    "audit_log_sync",
    "record_audit_event",
]
