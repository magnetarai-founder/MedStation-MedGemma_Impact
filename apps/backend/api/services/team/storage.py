"""
Team Service Storage Layer

Database access functions for team-related persistence.
All raw DB operations should go through this module.

Extracted modules (P2 decomposition):
- promotions.py: Delayed and temporary promotion operations
- god_rights.py: Founder Rights management
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

# Re-export from extracted modules for backward compatibility
from .promotions import (
    check_existing_delayed_promotion,
    create_delayed_promotion_record,
    get_pending_delayed_promotions,
    mark_delayed_promotion_executed,
    get_most_senior_admin,
    check_existing_temp_promotion,
    create_temp_promotion_record,
    get_active_temp_promotions,
    get_temp_promotion_details,
    update_temp_promotion_status,
)
from .god_rights import (
    get_god_rights_record,
    get_active_god_rights_record,
    create_god_rights_record,
    reactivate_god_rights_record,
    revoke_god_rights_record,
    get_all_god_rights_users,
    get_revoked_god_rights_users,
)

logger = logging.getLogger(__name__)


def _get_app_conn() -> sqlite3.Connection:
    """Get connection to app_db with row factory"""
    from api.config_paths import get_config_paths
    PATHS = get_config_paths()
    APP_DB = PATHS.app_db
    conn = sqlite3.connect(str(APP_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ========================================================================
# TEAM CRUD OPERATIONS
# ========================================================================

def create_team_record(team_id: str, name: str, creator_user_id: str, description: Optional[str] = None) -> bool:
    """Create a team record in the database"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO teams (team_id, name, description, created_by)
            VALUES (?, ?, ?, ?)
        """, (team_id, name, description, creator_user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to create team record: {e}")
        return False


def get_team_by_id(team_id: str) -> Optional[Dict]:
    """Get team details by ID"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_id, name, description, created_at, created_by
            FROM teams
            WHERE team_id = ?
        """, (team_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'team_id': row['team_id'],
            'name': row['name'],
            'description': row['description'],
            'created_at': row['created_at'],
            'created_by': row['created_by']
        }
    except Exception as e:
        logger.error(f"Failed to get team: {e}")
        return None


def team_id_exists(team_id: str) -> bool:
    """Check if a team ID already exists"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT team_id FROM teams WHERE team_id = ?", (team_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        logger.error(f"Failed to check team ID existence: {e}")
        return False


# ========================================================================
# TEAM MEMBER OPERATIONS
# ========================================================================

def add_member_record(team_id: str, user_id: str, role: str) -> bool:
    """Add a member to a team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role)
            VALUES (?, ?, ?)
        """, (team_id, user_id, role))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to add member record: {e}")
        return False


def is_team_member(team_id: str, user_id: str) -> bool:
    """Check if user is a member of the team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        logger.error(f"Failed to check team membership: {e}")
        return False


def get_team_members_list(team_id: str) -> List[Dict]:
    """Get all members of a team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, role, joined_at
            FROM team_members
            WHERE team_id = ?
            ORDER BY joined_at ASC
        """, (team_id,))

        members = []
        for row in cursor.fetchall():
            members.append({
                'user_id': row['user_id'],
                'role': row['role'],
                'joined_at': row['joined_at']
            })

        conn.close()
        return members
    except Exception as e:
        logger.error(f"Failed to get team members: {e}")
        return []


def get_user_teams_list(user_id: str) -> List[Dict]:
    """Get all teams a user is a member of"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.team_id, t.name, t.description, t.created_at, tm.role
            FROM teams t
            JOIN team_members tm ON t.team_id = tm.team_id
            WHERE tm.user_id = ?
            ORDER BY tm.joined_at DESC
        """, (user_id,))

        teams = []
        for row in cursor.fetchall():
            teams.append({
                'team_id': row['team_id'],
                'name': row['name'],
                'description': row['description'],
                'created_at': row['created_at'],
                'user_role': row['role']
            })

        conn.close()
        return teams
    except Exception as e:
        logger.error(f"Failed to get user teams: {e}")
        return []


def get_member_role(team_id: str, user_id: str) -> Optional[str]:
    """Get a member's role in a team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        row = cursor.fetchone()
        conn.close()
        return row['role'] if row else None
    except Exception as e:
        logger.error(f"Failed to get member role: {e}")
        return None


