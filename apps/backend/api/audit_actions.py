"""Backward Compatibility Shim - use api.audit instead."""

from api.audit.actions import (
    AuditEntry,
    AuditAction,
    get_action_category,
    get_all_actions,
    get_actions_by_category,
    is_valid_action,
)

__all__ = [
    "AuditEntry",
    "AuditAction",
    "get_action_category",
    "get_all_actions",
    "get_actions_by_category",
    "is_valid_action",
]
