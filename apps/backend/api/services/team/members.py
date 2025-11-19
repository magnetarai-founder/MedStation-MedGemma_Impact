"""
Team Service Members Module

Member management operations including:
- Getting team members and user teams
- Joining teams
- Role updates
- Last seen tracking
- Job role management
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from .storage import (
    get_team_members_list,
    get_user_teams_list,
    add_member_record,
    is_team_member,
    get_member_role,
    update_member_role_db,
    update_last_seen_db,
    get_member_joined_at,
    update_job_role_db,
    get_member_job_role_db,
    count_members_by_role,
    count_team_members,
)
from .types import SuccessResult

logger = logging.getLogger(__name__)


# ========================================================================
# MEMBER RETRIEVAL
# ========================================================================

def get_team_members(team_id: str) -> List[Dict]:
    """Get all members of a team"""
    return get_team_members_list(team_id)


def get_user_teams(user_id: str) -> List[Dict]:
    """Get all teams a user is a member of"""
    return get_user_teams_list(user_id)


# ========================================================================
# MEMBER OPERATIONS
# ========================================================================

def join_team(team_id: str, user_id: str, role: str = 'member') -> bool:
    """
    Add user to team

    Args:
        team_id: Team to join
        user_id: User joining
        role: Role to assign (default: member)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if user is already a member
        if is_team_member(team_id, user_id):
            logger.warning(f"User {user_id} already member of team {team_id}")
            return False

        # Add user as member
        success = add_member_record(team_id, user_id, role)
        if success:
            logger.info(f"User {user_id} joined team {team_id} as {role}")
        return success

    except Exception as e:
        logger.error(f"Failed to join team: {e}")
        return False


def update_member_role_impl(
    manager,  # TeamManager instance
    team_id: str,
    user_id: str,
    new_role: str,
    requesting_user_role: str = None,
    requesting_user_id: str = None
) -> SuccessResult:
    """
    Update a team member's role with validation

    Args:
        manager: TeamManager instance for accessing other methods
        team_id: Team ID
        user_id: User whose role to update
        new_role: New role to assign
        requesting_user_role: Role of user making the request (for Founder Rights check)
        requesting_user_id: ID of user making the request (for Founder Rights protection)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Check if user is member
        current_role = get_member_role(team_id, user_id)
        if not current_role:
            return False, f"User {user_id} is not a member of team {team_id}"

        # Founder Rights Protection (Phase 6.1)
        # Check if target user has Founder Rights - only Founder Rights can modify Founder Rights users
        target_has_god_rights, _ = manager.check_god_rights(user_id)
        if target_has_god_rights:
            # Check if requester has Founder Rights
            requester_has_god_rights = False
            if requesting_user_id:
                requester_has_god_rights, _ = manager.check_god_rights(requesting_user_id)
            elif requesting_user_role == 'god_rights':
                requester_has_god_rights = True

            if not requester_has_god_rights:
                return False, "Only users with Founder Rights can modify other Founder Rights users"

        # If promoting to Super Admin, check limits
        if new_role == 'super_admin' and current_role != 'super_admin':
            can_promote, reason = manager.can_promote_to_super_admin(team_id, requesting_user_role)
            if not can_promote:
                return False, reason

        # If demoting a Super Admin, check if they're the last one
        if current_role == 'super_admin' and new_role != 'super_admin':
            # Founder Rights can override
            if requesting_user_role != 'god_rights':
                current_super_admins = count_members_by_role(team_id, 'super_admin')
                if current_super_admins <= 1:
                    return False, "You're the last Super Admin. Promote an Admin first."

        # Update role
        success = update_member_role_db(team_id, user_id, new_role)
        if success:
            logger.info(f"Updated {user_id} role from {current_role} to {new_role} in team {team_id}")
            return True, f"Role updated to {new_role}"
        else:
            return False, "Failed to update role in database"

    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        return False, str(e)


# Keep old name for backward compatibility, but it now requires manager
def update_member_role(
    team_id: str,
    user_id: str,
    new_role: str,
    requesting_user_role: str = None,
    requesting_user_id: str = None,
    manager=None
) -> SuccessResult:
    """Backward-compatible wrapper - requires manager parameter"""
    if manager is None:
        raise ValueError("update_member_role requires manager parameter")
    return update_member_role_impl(manager, team_id, user_id, new_role, requesting_user_role, requesting_user_id)


def update_last_seen(team_id: str, user_id: str) -> SuccessResult:
    """
    Update last_seen timestamp for a team member (Phase 3.3)

    Should be called on every user activity to track online status

    Args:
        team_id: Team ID
        user_id: User ID to update

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        success = update_last_seen_db(team_id, user_id, datetime.now())

        if not success:
            return False, "User not found in team"

        return True, "Last seen updated"

    except Exception as e:
        logger.error(f"Failed to update last_seen: {e}")
        return False, str(e)


