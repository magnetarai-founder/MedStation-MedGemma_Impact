"""
Compatibility Shim for RBAC Permission Engine

The implementation now lives in the `api.permissions` package:
- api.permissions.types: PermissionLevel, UserPermissionContext
- api.permissions.hierarchy: LEVEL_HIERARCHY
- api.permissions.engine: PermissionEngine, get_permission_engine, get_effective_permissions
- api.permissions.decorators: require_perm, require_perm_team
- api.permissions.admin: High-level admin/service functions
- api.permissions.storage: DB connection helpers

This module re-exports the public API for backwards compatibility.
All existing imports from `api.permission_engine` will continue to work.

Original implementation: Phase 2 (Salesforce-style RBAC), Phase 2.5 (caching), Phase 3 (team context)
Refactored: Phase 6.1 (modular permissions package)
"""

from typing import Any, Dict, Optional

# Re-export from modular permissions package
try:
    from api.permissions import (
        PermissionLevel,
        UserPermissionContext,
        LEVEL_HIERARCHY,
        PermissionEngine,
        get_permission_engine,
        get_effective_permissions,
        require_perm,
        require_perm_team,
    )
except ImportError:
    from permissions import (
        PermissionLevel,
        UserPermissionContext,
        LEVEL_HIERARCHY,
        PermissionEngine,
        get_permission_engine,
        get_effective_permissions,
        require_perm,
        require_perm_team,
    )

# For backwards compatibility with code that imports has_permission directly
def has_permission(user_ctx, permission_key: str, required_level: Optional[str] = None) -> bool:
    """
    Compatibility wrapper for has_permission method.

    Args:
        user_ctx: UserPermissionContext
        permission_key: Permission to check
        required_level: Optional level requirement

    Returns:
        True if user has permission, False otherwise
    """
    engine = get_permission_engine()
    return engine.has_permission(user_ctx, permission_key, required_level=required_level)


__all__ = [
    "PermissionLevel",
    "UserPermissionContext",
    "LEVEL_HIERARCHY",
    "PermissionEngine",
    "get_permission_engine",
    "get_effective_permissions",
    "require_perm",
    "require_perm_team",
    "has_permission",
]
