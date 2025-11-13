"""
Team Service Package

Modular team service for team management, member operations,
invitations, roles, permissions, and team vault.

Public API compatible with existing imports:
    from api.services.team import get_team_manager, is_team_member, require_team_admin

Usage:
    from api.services.team import get_team_manager, is_team_member
    from api.services.team.core import TeamManager
"""

# Re-export core TeamManager
from .core import TeamManager

# Re-export helper functions (most commonly used)
from .helpers import (
    get_team_manager,
    is_team_member,
    require_team_admin,
    _get_app_conn,
)

__all__ = [
    # Core
    "TeamManager",
    # Helpers
    "get_team_manager",
    "is_team_member",
    "require_team_admin",
    "_get_app_conn",
]
