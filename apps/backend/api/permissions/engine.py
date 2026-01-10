"""
Core RBAC Permission Engine

Phase 2: Salesforce-style RBAC Permission Engine
Phase 2.5: Added caching, diagnostics, and permission-set grants
Phase 3: Team-aware permission resolution

Central permission evaluation system with:
- Permission registry (permissions table)
- Permission profiles (reusable role-based permission bundles)
- Permission sets (ad-hoc grants for specific users)
- User assignments (profiles + sets)
- Evaluation engine with Founder Rights bypass
- In-memory caching with invalidation (Phase 2.5)
- Developer diagnostics for permission decisions (Phase 2.5)
- Team-aware permission context (Phase 3)

Design:
- Founder Rights (founder_rights): Full bypass, always allowed
- Super Admin: Allowed unless explicitly restricted
- Admin/Member/Guest: Controlled by profiles + permission sets
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Set, Any
from functools import lru_cache

from .types import PermissionLevel, UserPermissionContext
from .hierarchy import LEVEL_HIERARCHY
from .storage import get_db_connection
from .role_baselines import get_role_baseline

logger = logging.getLogger(__name__)

# Phase 2.5: Enable diagnostics with environment variable
DIAGNOSTICS_ENABLED = os.getenv('ELOHIMOS_PERMS_EXPLAIN', '0') == '1'


class PermissionEngine:
    """
    Central permission evaluation engine

    Loads user context, resolves effective permissions from:
    1. Default role baseline
    2. Assigned permission profiles
    3. Assigned permission sets

    Evaluates permission checks with Founder Rights bypass.
    """

    def __init__(self, db_path: Path):
        """
        Initialize permission engine

        Args:
            db_path: Path to app_db (elohimos_app.db)
        """
        self.db_path = db_path
        # Phase 2.5: In-memory cache for effective permissions
        self._permission_cache: Dict[str, Dict[str, Any]] = {}

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory and optimized settings"""
        return get_db_connection(self.db_path)

    def load_user_context(self, user_id: str, team_id: Optional[str] = None) -> UserPermissionContext:
        """
        Load complete permission context for a user

        Phase 2.5: Now with caching support
        Phase 3: Now with team-aware context

        Process:
        1. Load user data (role, job_role, team_id from users table)
        2. Load assigned profiles (user_permission_profiles) - filtered by team scope
        3. Load assigned permission sets (user_permission_sets) - filtered by team scope
        4. Resolve effective permissions:
           - Start with default role baseline
           - Apply profile grants (team-scoped or system-wide)
           - Apply permission set grants (team-scoped or system-wide)

        Args:
            user_id: User identifier
            team_id: Optional team context (Phase 3). If provided, includes team-scoped permissions.

        Returns:
            UserPermissionContext with resolved permissions
        """
        # Phase 3: Include team_id in cache key
        cache_key = f"{user_id}:{team_id or 'system'}"

        # Phase 2.5: Check cache first
        if cache_key in self._permission_cache:
            cached_perms = self._permission_cache[cache_key]
            logger.debug(f"Cache hit for {cache_key}")
        else:
            cached_perms = None

        with self._get_connection() as conn:
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
                    raise ValueError(f"User not found: {user_id}")

                ctx = UserPermissionContext(
                    user_id=user_row['user_id'],
                    username=user_row['username'],
                    role=user_row['role'] or 'member',
                    job_role=None,
                    team_id=None,
                    is_solo_mode=True,
                )

            # Step 2 & 3: Load assigned profiles and permission sets in ONE query
            # Optimized to eliminate N+1 queries using LEFT JOIN + UNION ALL
            # This is significantly faster than separate queries
            if team_id:
                cur.execute("""
                    SELECT
                        'profile' as type,
                        upp.profile_id as id
                    FROM user_permission_profiles upp
                    JOIN permission_profiles pp ON upp.profile_id = pp.profile_id
                    WHERE upp.user_id = ?
                    AND (pp.team_id IS NULL OR pp.team_id = ?)

                    UNION ALL

                    SELECT
                        'permission_set' as type,
                        ups.permission_set_id as id
                    FROM user_permission_sets ups
                    JOIN permission_sets ps ON ups.permission_set_id = ps.permission_set_id
                    WHERE ups.user_id = ?
                    AND (ps.team_id IS NULL OR ps.team_id = ?)
                    AND (ups.expires_at IS NULL OR ups.expires_at > datetime('now'))
                """, (user_id, team_id, user_id, team_id))
            else:
                # Solo mode: only system-wide
                cur.execute("""
                    SELECT
                        'profile' as type,
                        upp.profile_id as id
                    FROM user_permission_profiles upp
                    JOIN permission_profiles pp ON upp.profile_id = pp.profile_id
                    WHERE upp.user_id = ?
                    AND pp.team_id IS NULL

                    UNION ALL

                    SELECT
                        'permission_set' as type,
                        ups.permission_set_id as id
                    FROM user_permission_sets ups
                    JOIN permission_sets ps ON ups.permission_set_id = ps.permission_set_id
                    WHERE ups.user_id = ?
                    AND ps.team_id IS NULL
                    AND (ups.expires_at IS NULL OR ups.expires_at > datetime('now'))
                """, (user_id, user_id))

            # Separate results by type
            ctx.profiles = []
            ctx.permission_sets = []
            for row in cur.fetchall():
                if row['type'] == 'profile':
                    ctx.profiles.append(row['id'])
                else:
                    ctx.permission_sets.append(row['id'])

            # Step 4: Resolve effective permissions
            if cached_perms is not None:
                # Use cached permissions
                ctx.effective_permissions = cached_perms
            else:
                # Resolve from DB and cache
                ctx.effective_permissions = self._resolve_permissions(
                    conn, ctx.role, ctx.profiles, ctx.permission_sets
                )
                # Phase 3: Store in cache with team-aware key
                self._permission_cache[cache_key] = ctx.effective_permissions
                logger.debug(f"Cached permissions for {cache_key}")

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
                        except (json.JSONDecodeError, TypeError):
                            permissions[perm_key] = {}
                    else:
                        permissions[perm_key] = {}

        # Step 3: Apply permission set grants (Phase 2.5)
        # Permission sets override profiles (later wins)
        if permission_set_ids:
            set_grants = self._load_set_grants(conn, permission_set_ids)
            permissions.update(set_grants)

        return permissions

    def _load_set_grants(self, conn: sqlite3.Connection, set_ids: List[str]) -> Dict[str, Any]:
        """
        Load permission grants from permission sets (Phase 2.5)

        Args:
            conn: Database connection
            set_ids: List of permission set IDs

        Returns:
            Dict mapping permission_key -> value
        """
        grants = {}

        if not set_ids:
            return grants

        cur = conn.cursor()
        placeholders = ','.join('?' for _ in set_ids)

        cur.execute(f"""
            SELECT psp.permission_id, psp.is_granted, psp.permission_level, psp.permission_scope,
                   p.permission_key, p.permission_type
            FROM permission_set_permissions psp
            JOIN permissions p ON psp.permission_id = p.permission_id
            WHERE psp.permission_set_id IN ({placeholders})
        """, set_ids)

        for row in cur.fetchall():
            perm_key = row['permission_key']
            perm_type = row['permission_type']

            if perm_type == 'boolean':
                grants[perm_key] = bool(row['is_granted'])
            elif perm_type == 'level':
                level_str = row['permission_level']
                if level_str:
                    try:
                        grants[perm_key] = PermissionLevel(level_str)
                    except ValueError:
                        grants[perm_key] = PermissionLevel.NONE
                else:
                    grants[perm_key] = PermissionLevel.NONE
            elif perm_type == 'scope':
                scope_data = row['permission_scope']
                if scope_data:
                    try:
                        grants[perm_key] = json.loads(scope_data)
                    except (json.JSONDecodeError, TypeError):
                        grants[perm_key] = {}
                else:
                    grants[perm_key] = {}

        return grants

    def _get_role_baseline(self, role: str) -> Dict[str, any]:
        """
        Get default permission baseline for a role.

        Delegates to standalone function from role_baselines module.

        Args:
            role: User role

        Returns:
            Dict of default permissions
        """
        # Delegate to extracted module (P2 decomposition)
        return get_role_baseline(role)

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
        1. If user is founder_rights: Always allow (Founder Rights bypass)
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
        # Founder Rights: Always allow
        if user_ctx.role == 'founder_rights':
            logger.debug(f"Founder Rights bypass: {user_ctx.username} allowed {permission_key}")
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

            # Audit log - Permission check denied
            self._log_permission_check(user_ctx, permission_key, False, "permission_not_defined")

            return False

        # Boolean permission
        if isinstance(perm_value, bool):
            if not perm_value:
                self._log_permission_check(user_ctx, permission_key, False, "boolean_permission_denied")
            return perm_value

        # Level-based permission
        if isinstance(perm_value, PermissionLevel):
            if required_level is None:
                # No specific level required: just check if not NONE
                granted = perm_value != PermissionLevel.NONE
                if not granted:
                    self._log_permission_check(user_ctx, permission_key, False, f"insufficient_level_{perm_value}")
                return granted

            try:
                required = PermissionLevel(required_level)
                user_level_num = LEVEL_HIERARCHY.get(perm_value, 0)
                required_level_num = LEVEL_HIERARCHY.get(required, 0)
                granted = user_level_num >= required_level_num

                if not granted:
                    self._log_permission_check(
                        user_ctx, permission_key, False,
                        f"insufficient_level_has_{perm_value}_requires_{required_level}"
                    )

                return granted
            except ValueError:
                logger.warning(f"Invalid permission level: {required_level}")
                self._log_permission_check(user_ctx, permission_key, False, "invalid_required_level")
                return False

        # Scope-based permission (simplified for v1)
        if isinstance(perm_value, dict):
            # For v1: if scope exists, permission is granted (scope filtering done at service level)
            return bool(perm_value)

        # Unknown type: deny
        return False

    def _log_permission_check(
        self,
        user_ctx: UserPermissionContext,
        permission_key: str,
        granted: bool,
        reason: str
    ) -> None:
        """
        Log permission check to audit log (Phase 5.1)

        Only logs denials to avoid excessive audit log growth.
        Grants are only logged for sensitive operations.

        Args:
            user_ctx: User permission context
            permission_key: Permission key being checked
            granted: Whether permission was granted
            reason: Reason for decision
        """
        # Only log denials (grants would be too noisy)
        if not granted:
            try:
                from audit_logger import audit_log_sync, AuditAction

                audit_log_sync(
                    user_id=user_ctx.user_id,
                    action=AuditAction.PERMISSION_CHECK_DENIED,
                    resource="permission",
                    resource_id=permission_key,
                    details={
                        "permission_key": permission_key,
                        "reason": reason,
                        "role": user_ctx.role
                    }
                )
            except Exception as e:
                # Don't fail permission check if audit logging fails
                logger.error(f"Failed to audit log permission check: {e}")

    def invalidate_user_permissions(self, user_id: str) -> None:
        """
        Invalidate cached permissions for a user (Phase 2.5 + Phase 3)

        Call this when:
        - User's role changes
        - User is assigned/unassigned a profile
        - User is assigned/unassigned a permission set
        - Profile or permission set grants are modified
        - User joins/leaves a team (Phase 3)
        - Team membership role changes (Phase 3)

        Phase 3: Clears all team contexts for the user, not just solo mode.

        Args:
            user_id: User identifier
        """
        # Phase 3: Clear all cache entries for this user across all team contexts
        # Cache keys are in format: "{user_id}:{team_id or 'system'}"
        keys_to_delete = [k for k in self._permission_cache.keys() if k.startswith(f"{user_id}:")]
        for key in keys_to_delete:
            del self._permission_cache[key]

        if keys_to_delete:
            logger.info(f"Invalidated {len(keys_to_delete)} permission cache entries for user {user_id}")

        # Also clear from DB cache if present
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM user_permissions_cache WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            logger.debug(f"Cleared DB cache for user {user_id}")
        except sqlite3.OperationalError:
            # Table doesn't exist yet; skip
            pass

    def explain_permission(
        self,
        user_ctx: UserPermissionContext,
        permission_key: str,
        required_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain why a permission was granted or denied (Phase 2.5)

        Only enabled when ELOHIMOS_PERMS_EXPLAIN=1 environment variable is set.
        Never includes secrets or sensitive data.

        Args:
            user_ctx: User permission context
            permission_key: Permission to explain
            required_level: Required level (if applicable)

        Returns:
            Dict with explanation:
            - decision: "allow" or "deny"
            - reason: Human-readable explanation
            - role: User's role
            - profiles: List of assigned profiles
            - permission_sets: List of assigned permission sets
            - effective_value: The resolved permission value
            - required_level: Required level (if applicable)
        """
        if not DIAGNOSTICS_ENABLED:
            return {
                "error": "Diagnostics disabled. Set ELOHIMOS_PERMS_EXPLAIN=1 to enable."
            }

        decision = self.has_permission(user_ctx, permission_key, required_level)
        effective_value = user_ctx.effective_permissions.get(permission_key)

        explanation = {
            "decision": "allow" if decision else "deny",
            "permission_key": permission_key,
            "user_id": user_ctx.user_id,
            "username": user_ctx.username,
            "role": user_ctx.role,
            "profiles": user_ctx.profiles,
            "permission_sets": user_ctx.permission_sets,
            "effective_value": str(effective_value) if effective_value is not None else None,
            "required_level": required_level,
        }

        # Add reason based on decision logic
        if user_ctx.role == 'founder_rights':
            explanation["reason"] = "Founder Rights bypass - Founder Rights always allowed"
        elif user_ctx.role == 'super_admin':
            if decision:
                explanation["reason"] = "Super Admin allowed (not explicitly denied)"
            else:
                explanation["reason"] = "Super Admin explicitly denied"
        elif effective_value is None:
            explanation["reason"] = "Permission not defined in role/profiles/sets"
        elif isinstance(effective_value, bool):
            explanation["reason"] = f"Boolean permission: {effective_value}"
        elif isinstance(effective_value, PermissionLevel):
            if required_level:
                user_level = LEVEL_HIERARCHY.get(effective_value, 0)
                req_level = LEVEL_HIERARCHY.get(PermissionLevel(required_level), 0)
                explanation["reason"] = f"Level permission: user has {effective_value} (level {user_level}), required {required_level} (level {req_level})"
            else:
                explanation["reason"] = f"Level permission: user has {effective_value}"
        elif isinstance(effective_value, dict):
            explanation["reason"] = "Scope permission: granted with scope data"
        else:
            explanation["reason"] = "Unknown permission type"

        return explanation


# Global permission engine instance
_permission_engine: Optional[PermissionEngine] = None


def get_permission_engine() -> PermissionEngine:
    """Get or initialize global permission engine"""
    global _permission_engine

    if _permission_engine is None:
        try:
            from ..auth_middleware import auth_service
        except ImportError:
            from auth_middleware import auth_service

        _permission_engine = PermissionEngine(auth_service.db_path)

    return _permission_engine


def get_effective_permissions(user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper function to get effective permissions for a user (Phase 3)

    Args:
        user_id: User identifier
        team_id: Optional team context

    Returns:
        Dict mapping permission_key -> value (bool, PermissionLevel, or scope dict)
    """
    engine = get_permission_engine()
    user_ctx = engine.load_user_context(user_id, team_id=team_id)
    return user_ctx.effective_permissions
