"""
Permissions Package

Centralized RBAC (Role-Based Access Control) permission system for ElohimOS.

This package provides:
- Core RBAC engine with permission evaluation
- FastAPI decorators for route protection
- Permission management admin/service functions
- Type definitions and hierarchy

Public API:
- Types: PermissionLevel, UserPermissionContext
- Hierarchy: LEVEL_HIERARCHY
- Engine: PermissionEngine, get_permission_engine, get_effective_permissions
- Decorators: require_perm, require_perm_team
- Admin functions: Available via .admin module
"""

from .types import PermissionLevel, UserPermissionContext
from .hierarchy import LEVEL_HIERARCHY
from .engine import PermissionEngine, get_permission_engine, get_effective_permissions
from .decorators import require_perm, require_perm_team
from . import admin
from . import storage

__all__ = [
    # Types
    "PermissionLevel",
    "UserPermissionContext",
    # Hierarchy
    "LEVEL_HIERARCHY",
    # Engine
    "PermissionEngine",
    "get_permission_engine",
    "get_effective_permissions",
    # Decorators
    "require_perm",
    "require_perm_team",
    # Submodules
    "admin",
    "storage",
]
