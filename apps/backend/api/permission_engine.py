"""
Phase 2: Salesforce-style RBAC Permission Engine

Central permission evaluation system with:
- Permission registry (permissions table)
- Permission profiles (reusable role-based permission bundles)
- Permission sets (ad-hoc grants for specific users)
- User assignments (profiles + sets)
- Evaluation engine with God Rights bypass

Design:
- Founder Rights (founder_rights): Full bypass, always allowed
- Super Admin: Allowed unless explicitly restricted
- Admin/Member/Guest: Controlled by profiles + permission sets
"""

import sqlite3
import logging
from enum import Enum
from typing import Optional, Dict, List, Set, Callable
from functools import wraps
from fastapi import HTTPException, Depends
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """Permission levels for hierarchical permissions"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


# Level hierarchy (higher number = more access)
LEVEL_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.ADMIN: 3,
}


@dataclass
class UserPermissionContext:
    """
    Complete permission context for a user

    Attributes:
        user_id: User identifier
        username: Username
        role: Base role (founder_rights, super_admin, admin, member, guest)
        job_role: Optional job role (e.g., "Product Manager")
        team_id: Optional team identifier
        is_solo_mode: Whether user is in solo mode (no team)
        profiles: List of assigned profile IDs
        permission_sets: List of assigned permission set IDs
        effective_permissions: Resolved permission map (permission_key -> value)
            - For boolean perms: True/False
            - For level perms: PermissionLevel enum
            - For scope perms: dict with scope data
    """
    user_id: str
    username: str
    role: str
    job_role: Optional[str] = None
    team_id: Optional[str] = None
    is_solo_mode: bool = True
    profiles: List[str] = None
    permission_sets: List[str] = None
    effective_permissions: Dict[str, any] = None

    def __post_init__(self):
        if self.profiles is None:
            self.profiles = []
        if self.permission_sets is None:
            self.permission_sets = []
        if self.effective_permissions is None:
            self.effective_permissions = {}


class PermissionEngine:
    """
    Central permission evaluation engine

    Loads user context, resolves effective permissions from:
    1. Default role baseline
    2. Assigned permission profiles
    3. Assigned permission sets

    Evaluates permission checks with God Rights bypass.
    """

    def __init__(self, db_path: Path):
        """
        Initialize permission engine

        Args:
            db_path: Path to app_db (elohimos_app.db)
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def load_user_context(self, user_id: str) -> UserPermissionContext:
        """
        Load complete permission context for a user

        Process:
        1. Load user data (role, job_role, team_id from users table)
        2. Load assigned profiles (user_permission_profiles)
        3. Load assigned permission sets (user_permission_sets)
        4. Resolve effective permissions:
           - Start with default role baseline
           - Apply profile grants (override)
           - Apply permission set grants (override)

        Args:
            user_id: User identifier

        Returns:
            UserPermissionContext with resolved permissions
        """
        conn = self._get_connection()
        cur = conn.cursor()

        # Step 1: Load user data
        # Note: team_id and job_role may not exist yet; handle gracefully
        try:
            cur.execute("""
                SELECT user_id, username, role, job_role, team_id
                FROM users
                WHERE user_id = ?
            """, (user_id,))
            user_row = cur.fetchone()

            if not user_row:
                conn.close()
                raise ValueError(f"User not found: {user_id}")

            ctx = UserPermissionContext(
                user_id=user_row['user_id'],
                username=user_row['username'],
                role=user_row['role'] or 'member',
                job_role=user_row['job_role'] if 'job_role' in user_row.keys() else None,
                team_id=user_row['team_id'] if 'team_id' in user_row.keys() else None,
                is_solo_mode=(user_row['team_id'] if 'team_id' in user_row.keys() else None) is None,
            )
        except sqlite3.OperationalError as e:
            # Columns don't exist yet; load minimal user data
            logger.warning(f"Loading user context with minimal schema (team_id/job_role missing): {e}")
            cur.execute("""
                SELECT user_id, username, role
                FROM users
                WHERE user_id = ?
            """, (user_id,))
            user_row = cur.fetchone()

            if not user_row:
                conn.close()
                raise ValueError(f"User not found: {user_id}")

            ctx = UserPermissionContext(
                user_id=user_row['user_id'],
                username=user_row['username'],
                role=user_row['role'] or 'member',
                job_role=None,
                team_id=None,
                is_solo_mode=True,
            )

        # Step 2: Load assigned profiles
        cur.execute("""
            SELECT profile_id
            FROM user_permission_profiles
            WHERE user_id = ?
        """, (user_id,))

        ctx.profiles = [row['profile_id'] for row in cur.fetchall()]

        # Step 3: Load assigned permission sets (that haven't expired)
        cur.execute("""
            SELECT permission_set_id
            FROM user_permission_sets
            WHERE user_id = ?
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (user_id,))

        ctx.permission_sets = [row['permission_set_id'] for row in cur.fetchall()]

        # Step 4: Resolve effective permissions
        ctx.effective_permissions = self._resolve_permissions(
            conn, ctx.role, ctx.profiles, ctx.permission_sets
        )

        conn.close()
        return ctx

    def _resolve_permissions(
        self,
        conn: sqlite3.Connection,
        role: str,
        profile_ids: List[str],
        permission_set_ids: List[str]
    ) -> Dict[str, any]:
        """
        Resolve effective permissions from role + profiles + sets

        Resolution order:
        1. Default role baseline (hardcoded)
        2. Profile grants (from DB)
        3. Permission set grants (from DB) - currently simplified to profile-style grants

        Later grants override earlier ones.

        Args:
            conn: Database connection
            role: User's base role
            profile_ids: List of assigned profile IDs
            permission_set_ids: List of assigned permission set IDs

        Returns:
            Dict mapping permission_key -> value (bool, PermissionLevel, or dict for scope)
        """
        permissions = {}

        # Step 1: Default role baseline
        permissions.update(self._get_role_baseline(role))

        # Step 2: Apply profile grants
        if profile_ids:
            cur = conn.cursor()
            placeholders = ','.join('?' for _ in profile_ids)

            cur.execute(f"""
                SELECT pp.permission_id, pp.is_granted, pp.permission_level, pp.permission_scope,
                       p.permission_key, p.permission_type
                FROM profile_permissions pp
                JOIN permissions p ON pp.permission_id = p.permission_id
                JOIN permission_profiles prof ON pp.profile_id = prof.profile_id
                WHERE pp.profile_id IN ({placeholders})
                AND prof.is_active = 1
            """, profile_ids)

            for row in cur.fetchall():
                perm_key = row['permission_key']
                perm_type = row['permission_type']

                if perm_type == 'boolean':
                    permissions[perm_key] = bool(row['is_granted'])
                elif perm_type == 'level':
                    level_str = row['permission_level']
                    if level_str:
                        try:
                            permissions[perm_key] = PermissionLevel(level_str)
                        except ValueError:
                            permissions[perm_key] = PermissionLevel.NONE
                    else:
                        permissions[perm_key] = PermissionLevel.NONE
                elif perm_type == 'scope':
                    # Scope-based: store scope dict (future expansion)
                    import json
                    scope_data = row['permission_scope']
                    if scope_data:
                        try:
                            permissions[perm_key] = json.loads(scope_data)
                        except:
                            permissions[perm_key] = {}
                    else:
                        permissions[perm_key] = {}

        # Step 3: Apply permission set grants
        # For Phase 2 v1, permission sets are simplified - they could have their own grants table
        # For now, we just track assignment; expand this later if needed

        return permissions

    def _get_role_baseline(self, role: str) -> Dict[str, any]:
        """
        Get default permission baseline for a role

        Baseline permissions before any profiles/sets are applied:
        - founder_rights: N/A (bypasses all checks)
        - super_admin: All features + resources (some system perms)
        - admin: Most features + resources, limited system perms
        - member: Core features (chat, vault, workflows, docs), no system perms
        - guest: Read-only access

        Args:
            role: User role

        Returns:
            Dict of default permissions
        """
        # For founder_rights, baseline doesn't matter (always bypassed)
        if role == 'founder_rights':
            return {}

        # Super Admin: Grant everything by default
        if role == 'super_admin':
            return {
                # Features
                'chat.use': True,
                'vault.use': True,
                'workflows.use': True,
                'docs.use': True,
                'data.run_sql': True,
                'data.export': True,
                'insights.use': True,
                'code.use': True,
                'team.use': True,
                'panic.use': True,
                'backups.use': True,

                # Vault resources (level-based)
                'vault.documents.create': PermissionLevel.ADMIN,
                'vault.documents.read': PermissionLevel.ADMIN,
                'vault.documents.update': PermissionLevel.ADMIN,
                'vault.documents.delete': PermissionLevel.ADMIN,
                'vault.documents.share': PermissionLevel.ADMIN,

                # Workflow resources
                'workflows.create': PermissionLevel.ADMIN,
                'workflows.view': PermissionLevel.ADMIN,
                'workflows.edit': PermissionLevel.ADMIN,
                'workflows.delete': PermissionLevel.ADMIN,
                'workflows.manage': PermissionLevel.ADMIN,

                # Docs resources
                'docs.create': PermissionLevel.ADMIN,
                'docs.read': PermissionLevel.ADMIN,
                'docs.update': PermissionLevel.ADMIN,
                'docs.delete': PermissionLevel.ADMIN,
                'docs.share': PermissionLevel.ADMIN,

                # System permissions
                'system.view_admin_dashboard': True,
                'system.manage_users': True,
                'system.view_audit_logs': True,
                'system.manage_permissions': True,
                'system.manage_settings': True,
            }

        # Admin: Most features, limited system perms
        if role == 'admin':
            return {
                # Features
                'chat.use': True,
                'vault.use': True,
                'workflows.use': True,
                'docs.use': True,
                'data.run_sql': True,
                'data.export': True,
                'insights.use': True,
                'code.use': True,
                'team.use': True,
                'panic.use': True,
                'backups.use': True,

                # Vault resources (write level)
                'vault.documents.create': PermissionLevel.WRITE,
                'vault.documents.read': PermissionLevel.WRITE,
                'vault.documents.update': PermissionLevel.WRITE,
                'vault.documents.delete': PermissionLevel.WRITE,
                'vault.documents.share': PermissionLevel.READ,

                # Workflow resources
                'workflows.create': PermissionLevel.WRITE,
                'workflows.view': PermissionLevel.WRITE,
                'workflows.edit': PermissionLevel.WRITE,
                'workflows.delete': PermissionLevel.WRITE,
                'workflows.manage': PermissionLevel.READ,

                # Docs resources
                'docs.create': PermissionLevel.WRITE,
                'docs.read': PermissionLevel.WRITE,
                'docs.update': PermissionLevel.WRITE,
                'docs.delete': PermissionLevel.WRITE,
                'docs.share': PermissionLevel.READ,

                # System permissions (limited)
                'system.view_admin_dashboard': True,
                'system.manage_users': True,
                'system.view_audit_logs': True,
                'system.manage_permissions': False,  # Not by default
                'system.manage_settings': True,
            }

        # Member: Core features, own resources
        if role == 'member':
            return {
                # Features
                'chat.use': True,
                'vault.use': True,
                'workflows.use': True,
                'docs.use': True,
                'data.run_sql': True,
                'data.export': False,  # Not by default
                'insights.use': False,
                'code.use': False,
                'team.use': False,
                'panic.use': False,
                'backups.use': False,

                # Vault resources (read/write on own)
                'vault.documents.create': PermissionLevel.WRITE,
                'vault.documents.read': PermissionLevel.WRITE,
                'vault.documents.update': PermissionLevel.WRITE,
                'vault.documents.delete': PermissionLevel.WRITE,
                'vault.documents.share': PermissionLevel.NONE,

                # Workflow resources
                'workflows.create': PermissionLevel.WRITE,
                'workflows.view': PermissionLevel.WRITE,
                'workflows.edit': PermissionLevel.WRITE,
                'workflows.delete': PermissionLevel.READ,  # Own only
                'workflows.manage': PermissionLevel.NONE,

                # Docs resources
                'docs.create': PermissionLevel.WRITE,
                'docs.read': PermissionLevel.WRITE,
                'docs.update': PermissionLevel.WRITE,
                'docs.delete': PermissionLevel.WRITE,
                'docs.share': PermissionLevel.NONE,

                # System permissions (none)
                'system.view_admin_dashboard': False,
                'system.manage_users': False,
                'system.view_audit_logs': False,
                'system.manage_permissions': False,
                'system.manage_settings': False,
            }

        # Guest: Read-only
        if role == 'guest':
            return {
                # Features (very limited)
                'chat.use': True,
                'vault.use': False,
                'workflows.use': False,
                'docs.use': True,
                'data.run_sql': False,
                'data.export': False,
                'insights.use': False,
                'code.use': False,
                'team.use': False,
                'panic.use': False,
                'backups.use': False,

                # Vault resources (none)
                'vault.documents.create': PermissionLevel.NONE,
                'vault.documents.read': PermissionLevel.READ,
                'vault.documents.update': PermissionLevel.NONE,
                'vault.documents.delete': PermissionLevel.NONE,
                'vault.documents.share': PermissionLevel.NONE,

                # Workflow resources (read-only)
                'workflows.create': PermissionLevel.NONE,
                'workflows.view': PermissionLevel.READ,
                'workflows.edit': PermissionLevel.NONE,
                'workflows.delete': PermissionLevel.NONE,
                'workflows.manage': PermissionLevel.NONE,

                # Docs resources (read-only)
                'docs.create': PermissionLevel.NONE,
                'docs.read': PermissionLevel.READ,
                'docs.update': PermissionLevel.NONE,
                'docs.delete': PermissionLevel.NONE,
                'docs.share': PermissionLevel.NONE,

                # System permissions (none)
                'system.view_admin_dashboard': False,
                'system.manage_users': False,
                'system.view_audit_logs': False,
                'system.manage_permissions': False,
                'system.manage_settings': False,
            }

        # Default: Empty (deny all)
        return {}

    def has_permission(
        self,
        user_ctx: UserPermissionContext,
        permission_key: str,
        required_level: Optional[str] = None,
        scope: Optional[dict] = None
    ) -> bool:
        """
        Check if user has a specific permission

        Logic:
        1. If user is founder_rights: Always allow (God Rights bypass)
        2. If user is super_admin: Allow unless explicitly forbidden
        3. For boolean permissions: Check if granted
        4. For level permissions: Check if user's level >= required level
        5. For scope permissions: Check scope intersection (simplified for v1)

        Args:
            user_ctx: User permission context
            permission_key: Permission to check (e.g., "vault.documents.read")
            required_level: Optional level requirement ("read", "write", "admin")
            scope: Optional scope constraints (future use)

        Returns:
            True if permission granted, False otherwise
        """
        # God Rights: Always allow
        if user_ctx.role == 'founder_rights':
            logger.debug(f"God Rights bypass: {user_ctx.username} allowed {permission_key}")
            return True

        # Super Admin: Allow unless explicitly forbidden
        if user_ctx.role == 'super_admin':
            # Check if explicitly forbidden in effective_permissions
            perm_value = user_ctx.effective_permissions.get(permission_key)
            if perm_value is False or perm_value == PermissionLevel.NONE:
                logger.debug(f"Super Admin explicitly denied: {permission_key}")
                return False
            # Otherwise allow
            logger.debug(f"Super Admin allowed: {permission_key}")
            return True

        # Get permission value from effective permissions
        perm_value = user_ctx.effective_permissions.get(permission_key)

        if perm_value is None:
            # Permission not defined: deny
            logger.debug(f"Permission not defined for {user_ctx.username}: {permission_key}")
            return False

        # Boolean permission
        if isinstance(perm_value, bool):
            return perm_value

        # Level-based permission
        if isinstance(perm_value, PermissionLevel):
            if required_level is None:
                # No specific level required: just check if not NONE
                return perm_value != PermissionLevel.NONE

            try:
                required = PermissionLevel(required_level)
                user_level_num = LEVEL_HIERARCHY.get(perm_value, 0)
                required_level_num = LEVEL_HIERARCHY.get(required, 0)
                return user_level_num >= required_level_num
            except ValueError:
                logger.warning(f"Invalid permission level: {required_level}")
                return False

        # Scope-based permission (simplified for v1)
        if isinstance(perm_value, dict):
            # For v1: if scope exists, permission is granted (scope filtering done at service level)
            return bool(perm_value)

        # Unknown type: deny
        return False


# Global permission engine instance
_permission_engine: Optional[PermissionEngine] = None


def get_permission_engine() -> PermissionEngine:
    """Get or initialize global permission engine"""
    global _permission_engine

    if _permission_engine is None:
        try:
            from .auth_middleware import auth_service
        except ImportError:
            from auth_middleware import auth_service

        _permission_engine = PermissionEngine(auth_service.db_path)

    return _permission_engine


# ===== FastAPI Decorators =====

def require_perm(permission_key: str, level: Optional[str] = None):
    """
    FastAPI decorator to require a specific permission

    Usage:
        from .auth_middleware import get_current_user

        @router.get("/documents")
        @require_perm("vault.documents.read", level="read")
        async def list_documents(current_user: Dict = Depends(get_current_user)):
            ...

    Args:
        permission_key: Permission to check (e.g., "vault.documents.read")
        level: Optional level requirement ("read", "write", "admin")

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (must be injected by get_current_user dependency)
            current_user = kwargs.get('current_user')

            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            user_id = current_user.get('user_id')
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication: user_id missing"
                )

            # Load user context
            engine = get_permission_engine()
            try:
                user_ctx = engine.load_user_context(user_id)
            except ValueError as e:
                logger.error(f"Failed to load user context: {e}")
                raise HTTPException(
                    status_code=403,
                    detail="User context not found"
                )

            # Check permission
            if not engine.has_permission(user_ctx, permission_key, required_level=level):
                logger.warning(
                    f"Permission denied: {user_ctx.username} ({user_ctx.role}) "
                    f"attempted {permission_key} (level={level})"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required permission: {permission_key}" +
                           (f" (level: {level})" if level else "")
                )

            # Permission granted: proceed
            return await func(*args, **kwargs)

        return wrapper
    return decorator
