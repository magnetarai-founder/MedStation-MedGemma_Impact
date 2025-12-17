"""
Team Roles & Promotions Module

Handles role validation, promotion logic, and role-based access control.
All DB operations delegate to storage.py.
"""

import logging
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, UTC

from . import storage

if TYPE_CHECKING:
    from .core import TeamManager

logger = logging.getLogger(__name__)


def get_max_super_admins(team_size: int) -> int:
    """
    Calculate maximum allowed Super Admins based on team size

    Args:
        team_size: Total number of team members

    Returns:
        Maximum number of Super Admins allowed
    """
    if team_size <= 5:
        return 1
    elif team_size <= 15:
        return 2
    elif team_size <= 30:
        return 3
    elif team_size <= 50:
        return 4
    else:
        return 5


def can_promote_to_super_admin(
    manager: 'TeamManager',
    team_id: str,
    requesting_user_role: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if team can have another Super Admin

    Args:
        manager: TeamManager instance
        team_id: Team to check
        requesting_user_role: Role of user making the request (optional)

    Returns:
        Tuple of (can_promote: bool, message: str)
    """
    # Founder Rights (god_rights) bypass role limits
    if requesting_user_role == 'god_rights':
        return True, "Founder Rights: No limits on Super Admin promotions"

    team_size = manager.get_team_size(team_id)
    current_super_admins = manager.count_super_admins(team_id)
    max_allowed = get_max_super_admins(team_size)

    if current_super_admins >= max_allowed:
        return False, f"Team already has maximum Super Admins ({current_super_admins}/{max_allowed} for team size {team_size})"

    return True, f"Can promote: {current_super_admins}/{max_allowed} Super Admins"


def check_auto_promotion_eligibility(
    manager: 'TeamManager',
    team_id: str,
    user_id: str,
    required_days: int = 7
) -> Tuple[bool, str, int]:
    """
    Check if a guest is eligible for auto-promotion to member

    Args:
        manager: TeamManager instance
        team_id: Team ID
        user_id: User ID
        required_days: Days required for auto-promotion (default: 7)

    Returns:
        Tuple of (is_eligible: bool, reason: str, days_elapsed: int)
    """
    try:
        # Get member record to check role
        member = storage.get_member_record(team_id, user_id)
        if not member:
            return False, "User not found in team", 0

        current_role = member['role']

        # Only guests are eligible for auto-promotion
        if current_role != 'guest':
            return False, f"User is already {current_role}, not a guest", 0

        # Calculate days
        days_elapsed = manager.get_days_since_joined(team_id, user_id)
        if days_elapsed is None:
            return False, "Failed to calculate days elapsed", 0

        if days_elapsed >= required_days:
            return True, f"Eligible after {days_elapsed} days (required: {required_days})", days_elapsed
        else:
            return False, f"Not eligible yet: {days_elapsed} days (required: {required_days})", days_elapsed

    except Exception as e:
        logger.error(f"Failed to check auto-promotion eligibility: {e}")
        return False, str(e), 0


def auto_promote_guests(
    manager: 'TeamManager',
    team_id: str,
    required_days: int = 7
) -> List[Dict]:
    """
    Auto-promote all eligible guests in a team to members

    Args:
        manager: TeamManager instance
        team_id: Team ID
        required_days: Days required for auto-promotion (default: 7)

    Returns:
        List of dictionaries with promotion results
    """
    try:
        # Get all guests
        guests = storage.list_members_by_role(team_id, 'guest')
        results = []

        for guest in guests:
            user_id = guest['user_id']
            joined_at = datetime.fromisoformat(guest['joined_at'])
            days_elapsed = (datetime.now() - joined_at).days

            if days_elapsed >= required_days:
                # Auto-promote to member
                success, message = manager.update_member_role(team_id, user_id, 'member')
                results.append({
                    'user_id': user_id,
                    'days_elapsed': days_elapsed,
                    'promoted': success,
                    'message': message if success else f"Failed: {message}"
                })
                logger.info(f"Auto-promoted {user_id} to member after {days_elapsed} days")

        return results

    except Exception as e:
        logger.error(f"Failed to auto-promote guests: {e}")
        return []


def instant_promote_guest(
    manager: 'TeamManager',
    team_id: str,
    user_id: str,
    approved_by_user_id: str,
    auth_type: str = 'real_password'
) -> Tuple[bool, str]:
    """
    Instantly promote a guest to member (Phase 4.2)

    Bypasses 7-day wait when Super Admin approves with real password + biometric

    Args:
        manager: TeamManager instance
        team_id: Team ID
        user_id: Guest user to promote
        approved_by_user_id: Super Admin who approved
        auth_type: 'real_password' or 'decoy_password' (for audit)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Verify guest exists
        member = storage.get_member_record(team_id, user_id)
        if not member:
            return False, f"User {user_id} not found in team"

        if member['role'] != 'guest':
            return False, f"User is already {member['role']}, not a guest"

        # Promote immediately
        success, message = manager.update_member_role(team_id, user_id, 'member')

        if success:
            logger.info(f"Instant-promoted {user_id} to member (approved by {approved_by_user_id}, auth: {auth_type})")
            return True, "Instantly promoted to member. Access granted from now forward."

        return False, message

    except Exception as e:
        logger.error(f"Failed instant promotion: {e}")
        return False, str(e)


def schedule_delayed_promotion(
    team_id: str,
    user_id: str,
    delay_days: int = 21,
    approved_by_user_id: Optional[str] = None,
    reason: str = "Decoy password delay"
) -> Tuple[bool, str]:
    """
    Schedule a delayed promotion (Phase 4.3)

    Used when Super Admin approves with decoy password + biometric

    Args:
        team_id: Team ID
        user_id: Guest user to promote
        delay_days: Days to delay promotion (default: 21)
        approved_by_user_id: Super Admin who approved
        reason: Reason for delay

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Verify guest exists
        member = storage.get_member_record(team_id, user_id)
        if not member:
            return False, f"User {user_id} not found in team"

        if member['role'] != 'guest':
            return False, f"User is already {member['role']}, not a guest"

        # Check for existing delayed promotion
        existing = storage.check_existing_delayed_promotion(team_id, user_id)
        if existing:
            return False, f"User already has a scheduled promotion (execute at: {existing['execute_at']})"

        # Schedule promotion
        now = datetime.now(UTC)
        execute_at = now + timedelta(days=delay_days)

        success = storage.create_delayed_promotion_record(
            team_id=team_id,
            user_id=user_id,
            from_role='guest',
            to_role='member',
            execute_at=execute_at.isoformat(),
            scheduled_at=now.isoformat(),
            reason=reason
        )

        if success:
            logger.info(f"Scheduled delayed promotion for {user_id} (execute at: {execute_at.isoformat()})")
            return True, f"Promotion scheduled for {execute_at.strftime('%Y-%m-%d %H:%M:%S')} ({delay_days} days)"

        return False, "Failed to schedule delayed promotion"

    except Exception as e:
        logger.error(f"Failed to schedule delayed promotion: {e}")
        return False, str(e)


def execute_delayed_promotions(
    manager: 'TeamManager',
    team_id: Optional[str] = None
) -> List[Dict]:
    """
    Execute all pending delayed promotions (cron job)

    Args:
        manager: TeamManager instance
        team_id: Optional team ID to filter by

    Returns:
        List of promotion execution results
    """
    try:
        # Get pending promotions
        promotions = storage.get_pending_delayed_promotions(team_id)
        results = []
        now = datetime.now(UTC).isoformat()

        for promo in promotions:
            # Execute promotion
            success, message = manager.update_member_role(
                promo['team_id'],
                promo['user_id'],
                promo['to_role']
            )

            if success:
                # Mark as executed
                storage.mark_delayed_promotion_executed(promo['id'], now)
                results.append({
                    'promotion_id': promo['id'],
                    'team_id': promo['team_id'],
                    'user_id': promo['user_id'],
                    'from_role': promo['from_role'],
                    'to_role': promo['to_role'],
                    'success': True,
                    'message': f"Promoted from {promo['from_role']} to {promo['to_role']}"
                })
                logger.info(f"Executed delayed promotion {promo['id']}: {promo['user_id']} → {promo['to_role']}")
            else:
                results.append({
                    'promotion_id': promo['id'],
                    'team_id': promo['team_id'],
                    'user_id': promo['user_id'],
                    'from_role': promo['from_role'],
                    'to_role': promo['to_role'],
                    'success': False,
                    'message': f"Failed: {message}"
                })
                logger.error(f"Failed to execute delayed promotion {promo['id']}: {message}")

        return results

    except Exception as e:
        logger.error(f"Failed to execute delayed promotions: {e}")
        return []


def promote_admin_temporarily(
    manager: 'TeamManager',
    team_id: str,
    offline_super_admin_id: str,
    requesting_user_role: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Temporarily promote most senior admin to super_admin (offline failsafe)

    Args:
        manager: TeamManager instance
        team_id: Team ID
        offline_super_admin_id: ID of offline Super Admin
        requesting_user_role: Role of requester

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Find most senior admin
        senior_admin = storage.get_most_senior_admin(team_id)
        if not senior_admin:
            return False, "No admins available for temporary promotion"

        promoted_admin_id = senior_admin['user_id']

        # Check for existing temp promotion
        existing = storage.check_existing_temp_promotion(team_id)
        if existing:
            return False, f"Already have active temp promotion: {existing['promoted_admin_id']}"

        # Promote admin to super_admin
        success, message = manager.update_member_role(
            team_id,
            promoted_admin_id,
            'super_admin',
            requesting_user_role
        )

        if not success:
            return False, f"Failed to promote admin: {message}"

        # Record temp promotion
        now = datetime.now(UTC).isoformat()
        storage.create_temp_promotion_record(
            team_id=team_id,
            original_super_admin_id=offline_super_admin_id,
            promoted_admin_id=promoted_admin_id,
            promoted_at=now,
            reason=f"Offline Super Admin failsafe: {offline_super_admin_id} offline"
        )

        logger.info(f"Temporarily promoted {promoted_admin_id} to super_admin (offline: {offline_super_admin_id})")
        return True, f"Temporarily promoted {promoted_admin_id} to Super Admin"

    except Exception as e:
        logger.error(f"Failed temporary promotion: {e}")
        return False, str(e)


def get_pending_temp_promotions(team_id: str) -> List[Dict]:
    """
    Get all pending temporary promotions for a team

    Args:
        team_id: Team ID

    Returns:
        List of pending temporary promotions
    """
    return storage.get_active_temp_promotions(team_id)


def approve_temp_promotion(
    temp_promotion_id: int,
    approved_by: str
) -> Tuple[bool, str]:
    """
    Approve a temporary promotion (make it permanent)

    Args:
        temp_promotion_id: Temp promotion ID
        approved_by: User ID who approved

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get promotion details
        promo = storage.get_temp_promotion_details(temp_promotion_id)
        if not promo:
            return False, f"Temp promotion {temp_promotion_id} not found"

        if promo['status'] != 'active':
            return False, f"Temp promotion status is '{promo['status']}', expected 'active'"

        # Mark as approved
        now = datetime.now(UTC).isoformat()
        success = storage.update_temp_promotion_status(
            temp_promotion_id,
            'approved',
            approved_by=approved_by
        )

        if success:
            logger.info(f"Approved temp promotion {temp_promotion_id} (by {approved_by})")
            return True, f"Temporary promotion approved. Admin {promo['promoted_admin_id']} is now permanently Super Admin."

        return False, "Failed to approve temp promotion"

    except Exception as e:
        logger.error(f"Failed to approve temp promotion: {e}")
        return False, str(e)


def revert_temp_promotion(
    manager: 'TeamManager',
    temp_promotion_id: int,
    reverted_by: str
) -> Tuple[bool, str]:
    """
    Revert a temporary promotion (demote back to admin)

    Args:
        manager: TeamManager instance
        temp_promotion_id: Temp promotion ID
        reverted_by: User ID who reverted

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get promotion details
        promo = storage.get_temp_promotion_details(temp_promotion_id)
        if not promo:
            return False, f"Temp promotion {temp_promotion_id} not found"

        if promo['status'] != 'active':
            return False, f"Temp promotion status is '{promo['status']}', expected 'active'"

        # Demote back to admin
        success, message = manager.update_member_role(
            promo['team_id'],
            promo['promoted_admin_id'],
            'admin'
        )

        if not success:
            return False, f"Failed to demote: {message}"

        # Mark as reverted
        now = datetime.now(UTC).isoformat()
        storage.update_temp_promotion_status(
            temp_promotion_id,
            'reverted',
            reverted_at=now
        )

        logger.info(f"Reverted temp promotion {temp_promotion_id} (by {reverted_by})")
        return True, f"Reverted: {promo['promoted_admin_id']} demoted back to Admin"

    except Exception as e:
        logger.error(f"Failed to revert temp promotion: {e}")
        return False, str(e)
