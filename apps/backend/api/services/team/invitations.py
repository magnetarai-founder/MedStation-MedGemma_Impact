"""
Team Service Invitations Module

Invite code lifecycle management including:
- Code generation
- Code validation
- Brute-force protection
- Code regeneration
"""

import secrets
import string
import logging
from datetime import datetime, timedelta
from typing import Optional

from .storage import (
    create_invite_code_record,
    invite_code_exists,
    get_active_invite_code_record,
    get_invite_code_details,
    mark_invite_codes_used,
    record_invite_attempt_db,
    count_failed_invite_attempts,
)
from .types import MAX_INVITE_ATTEMPTS

logger = logging.getLogger(__name__)


# ========================================================================
# INVITE CODE GENERATION
# ========================================================================

def generate_invite_code(team_id: str, expires_days: Optional[int] = None) -> str:
    """
    Generate a shareable invite code
    Format: XXXXX-XXXXX-XXXXX (e.g., A7B3C-D9E2F-G1H4I)

    Args:
        team_id: Team ID to generate code for
        expires_days: Optional expiration in days

    Returns:
        Generated invite code string
    """
    # Generate 3 groups of 5 characters
    parts = []
    for _ in range(3):
        part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        parts.append(part)

    code = '-'.join(parts)

    # Calculate expiration
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)

    # Try to create the code, retry if collision
    success = create_invite_code_record(code, team_id, expires_at)
    if not success:
        # Code collision, try again
        return generate_invite_code(team_id, expires_days)

    return code


def get_active_invite_code(team_id: str) -> Optional[str]:
    """Get active (non-expired, unused) invite code for team"""
    return get_active_invite_code_record(team_id)


def regenerate_invite_code(team_id: str, expires_days: int = 30) -> str:
    """
    Generate a new invite code for team (invalidates old ones)

    Args:
        team_id: Team ID
        expires_days: Days until expiration (default: 30)

    Returns:
        New invite code
    """
    try:
        # Mark existing codes as used
        mark_invite_codes_used(team_id)

        # Generate new code
        return generate_invite_code(team_id, expires_days)

    except Exception as e:
        logger.error(f"Failed to regenerate invite code: {e}")
        raise


# ========================================================================
# INVITE CODE VALIDATION
# ========================================================================

def record_invite_attempt(invite_code: str, ip_address: str, success: bool):
    """Record an invite code validation attempt (HIGH-05)"""
    record_invite_attempt_db(invite_code, ip_address, success)


def check_brute_force_lockout(invite_code: str, ip_address: str) -> bool:
    """
    Check if invite code is locked due to too many failed attempts (HIGH-05)

    Args:
        invite_code: The invite code being checked
        ip_address: IP address of requester

    Returns:
        True if locked (too many failures), False if attempts are allowed
    """
    try:
        # Count failed attempts in last hour for this code+IP combination
        failed_count = count_failed_invite_attempts(invite_code, ip_address, window_hours=1)

        if failed_count >= 10:  # MAX_INVITE_ATTEMPTS threshold
            logger.warning(f"Invite code locked: {invite_code} from {ip_address} ({failed_count} failed attempts)")
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to check brute force lockout: {e}")
        return False  # Fail open to avoid blocking legitimate users


def validate_invite_code(invite_code: str, ip_address: Optional[str] = None) -> Optional[str]:
    """
    Validate invite code and return team_id if valid

    Args:
        invite_code: The invite code to validate
        ip_address: IP address of requester (for brute-force protection)

    Returns:
        team_id if code is valid and not expired/used, None otherwise
    """
    # Check for brute-force lockout (HIGH-05)
    if ip_address and check_brute_force_lockout(invite_code, ip_address):
        if ip_address:
            record_invite_attempt(invite_code, ip_address, False)
        return None

    try:
        details = get_invite_code_details(invite_code)

        if not details:
            logger.warning(f"Invite code not found: {invite_code}")
            if ip_address:
                record_invite_attempt(invite_code, ip_address, False)
            return None

        # Check if already used
        if details['used']:
            logger.warning(f"Invite code already used: {invite_code}")
            if ip_address:
                record_invite_attempt(invite_code, ip_address, False)
            return None

        # Check if expired
        if details['expires_at']:
            expires_at = datetime.fromisoformat(details['expires_at'])
            if datetime.now() > expires_at:
                logger.warning(f"Invite code expired: {invite_code}")
                if ip_address:
                    record_invite_attempt(invite_code, ip_address, False)
                return None

        # Success - record attempt
        if ip_address:
            record_invite_attempt(invite_code, ip_address, True)

        return details['team_id']

    except Exception as e:
        logger.error(f"Failed to validate invite code: {e}")
        return None