def update_member_role_db(team_id: str, user_id: str, new_role: str) -> bool:
    """Update a team member's role"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE team_members
            SET role = ?
            WHERE team_id = ? AND user_id = ?
        """, (new_role, team_id, user_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        return False


def update_last_seen_db(team_id: str, user_id: str, timestamp: datetime) -> bool:
    """Update last_seen timestamp for a team member"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE team_members
            SET last_seen = ?
            WHERE team_id = ? AND user_id = ?
        """, (timestamp, team_id, user_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to update last_seen: {e}")
        return False


def get_member_joined_at(team_id: str, user_id: str) -> Optional[str]:
    """Get when a member joined the team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT joined_at FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        row = cursor.fetchone()
        conn.close()
        return row['joined_at'] if row else None
    except Exception as e:
        logger.error(f"Failed to get member joined_at: {e}")
        return None


def update_job_role_db(team_id: str, user_id: str, job_role: str) -> bool:
    """Update a team member's job role"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE team_members
            SET job_role = ?
            WHERE team_id = ? AND user_id = ?
        """, (job_role, team_id, user_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to update job role: {e}")
        return False


def get_member_job_role_db(team_id: str, user_id: str) -> Optional[str]:
    """Get a team member's job role"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_role FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        row = cursor.fetchone()
        conn.close()
        return row['job_role'] if row else None
    except Exception as e:
        logger.error(f"Failed to get job role: {e}")
        return None


def count_members_by_role(team_id: str, role: str) -> int:
    """Count number of members with a specific role"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM team_members
            WHERE team_id = ? AND role = ?
        """, (team_id, role))

        row = cursor.fetchone()
        conn.close()
        return row['count'] if row else 0
    except Exception as e:
        logger.error(f"Failed to count members by role: {e}")
        return 0


def count_team_members(team_id: str) -> int:
    """Count total number of team members"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM team_members
            WHERE team_id = ?
        """, (team_id,))

        row = cursor.fetchone()
        conn.close()
        return row['count'] if row else 0
    except Exception as e:
        logger.error(f"Failed to count team members: {e}")
        return 0


# ========================================================================
# INVITE CODE OPERATIONS
# ========================================================================

def create_invite_code_record(code: str, team_id: str, expires_at: Optional[datetime] = None) -> bool:
    """Create an invite code record"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invite_codes (code, team_id, expires_at)
            VALUES (?, ?, ?)
        """, (code, team_id, expires_at))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Code collision
        return False
    except Exception as e:
        logger.error(f"Failed to create invite code: {e}")
        return False


def invite_code_exists(code: str) -> bool:
    """Check if an invite code already exists"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM invite_codes WHERE code = ?", (code,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        logger.error(f"Failed to check invite code existence: {e}")
        return False


def get_active_invite_code_record(team_id: str) -> Optional[str]:
    """Get active (non-expired, unused) invite code for team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT code, expires_at
            FROM invite_codes
            WHERE team_id = ?
              AND used = FALSE
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY created_at DESC
            LIMIT 1
        """, (team_id,))

        row = cursor.fetchone()
        conn.close()
        return row['code'] if row else None
    except Exception as e:
        logger.error(f"Failed to get active invite code: {e}")
        return None


def get_invite_code_details(code: str) -> Optional[Dict]:
    """Get invite code details including team_id, expires_at, used status"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_id, expires_at, used
            FROM invite_codes
            WHERE code = ?
        """, (code,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'team_id': row['team_id'],
            'expires_at': row['expires_at'],
            'used': row['used']
        }
    except Exception as e:
        logger.error(f"Failed to get invite code details: {e}")
        return None


def mark_invite_codes_used(team_id: str) -> bool:
    """Mark all invite codes for a team as used"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE invite_codes
            SET used = TRUE
            WHERE team_id = ? AND used = FALSE
        """, (team_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to mark invite codes as used: {e}")
        return False


def record_invite_attempt_db(invite_code: str, ip_address: str, success: bool) -> bool:
    """Record an invite code validation attempt"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invite_attempts (invite_code, ip_address, success)
            VALUES (?, ?, ?)
        """, (invite_code, ip_address, success))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to record invite attempt: {e}")
        return False


def count_failed_invite_attempts(invite_code: str, ip_address: str, window_hours: int = 1) -> int:
    """Count failed attempts for an invite code + IP combo within time window"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as failed_count
            FROM invite_attempts
            WHERE invite_code = ?
            AND ip_address = ?
            AND success = FALSE
            AND attempt_timestamp > datetime('now', ?)
        """, (invite_code, ip_address, f'-{window_hours} hour'))

        row = cursor.fetchone()
        conn.close()
        return row['failed_count'] if row else 0
    except Exception as e:
        logger.error(f"Failed to count failed attempts: {e}")
        return 0


