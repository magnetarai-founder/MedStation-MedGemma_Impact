"""
Audit Actions and Entry Models

Static constants and models for the audit logging system.
Extracted from audit_logger.py during P2 decomposition.

Contains:
- AuditAction class with 70+ action type constants
- AuditEntry Pydantic model
- Action categorization helpers
- Action validation utilities
"""

from typing import Optional, Dict, Any, List, Set
from pydantic import BaseModel


class AuditEntry(BaseModel):
    """Audit log entry model"""
    id: Optional[int] = None
    user_id: str
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class AuditAction:
    """
    Standard audit action types

    Organized by category for easy reference.
    All actions follow the pattern: category.subcategory.verb
    """

    # ============================================
    # AUTHENTICATION
    # ============================================
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login.failed"

    # ============================================
    # USER MANAGEMENT
    # ============================================
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role.changed"

    # ============================================
    # VAULT OPERATIONS
    # ============================================
    VAULT_ACCESSED = "vault.accessed"
    VAULT_ITEM_CREATED = "vault.item.created"
    VAULT_ITEM_VIEWED = "vault.item.viewed"
    VAULT_ITEM_UPDATED = "vault.item.updated"
    VAULT_ITEM_DELETED = "vault.item.deleted"

    # ============================================
    # WORKFLOW OPERATIONS
    # ============================================
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_VIEWED = "workflow.viewed"
    WORKFLOW_UPDATED = "workflow.updated"
    WORKFLOW_DELETED = "workflow.deleted"
    WORKFLOW_EXECUTED = "workflow.executed"
    WORKFLOW_VISIBILITY_CHANGED = "workflow.visibility.changed"  # AUTH-P5
    WORKFLOW_OWNERSHIP_CHANGED = "workflow.ownership.changed"    # AUTH-P5

    # ============================================
    # FILE OPERATIONS
    # ============================================
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_DELETED = "file.deleted"

    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    SQL_QUERY_EXECUTED = "sql.query.executed"
    DATABASE_EXPORTED = "database.exported"

    # ============================================
    # SECURITY OPERATIONS
    # ============================================
    PANIC_MODE_ACTIVATED = "security.panic_mode.activated"
    BACKUP_CREATED = "backup.created"
    BACKUP_RESTORED = "backup.restored"
    ENCRYPTION_KEY_ROTATED = "security.key.rotated"

    # ============================================
    # SETTINGS
    # ============================================
    SETTINGS_CHANGED = "settings.changed"

    # ============================================
    # CODE & AGENT OPERATIONS
    # ============================================
    CODE_ASSIST = "code.assist"
    CODE_EDIT = "code.edit"
    CODE_FILE_OPENED = "code.file.opened"
    CODE_FILE_SAVED = "code.file.saved"
    CODE_WORKSPACE_CREATED = "code.workspace.created"
    CODE_WORKSPACE_SYNCED = "code.workspace.synced"
    CODE_FILE_CREATED = "code.file.created"
    CODE_FILE_UPDATED = "code.file.updated"
    CODE_FILE_DELETED = "code.file.deleted"
    CODE_FILE_IMPORTED = "code.file.imported"

    # ============================================
    # TERMINAL OPERATIONS
    # ============================================
    TERMINAL_SPAWN = "terminal.spawn"
    TERMINAL_CLOSE = "terminal.close"
    TERMINAL_COMMAND = "terminal.command"

    # ============================================
    # ADMIN/FOUNDER RIGHTS OPERATIONS
    # ============================================
    ADMIN_LIST_USERS = "admin.list.users"
    ADMIN_VIEW_USER = "admin.view.user"
    ADMIN_VIEW_USER_CHATS = "admin.view.user_chats"
    ADMIN_LIST_ALL_CHATS = "admin.list.all_chats"
    ADMIN_RESET_PASSWORD = "admin.reset_password"
    ADMIN_UNLOCK_ACCOUNT = "admin.unlock_account"
    ADMIN_VIEW_VAULT_STATUS = "admin.view.vault_status"
    ADMIN_VIEW_DEVICE_OVERVIEW = "admin.view.device_overview"
    ADMIN_VIEW_USER_WORKFLOWS = "admin.view.user_workflows"
    FOUNDER_RIGHTS_LOGIN = "founder_rights.login"

    # ============================================
    # ADMIN DANGER ZONE OPERATIONS (AUTH-P5)
    # ============================================
    ADMIN_RESET_ALL = "admin.reset_all"
    ADMIN_UNINSTALL = "admin.uninstall"
    ADMIN_CLEAR_CHATS = "admin.clear_chats"
    ADMIN_CLEAR_TEAM_MESSAGES = "admin.clear_team_messages"
    ADMIN_CLEAR_QUERY_LIBRARY = "admin.clear_query_library"
    ADMIN_CLEAR_QUERY_HISTORY = "admin.clear_query_history"
    ADMIN_CLEAR_TEMP_FILES = "admin.clear_temp_files"
    ADMIN_CLEAR_CODE_FILES = "admin.clear_code_files"
    ADMIN_RESET_SETTINGS = "admin.reset_settings"
    ADMIN_RESET_DATA = "admin.reset_data"

    # ============================================
    # ADMIN EXPORT OPERATIONS (AUTH-P5)
    # ============================================
    ADMIN_EXPORT_ALL = "admin.export_all"
    ADMIN_EXPORT_CHATS = "admin.export_chats"
    ADMIN_EXPORT_QUERIES = "admin.export_queries"

    # ============================================
    # PERMISSION OPERATIONS (Phase 5.1 - LOW-07)
    # ============================================
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    PERMISSION_MODIFIED = "permission.modified"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_REMOVED = "role.removed"
    PROFILE_GRANTED = "profile.granted"
    PROFILE_REVOKED = "profile.revoked"
    PERMISSION_SET_GRANTED = "permission_set.granted"
    PERMISSION_SET_REVOKED = "permission_set.revoked"
    PERMISSION_CHECK_DENIED = "permission.check.denied"
    PERMISSION_CHECK_GRANTED = "permission.check.granted"

    # ============================================
    # MODEL OPERATIONS (Sprint 3)
    # ============================================
    MODEL_PREFERENCE_TOGGLED = "model.preference.toggled"
    MODEL_HOT_SLOT_ASSIGNED = "model.hot_slot.assigned"
    SESSION_MODEL_UPDATED = "session.model.updated"

    # ============================================
    # SESSION OPERATIONS (Sprint 4)
    # ============================================
    TOKEN_NEAR_LIMIT_WARNING = "session.token.near_limit"
    SUMMARIZE_CONTEXT_INVOKED = "session.summarize.invoked"

    # ============================================
    # MODEL POLICY OPERATIONS (Sprint 5)
    # ============================================
    MODEL_POLICY_VIOLATED = "model.policy.violated"
    MODEL_POLICY_UPDATED = "model.policy.updated"

    # ============================================
    # AGENT SESSION OPERATIONS (Obs-1)
    # ============================================
    AGENT_SESSION_CREATED = "agent.session.created"
    AGENT_SESSION_CLOSED = "agent.session.closed"
    AGENT_SESSION_PLAN_UPDATED = "agent.session.plan.updated"
    AGENT_SESSION_ERROR = "agent.session.error"

    # ============================================
    # AGENT ORCHESTRATION OPERATIONS (Obs-1, AUTH-P5)
    # ============================================
    AGENT_ROUTE_COMPLETED = "agent.route.completed"
    AGENT_PLAN_GENERATED = "agent.plan.generated"
    AGENT_CONTEXT_BUILT = "agent.context.built"
    AGENT_APPLY_SUCCESS = "agent.apply.success"
    AGENT_APPLY_FAILURE = "agent.apply.failure"
    AGENT_AUTO_APPLY = "agent.auto_apply"  # AUTH-P5 - Agent auto-apply with file changes

    # ============================================
    # WORKFLOW AGENT INTEGRATION (Obs-1)
    # ============================================
    WORKFLOW_AGENT_ASSIST_STARTED = "workflow.agent_assist.started"
    WORKFLOW_AGENT_ASSIST_COMPLETED = "workflow.agent_assist.completed"
    WORKFLOW_AGENT_ASSIST_ERROR = "workflow.agent_assist.error"
    WORKFLOW_TRIGGER_FIRED = "workflow.trigger.fired"
    WORKFLOW_ANALYTICS_COMPUTED = "workflow.analytics.computed"


