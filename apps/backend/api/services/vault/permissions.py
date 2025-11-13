"""
Vault Permissions

Permission checking and team membership helpers for vault operations.
"""

import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def check_vault_permission(user_id: str, permission: str, team_id: Optional[str] = None) -> None:
    """
    Check if user has vault permission.

    Args:
        user_id: User ID
        permission: Permission key (e.g., 'vault.use', 'vault.documents.create')
        team_id: Optional team ID for team-scoped operations

    Raises:
        HTTPException: If user lacks permission
    """
    # Import here to avoid circular dependencies
    from api.permission_engine import require_perm, require_perm_team

    if team_id:
        require_perm_team(user_id, permission, team_id)
    else:
        require_perm(user_id, permission)


def check_team_membership(user_id: str, team_id: str) -> bool:
    """
    Check if user is a member of the team.

    Args:
        user_id: User ID
        team_id: Team ID

    Returns:
        True if user is team member
    """
    # Import here to avoid circular dependencies
    from api.team_service import is_team_member

    return is_team_member(user_id, team_id)


def require_vault_access(user_id: str, vault_type: str, team_id: Optional[str] = None) -> None:
    """
    Require user has access to specified vault type.

    Args:
        user_id: User ID
        vault_type: Vault type ('real' or 'decoy')
        team_id: Optional team ID

    Raises:
        HTTPException: If access denied
    """
    permission = 'vault.use'
    check_vault_permission(user_id, permission, team_id)
