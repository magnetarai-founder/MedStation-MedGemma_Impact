"""Backward Compatibility Shim - use api.audit instead."""

from api.audit.helper import (
    record_audit_event,
    get_user_from_current_user,
    logger,
)

__all__ = [
    "record_audit_event",
    "get_user_from_current_user",
    "logger",
]