# ============================================
# ACTION CATEGORIZATION HELPERS
# ============================================

def get_action_category(action: str) -> str:
    """
    Get the category of an audit action.

    Args:
        action: Action string (e.g., "user.login", "vault.item.created")

    Returns:
        Category string (e.g., "user", "vault", "admin")
    """
    parts = action.split(".")
    return parts[0] if parts else "unknown"


def get_all_actions() -> List[str]:
    """
    Get all defined audit action values.

    Returns:
        List of all action string values
    """
    return [
        getattr(AuditAction, attr)
        for attr in dir(AuditAction)
        if not attr.startswith("_") and isinstance(getattr(AuditAction, attr), str)
    ]


def get_actions_by_category(category: str) -> List[str]:
    """
    Get all actions in a specific category.

    Args:
        category: Category prefix (e.g., "user", "vault", "admin")

    Returns:
        List of action strings in that category
    """
    prefix = f"{category}."
    return [action for action in get_all_actions() if action.startswith(prefix)]


def is_valid_action(action: str) -> bool:
    """
    Check if an action string is a valid defined action.

    Args:
        action: Action string to validate

    Returns:
        True if action is defined in AuditAction
    """
    return action in get_all_actions()


# Pre-computed category sets for efficient lookups
SECURITY_ACTIONS: Set[str] = {
    AuditAction.USER_LOGIN,
    AuditAction.USER_LOGOUT,
    AuditAction.USER_LOGIN_FAILED,
    AuditAction.PANIC_MODE_ACTIVATED,
    AuditAction.ENCRYPTION_KEY_ROTATED,
    AuditAction.PERMISSION_CHECK_DENIED,
    AuditAction.PERMISSION_CHECK_GRANTED,
    AuditAction.FOUNDER_RIGHTS_LOGIN,
}
"""Actions related to security events"""

