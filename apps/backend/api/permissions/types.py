"""
Permission Types

Core type definitions for the RBAC permission system.
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


class PermissionLevel(str, Enum):
    """Permission levels for hierarchical permissions"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


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
    effective_permissions: Dict[str, Any] = None

    def __post_init__(self):
        if self.profiles is None:
            self.profiles = []
        if self.permission_sets is None:
            self.permission_sets = []
        if self.effective_permissions is None:
            self.effective_permissions = {}
