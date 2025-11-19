"""
Permission Hierarchy

Defines the hierarchical ordering of permission levels.
"""

from .types import PermissionLevel


# Level hierarchy (higher number = more access)
LEVEL_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.ADMIN: 3,
}
