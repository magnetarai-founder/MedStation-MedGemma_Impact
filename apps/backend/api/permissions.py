"""
Role-Based Access Control (RBAC) System

4 Roles:
- Super Admin: Full control, can create Admins, transfer super admin status
- Admin: Manage users/workflows/settings (cannot create other Admins)
- Member: Default role, create/edit own workflows, access vault
- Viewer: Read-only access, cannot modify anything

Security Rules:
- Last Admin cannot be deleted/downgraded
- Super Admin cannot delete themselves (must transfer first)
- Only Super Admin can create/manage Admins
"""

from enum import Enum
from typing import Optional, Callable
from functools import wraps
from fastapi import HTTPException, Depends, Request
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles in order of privilege"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Role hierarchy (higher number = more privileges)
ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: 4,
    Role.ADMIN: 3,
    Role.MEMBER: 2,
    Role.VIEWER: 1
}


class Permission:
    """Permission definitions"""

    # User Management
    CREATE_ADMIN = "create_admin"
    MANAGE_USERS = "manage_users"
    DELETE_USER = "delete_user"

    # Workflows
    CREATE_WORKFLOW = "create_workflow"
    EDIT_WORKFLOW = "edit_workflow"
    DELETE_WORKFLOW = "delete_workflow"
    VIEW_WORKFLOW = "view_workflow"

    # Data & Vault
    ACCESS_VAULT = "access_vault"
    EXPORT_DATA = "export_data"
    RUN_SQL = "run_sql"

    # System
    TRIGGER_PANIC_MODE = "trigger_panic_mode"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SETTINGS = "manage_settings"


# Permissions matrix
PERMISSIONS_MAP = {
    Role.SUPER_ADMIN: {
        Permission.CREATE_ADMIN,
        Permission.MANAGE_USERS,
        Permission.DELETE_USER,
        Permission.CREATE_WORKFLOW,
        Permission.EDIT_WORKFLOW,
        Permission.DELETE_WORKFLOW,
        Permission.VIEW_WORKFLOW,
        Permission.ACCESS_VAULT,
        Permission.EXPORT_DATA,
        Permission.RUN_SQL,
        Permission.TRIGGER_PANIC_MODE,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_SETTINGS,
    },
    Role.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.DELETE_USER,
        Permission.CREATE_WORKFLOW,
        Permission.EDIT_WORKFLOW,
        Permission.DELETE_WORKFLOW,
        Permission.VIEW_WORKFLOW,
        Permission.ACCESS_VAULT,
        Permission.EXPORT_DATA,
        Permission.RUN_SQL,
        Permission.TRIGGER_PANIC_MODE,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_SETTINGS,
    },
    Role.MEMBER: {
        Permission.CREATE_WORKFLOW,
        Permission.EDIT_WORKFLOW,
        Permission.DELETE_WORKFLOW,  # Own workflows only
        Permission.VIEW_WORKFLOW,
        Permission.ACCESS_VAULT,
        Permission.EXPORT_DATA,
        Permission.RUN_SQL,
    },
    Role.VIEWER: {
        Permission.VIEW_WORKFLOW,
    }
}


def get_user_db_path() -> Path:
    """
    Get path to auth database (Phase 0: use app_db for users)

    Phase 0: Returns auth_service.db_path which points to elohimos_app.db
    """
    try:
        from .auth_middleware import auth_service
    except ImportError:
        from auth_middleware import auth_service

    return auth_service.db_path


def get_user_role(user_id: str) -> Optional[Role]:
    """
    Get role for a user from auth.users table

    Phase 0: Reads from auth.users in app_db, not legacy users.db

    Args:
        user_id: User identifier

    Returns:
        Role enum or None if user not found
    """
    try:
        conn = sqlite3.connect(str(get_user_db_path()))
        cursor = conn.cursor()

        # Phase 0: Read from auth.users table
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return Role(row[0])

        # Default to MEMBER if no role set
        return Role.MEMBER

    except Exception as e:
        logger.error(f"Failed to get user role: {e}")
        return Role.MEMBER  # Fail safe to member


def has_permission(user_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission

    Args:
        user_id: User identifier
        permission: Permission to check

    Returns:
        True if user has permission
    """
    role = get_user_role(user_id)

    if not role:
        return False

    return permission in PERMISSIONS_MAP.get(role, set())


def is_last_admin() -> bool:
    """
    Check if there is only one admin left

    Returns:
        True if only one admin (super_admin or admin) exists
    """
    try:
        conn = sqlite3.connect(str(get_user_db_path()))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE role IN ('super_admin', 'admin')
        """)

        count = cursor.fetchone()[0]
        conn.close()

        return count <= 1

    except Exception as e:
        logger.error(f"Failed to check admin count: {e}")
        return True  # Fail safe to prevent deletion


