"""Backward Compatibility Shim - use api.audit instead."""

from api.audit.logger import (
    AuditLogger,
    get_audit_logger,
    audit_log,
    audit_log_sync,
)

# Re-export types that were traditionally imported from this module
from api.audit.actions import AuditEntry, AuditAction

__all__ = [
    "AuditLogger",
    "get_audit_logger",
    "audit_log",
    "audit_log_sync",
    "AuditEntry",
    "AuditAction",
]