DESTRUCTIVE_ACTIONS: Set[str] = {
    AuditAction.USER_DELETED,
    AuditAction.VAULT_ITEM_DELETED,
    AuditAction.WORKFLOW_DELETED,
    AuditAction.FILE_DELETED,
    AuditAction.CODE_FILE_DELETED,
    AuditAction.ADMIN_RESET_ALL,
    AuditAction.ADMIN_UNINSTALL,
    AuditAction.ADMIN_CLEAR_CHATS,
    AuditAction.ADMIN_CLEAR_TEAM_MESSAGES,
    AuditAction.ADMIN_CLEAR_QUERY_LIBRARY,
    AuditAction.ADMIN_CLEAR_QUERY_HISTORY,
    AuditAction.ADMIN_CLEAR_TEMP_FILES,
    AuditAction.ADMIN_CLEAR_CODE_FILES,
    AuditAction.ADMIN_RESET_SETTINGS,
    AuditAction.ADMIN_RESET_DATA,
}
"""Actions that delete or destroy data"""

ADMIN_ACTIONS: Set[str] = {
    action for action in get_all_actions() if action.startswith("admin.")
}
"""All admin-level actions"""


__all__ = [
    # Models
    "AuditEntry",
    "AuditAction",
    # Helper functions
    "get_action_category",
    "get_all_actions",
    "get_actions_by_category",
    "is_valid_action",
    # Pre-computed sets
    "SECURITY_ACTIONS",
    "DESTRUCTIVE_ACTIONS",
    "ADMIN_ACTIONS",
]
