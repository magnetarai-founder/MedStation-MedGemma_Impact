"""
Audit Helper (AUTH-P5)

Unified API for recording audit events consistently across the codebase.
Thin wrapper around audit_logger that provides a clean interface for:
- Admin/danger zone operations
- RBAC changes
- Workflow visibility changes
- Agent auto-apply operations
- Data export/backup operations

Writes to both:
- audit.db (persistent storage)
- Structured Python logging

All secrets are automatically redacted via sanitize_for_log().
"""

import logging
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def record_audit_event(
    user_id: str,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """
    Record an audit event in both DB and structured logs.

    This is the canonical way to audit sensitive operations. Use this for:
    - Admin/danger zone operations (resets, clears, uninstalls)
    - RBAC changes (role assignments, permission grants)
    - Workflow visibility changes
    - Agent auto-apply operations
    - Data export/backup operations

    Args:
        user_id: ID of the acting user (or 'system' for internal events)
        action: Short action code (use AuditAction constants)
                Examples: 'admin.reset_all', 'workflow.visibility.changed', 'agent.auto_apply'
        resource: Target resource type (e.g., 'workflow', 'system', 'user')
        resource_id: Specific resource identifier (workflow_id, user_id, etc.)
        details: Optional dict with extra context (no secrets - they'll be redacted)
                 Examples: {'files_changed': 5}, {'from': 'personal', 'to': 'team'}
        ip_address: Client IP address (if available)
        user_agent: Client user agent (if available)

    Returns:
        True if audit event was recorded successfully, False otherwise

    Notes:
        - Writes to audit.db (SQLite) for persistence
        - Writes to Python logger for structured logging
        - Automatically redacts secrets (passwords, tokens, keys) from details
        - Never raises exceptions - failures are logged but don't crash the app

    Example:
        >>> from api.audit_helper import record_audit_event
        >>> from api.audit_logger import AuditAction
        >>> record_audit_event(
        ...     user_id='user_123',
        ...     action=AuditAction.ADMIN_RESET_ALL,
        ...     resource='system',
        ...     details={'reason': 'dev reset'}
        ... )
        True
    """
    try:
        # Import audit_logger (lazy to avoid circular imports)
        try:
            from api.audit_logger import audit_log_sync
        except ImportError:
            from audit_logger import audit_log_sync

        # Call the existing audit_log_sync which:
        # 1. Writes to audit.db
        # 2. Writes to structured Python logging
        # 3. Sanitizes secrets from details automatically
        audit_log_sync(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details
        )

        # Log to Python logger as well for immediate visibility
        logger.info(
            f"Audit: {action}",
            extra={
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )

        return True

    except Exception as e:
        # Log error but don't raise - audit failures shouldn't break operations
        logger.error(f"Failed to record audit event: {e}", exc_info=True)
        return False


def get_user_from_current_user(current_user: Optional[dict]) -> str:
    """
    Extract user_id from current_user dict (FastAPI dependency injection pattern).

    Args:
        current_user: Dict from get_current_user dependency

    Returns:
        user_id string, or 'system' if not available
    """
    if current_user and isinstance(current_user, dict):
        return current_user.get('user_id', 'system')
    return 'system'