def get_super_admin_count() -> int:
    """
    Get number of super admins

    Returns:
        Count of super admin users
    """
    try:
        conn = sqlite3.connect(str(get_user_db_path()))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE role = 'super_admin'
        """)

        count = cursor.fetchone()[0]
        conn.close()

        return count

    except Exception as e:
        logger.error(f"Failed to count super admins: {e}")
        return 0


def can_delete_user(current_user_id: str, target_user_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if current user can delete target user

    Args:
        current_user_id: User attempting deletion
        target_user_id: User to be deleted

    Returns:
        (can_delete, error_message) tuple
    """
    current_role = get_user_role(current_user_id)
    target_role = get_user_role(target_user_id)

    # Cannot delete yourself
    if current_user_id == target_user_id:
        if current_role == Role.SUPER_ADMIN:
            return False, "Super Admin cannot delete themselves. Transfer super admin status first."
        return False, "Cannot delete yourself"

    # Check permission
    if not has_permission(current_user_id, Permission.DELETE_USER):
        return False, "Insufficient permissions to delete users"

    # Check if last admin
    if target_role in [Role.SUPER_ADMIN, Role.ADMIN]:
        if is_last_admin():
            return False, "Cannot delete the last admin. Assign another admin first."

    return True, None


def can_change_role(current_user_id: str, target_user_id: str, new_role: Role) -> tuple[bool, Optional[str]]:
    """
    Check if current user can change target user's role

    Args:
        current_user_id: User attempting role change
        target_user_id: User whose role will change
        new_role: New role to assign

    Returns:
        (can_change, error_message) tuple
    """
    current_role = get_user_role(current_user_id)
    target_current_role = get_user_role(target_user_id)

    # Only super admin can create/manage admins
    if new_role == Role.ADMIN or new_role == Role.SUPER_ADMIN:
        if current_role != Role.SUPER_ADMIN:
            return False, "Only Super Admin can create or manage Admin roles"

    # Cannot downgrade yourself if you're super admin
    if current_user_id == target_user_id and current_role == Role.SUPER_ADMIN:
        return False, "Super Admin cannot change their own role. Transfer super admin status first."

    # Check if downgrading last admin
    if target_current_role in [Role.SUPER_ADMIN, Role.ADMIN]:
        if new_role not in [Role.SUPER_ADMIN, Role.ADMIN]:
            if is_last_admin():
                return False, "Cannot downgrade the last admin. Assign another admin first."

    # Check if changing last super admin
    if target_current_role == Role.SUPER_ADMIN and new_role != Role.SUPER_ADMIN:
        if get_super_admin_count() <= 1:
            return False, "Cannot remove the last Super Admin. Transfer super admin status first."

    return True, None


# ===== Decorators =====

def require_role(required_role: Role):
    """
    Decorator to require a minimum role for an endpoint

    Usage:
        @router.get("/admin/users")
        @require_role(Role.ADMIN)
        async def list_users():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or request
            user_id = kwargs.get('user_id') or kwargs.get('current_user_id')

            if not user_id:
                # Try to get from request if available
                request = kwargs.get('request')
                if request and isinstance(request, Request):
                    user_id = request.headers.get('X-User-ID')

            if not user_id:
                raise HTTPException(status_code=401, detail="User ID not provided")

            user_role = get_user_role(user_id)

            if not user_role:
                raise HTTPException(status_code=403, detail="User role not found")

            # Check role hierarchy
            required_level = ROLE_HIERARCHY.get(required_role, 0)
            user_level = ROLE_HIERARCHY.get(user_role, 0)

            if user_level < required_level:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required: {required_role.value}, Have: {user_role.value}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_permission(permission: str):
    """
    Decorator to require a specific permission for an endpoint

    Usage:
        @router.delete("/workflows/{workflow_id}")
        @require_permission(Permission.DELETE_WORKFLOW)
        async def delete_workflow(workflow_id: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or request
            user_id = kwargs.get('user_id') or kwargs.get('current_user_id')

            if not user_id:
                # Try to get from request
                request = kwargs.get('request')
                if request and isinstance(request, Request):
                    user_id = request.headers.get('X-User-ID')

            if not user_id:
                raise HTTPException(status_code=401, detail="User ID not provided")

            if not has_permission(user_id, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required permission: {permission}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
