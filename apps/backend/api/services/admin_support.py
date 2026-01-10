"""
Admin Support Service for ElohimOS

Provides Founder Rights support capabilities:
- User account metadata (list, details)
- Chat session metadata (user chats, all chats)
- Account remediation (password reset, unlock)
- Vault status metadata (document counts only, no decrypted content)
- Device overview metrics (system-wide statistics)
- Workflow metadata
- Audit log queries

Does NOT expose:
- Decrypted vault content
- User passwords
- Personal encrypted data

This follows the Salesforce model: Admins can manage accounts but cannot see user data.

Extracted modules (P2 decomposition):
- admin_users.py: User and chat metadata operations
- admin_account.py: Account remediation operations
- admin_metrics.py: Vault, device, and workflow metrics
- admin_audit.py: Audit log operations
"""

import logging

logger = logging.getLogger(__name__)

# Re-export from extracted modules for backward compatibility
from .admin_users import (
    get_admin_db_connection,
    list_all_users,
    get_user_details,
    get_user_chats,
    list_all_chats,
)
from .admin_account import (
    reset_user_password,
    unlock_user_account,
)
from .admin_metrics import (
    get_vault_status,
    get_device_overview_metrics,
    get_user_workflows,
)
from .admin_audit import (
    get_audit_logs,
    export_audit_logs,
)


__all__ = [
    # From admin_users
    "get_admin_db_connection",
    "list_all_users",
    "get_user_details",
    "get_user_chats",
    "list_all_chats",
    # From admin_account
    "reset_user_password",
    "unlock_user_account",
    # From admin_metrics
    "get_vault_status",
    "get_device_overview_metrics",
    "get_user_workflows",
    # From admin_audit
    "get_audit_logs",
    "export_audit_logs",
]
