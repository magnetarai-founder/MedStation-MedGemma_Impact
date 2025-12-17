"""
Team Founder Rights (God Rights) Module

Handles Founder Rights / God Rights authorization and management.
Phase 6.1 implementation - highest privilege tier in the system.

All DB operations delegate to storage.py.
"""

import logging
import hashlib
from typing import List, Tuple, Optional, Dict, TYPE_CHECKING
from datetime import datetime, UTC

from . import storage

if TYPE_CHECKING:
    from .core import TeamManager

logger = logging.getLogger(__name__)


def grant_god_rights(
    manager: 'TeamManager',
    user_id: str,
    delegated_by: Optional[str] = None,
    auth_key: Optional[str] = None,
    notes: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Grant Founder Rights to a user (Phase 6.1)

    Args:
        manager: TeamManager instance (for delegator verification)
        user_id: User to grant rights to
        delegated_by: User ID delegating the rights (must have god_rights themselves)
        auth_key: Optional auth key for verification
        notes: Optional notes

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # If delegated, verify delegator has god rights
        if delegated_by:
            has_rights, _ = check_god_rights(delegated_by)
            if not has_rights:
                return False, f"Delegator {delegated_by} does not have Founder Rights"

        # Check if user already has rights
        existing = storage.get_god_rights_record(user_id)

        # Hash auth key if provided
        auth_key_hash = None
        if auth_key:
            auth_key_hash = hashlib.sha256(auth_key.encode()).hexdigest()

        now = datetime.now(UTC).isoformat()

        if existing:
            # Reactivate if previously revoked
            if not existing['is_active']:
                success = storage.reactivate_god_rights_record(user_id, now)
                if success:
                    logger.info(f"Reactivated Founder Rights for {user_id} (delegated by: {delegated_by})")
                    return True, f"Founder Rights reactivated for {user_id}"
                return False, "Failed to reactivate Founder Rights"
            else:
                return False, f"User {user_id} already has active Founder Rights"

        # Create new god rights record
        success = storage.create_god_rights_record(
            user_id=user_id,
            auth_key_hash=auth_key_hash,
            delegated_by=delegated_by,
            created_at=now,
            notes=notes
        )

        if success:
            logger.info(f"Granted Founder Rights to {user_id} (delegated by: {delegated_by})")
            return True, f"Founder Rights granted to {user_id}"

        return False, "Failed to grant Founder Rights"

    except Exception as e:
        logger.error(f"Failed to grant Founder Rights: {e}")
        return False, str(e)


def revoke_god_rights(
    manager: 'TeamManager',
    user_id: str,
    revoked_by: str
) -> Tuple[bool, str]:
    """
    Revoke Founder Rights from a user (Phase 6.1)

    Args:
        manager: TeamManager instance (for revoker verification)
        user_id: User to revoke rights from
        revoked_by: User ID revoking the rights (must have god_rights themselves)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Verify revoker has god rights
        has_rights, _ = check_god_rights(revoked_by)
        if not has_rights:
            return False, f"User {revoked_by} does not have Founder Rights to revoke"

        # Check if target user has active rights
        existing = storage.get_active_god_rights_record(user_id)
        if not existing:
            return False, f"User {user_id} does not have active Founder Rights"

        # Revoke rights
        now = datetime.now(UTC).isoformat()
        success = storage.revoke_god_rights_record(user_id, now, revoked_by)

        if success:
            logger.info(f"Revoked Founder Rights from {user_id} (by {revoked_by})")
            return True, f"Founder Rights revoked from {user_id}"

        return False, "Failed to revoke Founder Rights"

    except Exception as e:
        logger.error(f"Failed to revoke Founder Rights: {e}")
        return False, str(e)


def check_god_rights(user_id: str) -> Tuple[bool, str]:
    """
    Check if a user has active Founder Rights (Phase 6.1)

    Args:
        user_id: User ID to check

    Returns:
        Tuple of (has_rights: bool, message: str)
    """
    try:
        record = storage.get_active_god_rights_record(user_id)

        if record:
            return True, f"User {user_id} has active Founder Rights (granted: {record['created_at']})"

        return False, f"User {user_id} does not have active Founder Rights"

    except Exception as e:
        logger.error(f"Failed to check Founder Rights: {e}")
        return False, str(e)


def get_god_rights_users() -> List[Dict]:
    """
    Get all users with active Founder Rights (Phase 6.1)

    Returns:
        List of users with Founder Rights
    """
    try:
        users = storage.get_all_god_rights_users(active_only=True)

        return [
            {
                'user_id': user['user_id'],
                'delegated_by': user['delegated_by'],
                'granted_at': user['created_at'],
                'notes': user['notes']
            }
            for user in users
        ]

    except Exception as e:
        logger.error(f"Failed to get Founder Rights users: {e}")
        return []


def get_revoked_god_rights() -> List[Dict]:
    """
    Get all users with revoked Founder Rights (audit trail)

    Returns:
        List of users with revoked Founder Rights
    """
    try:
        users = storage.get_revoked_god_rights_users()

        return [
            {
                'user_id': user['user_id'],
                'delegated_by': user['delegated_by'],
                'granted_at': user['created_at'],
                'revoked_at': user['revoked_at'],
                'notes': user['notes']
            }
            for user in users
        ]

    except Exception as e:
        logger.error(f"Failed to get revoked Founder Rights: {e}")
        return []