def get_days_since_joined(team_id: str, user_id: str) -> Optional[int]:
    """
    Calculate days since user joined the team

    Args:
        team_id: Team ID
        user_id: User ID

    Returns:
        Number of days since joining, or None if user not found
    """
    try:
        joined_at_str = get_member_joined_at(team_id, user_id)
        if not joined_at_str:
            return None

        joined_at = datetime.fromisoformat(joined_at_str)
        days_elapsed = (datetime.now() - joined_at).days

        return days_elapsed

    except Exception as e:
        logger.error(f"Failed to calculate days since joined: {e}")
        return None


# ========================================================================
# JOB ROLE MANAGEMENT (Phase 5.1)
# ========================================================================

def update_job_role(team_id: str, user_id: str, job_role: str) -> SuccessResult:
    """
    Update a team member's job role (Phase 5.1)

    Job roles are used for workflow permissions and queue access control.
    Valid roles: doctor, pastor, nurse, admin_staff, volunteer, custom, unassigned

    Args:
        team_id: Team ID
        user_id: User ID to update
        job_role: New job role

    Returns:
        Tuple of (success: bool, message: str)
    """
    valid_job_roles = ['doctor', 'pastor', 'nurse', 'admin_staff', 'volunteer', 'unassigned']

    # Allow custom job roles (anything not in the predefined list that's not 'unassigned')
    if job_role not in valid_job_roles and job_role != 'unassigned':
        # Treat as custom role, validate it's reasonable
        if len(job_role) > 50:
            return False, "Custom job role must be 50 characters or less"
        if not job_role.strip():
            return False, "Job role cannot be empty"

    try:
        # Verify user exists in team
        if not is_team_member(team_id, user_id):
            return False, f"User {user_id} not found in team"

        # Update job role
        success = update_job_role_db(team_id, user_id, job_role)

        if success:
            logger.info(f"Updated job role for {user_id} in team {team_id} to {job_role}")
            return True, f"Job role updated to {job_role}"
        else:
            return False, "Failed to update job role in database"

    except Exception as e:
        logger.error(f"Failed to update job role: {e}")
        return False, str(e)


def get_member_job_role(team_id: str, user_id: str) -> Optional[str]:
    """
    Get a team member's job role (Phase 5.1)

    Args:
        team_id: Team ID
        user_id: User ID

    Returns:
        Job role string or None if not found
    """
    return get_member_job_role_db(team_id, user_id)


# ========================================================================
# ROLE/SIZE UTILITIES
# ========================================================================

def count_role(team_id: str, role: str) -> int:
    """Count number of members with a specific role"""
    return count_members_by_role(team_id, role)


def count_super_admins(team_id: str) -> int:
    """Count number of super admins in a team"""
    return count_members_by_role(team_id, 'super_admin')


def get_team_size(team_id: str) -> int:
    """Get total number of team members"""
    return count_team_members(team_id)
