"""
Team Service Storage Layer

Database access functions for team-related persistence.
All raw DB operations should go through this module.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

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


# ========================================================================
# DELAYED PROMOTIONS OPERATIONS
# ========================================================================

def check_existing_delayed_promotion(team_id: str, user_id: str) -> Optional[Dict]:
    """Check if user already has a pending delayed promotion"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, team_id, user_id, from_role, to_role, scheduled_at, execute_at, reason
            FROM delayed_promotions
            WHERE team_id = ? AND user_id = ? AND executed = 0
        """, (team_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'team_id': row['team_id'],
                'user_id': row['user_id'],
                'from_role': row['from_role'],
                'to_role': row['to_role'],
                'scheduled_at': row['scheduled_at'],
                'execute_at': row['execute_at'],
                'reason': row['reason']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to check existing delayed promotion: {e}")
        return None


def create_delayed_promotion_record(
    team_id: str,
    user_id: str,
    from_role: str,
    to_role: str,
    execute_at: str,
    scheduled_at: str,
    reason: str
) -> bool:
    """Create a delayed promotion record"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO delayed_promotions
            (team_id, user_id, from_role, to_role, scheduled_at, execute_at, executed, reason)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (team_id, user_id, from_role, to_role, scheduled_at, execute_at, reason))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to create delayed promotion: {e}")
        return False


def get_pending_delayed_promotions(team_id: Optional[str] = None) -> List[Dict]:
    """Get all pending delayed promotions, optionally filtered by team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        
        if team_id:
            cursor.execute("""
                SELECT id, team_id, user_id, from_role, to_role, scheduled_at, execute_at, reason
                FROM delayed_promotions
                WHERE team_id = ? AND executed = 0 AND execute_at <= datetime('now')
                ORDER BY execute_at ASC
            """, (team_id,))
        else:
            cursor.execute("""
                SELECT id, team_id, user_id, from_role, to_role, scheduled_at, execute_at, reason
                FROM delayed_promotions
                WHERE executed = 0 AND execute_at <= datetime('now')
                ORDER BY execute_at ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row['id'],
                'team_id': row['team_id'],
                'user_id': row['user_id'],
                'from_role': row['from_role'],
                'to_role': row['to_role'],
                'scheduled_at': row['scheduled_at'],
                'execute_at': row['execute_at'],
                'reason': row['reason']
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get pending delayed promotions: {e}")
        return []


def mark_delayed_promotion_executed(promotion_id: int, executed_at: str) -> bool:
    """Mark a delayed promotion as executed"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE delayed_promotions
            SET executed = 1, executed_at = ?
            WHERE id = ?
        """, (executed_at, promotion_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to mark delayed promotion executed: {e}")
        return False


# ========================================================================
# TEMPORARY PROMOTIONS OPERATIONS
# ========================================================================

def get_most_senior_admin(team_id: str) -> Optional[Dict]:
    """Get the most senior admin (earliest joined_at) for temporary promotion"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, joined_at
            FROM team_members
            WHERE team_id = ? AND role = 'admin'
            ORDER BY joined_at ASC
            LIMIT 1
        """, (team_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row['user_id'],
                'joined_at': row['joined_at']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get most senior admin: {e}")
        return None


def check_existing_temp_promotion(team_id: str) -> Optional[Dict]:
    """Check if there's already an active temporary promotion"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, promoted_admin_id, promoted_at, reason
            FROM temp_promotions
            WHERE team_id = ? AND status = 'active'
        """, (team_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'promoted_admin_id': row['promoted_admin_id'],
                'promoted_at': row['promoted_at'],
                'reason': row['reason']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to check existing temp promotion: {e}")
        return None


def create_temp_promotion_record(
    team_id: str,
    original_super_admin_id: str,
    promoted_admin_id: str,
    promoted_at: str,
    reason: str
) -> bool:
    """Create a temporary promotion record"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO temp_promotions
            (team_id, original_super_admin_id, promoted_admin_id, promoted_at, status, reason)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (team_id, original_super_admin_id, promoted_admin_id, promoted_at, reason))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to create temp promotion: {e}")
        return False


def get_active_temp_promotions(team_id: str) -> List[Dict]:
    """Get all active temporary promotions for a team"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, team_id, original_super_admin_id, promoted_admin_id,
                   promoted_at, reverted_at, status, reason, approved_by
            FROM temp_promotions
            WHERE team_id = ? AND status = 'active'
            ORDER BY promoted_at DESC
        """, (team_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row['id'],
                'team_id': row['team_id'],
                'original_super_admin_id': row['original_super_admin_id'],
                'promoted_admin_id': row['promoted_admin_id'],
                'promoted_at': row['promoted_at'],
                'reverted_at': row['reverted_at'],
                'status': row['status'],
                'reason': row['reason'],
                'approved_by': row['approved_by']
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get active temp promotions: {e}")
        return []


def get_temp_promotion_details(promotion_id: int) -> Optional[Dict]:
    """Get details of a specific temporary promotion"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, team_id, original_super_admin_id, promoted_admin_id,
                   promoted_at, status
            FROM temp_promotions
            WHERE id = ?
        """, (promotion_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'team_id': row['team_id'],
                'original_super_admin_id': row['original_super_admin_id'],
                'promoted_admin_id': row['promoted_admin_id'],
                'promoted_at': row['promoted_at'],
                'status': row['status']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get temp promotion details: {e}")
        return None


def update_temp_promotion_status(
    promotion_id: int,
    status: str,
    approved_by: Optional[str] = None,
    reverted_at: Optional[str] = None
) -> bool:
    """Update temporary promotion status"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        
        if approved_by:
            cursor.execute("""
                UPDATE temp_promotions
                SET status = ?, approved_by = ?
                WHERE id = ?
            """, (status, approved_by, promotion_id))
        elif reverted_at:
            cursor.execute("""
                UPDATE temp_promotions
                SET status = ?, reverted_at = ?
                WHERE id = ?
            """, (status, reverted_at, promotion_id))
        else:
            cursor.execute("""
                UPDATE temp_promotions
                SET status = ?
                WHERE id = ?
            """, (status, promotion_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to update temp promotion status: {e}")
        return False


# ========================================================================
# FOUNDER RIGHTS / GOD RIGHTS OPERATIONS
# ========================================================================

def get_god_rights_record(user_id: str) -> Optional[Dict]:
    """Get Founder Rights record for a user"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, auth_key_hash, delegated_by, created_at,
                   revoked_at, is_active, notes
            FROM god_rights_auth
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'user_id': row['user_id'],
                'auth_key_hash': row['auth_key_hash'],
                'delegated_by': row['delegated_by'],
                'created_at': row['created_at'],
                'revoked_at': row['revoked_at'],
                'is_active': bool(row['is_active']),
                'notes': row['notes']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get god rights record: {e}")
        return None


def get_active_god_rights_record(user_id: str) -> Optional[Dict]:
    """Get active Founder Rights record for a user"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, auth_key_hash, delegated_by, created_at, notes
            FROM god_rights_auth
            WHERE user_id = ? AND is_active = 1
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'user_id': row['user_id'],
                'auth_key_hash': row['auth_key_hash'],
                'delegated_by': row['delegated_by'],
                'created_at': row['created_at'],
                'notes': row['notes']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get active god rights: {e}")
        return None


def create_god_rights_record(
    user_id: str,
    auth_key_hash: Optional[str],
    delegated_by: Optional[str],
    created_at: str,
    notes: Optional[str]
) -> bool:
    """Create a new Founder Rights record"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO god_rights_auth
            (user_id, auth_key_hash, delegated_by, created_at, is_active, notes)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (user_id, auth_key_hash, delegated_by, created_at, notes))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to create god rights record: {e}")
        return False


def reactivate_god_rights_record(user_id: str, updated_at: str) -> bool:
    """Reactivate revoked Founder Rights"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE god_rights_auth
            SET is_active = 1, revoked_at = NULL
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to reactivate god rights: {e}")
        return False


def revoke_god_rights_record(user_id: str, revoked_at: str, revoked_by: str) -> bool:
    """Revoke Founder Rights for a user"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE god_rights_auth
            SET is_active = 0, revoked_at = ?
            WHERE user_id = ? AND is_active = 1
        """, (revoked_at, user_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Failed to revoke god rights: {e}")
        return False


def get_all_god_rights_users(active_only: bool = True) -> List[Dict]:
    """Get all users with Founder Rights"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("""
                SELECT user_id, auth_key_hash, delegated_by, created_at, notes
                FROM god_rights_auth
                WHERE is_active = 1
                ORDER BY created_at ASC
            """)
        else:
            cursor.execute("""
                SELECT user_id, auth_key_hash, delegated_by, created_at,
                       revoked_at, is_active, notes
                FROM god_rights_auth
                ORDER BY created_at ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if active_only:
            return [
                {
                    'user_id': row['user_id'],
                    'auth_key_hash': row['auth_key_hash'],
                    'delegated_by': row['delegated_by'],
                    'created_at': row['created_at'],
                    'notes': row['notes']
                }
                for row in rows
            ]
        else:
            return [
                {
                    'user_id': row['user_id'],
                    'auth_key_hash': row['auth_key_hash'],
                    'delegated_by': row['delegated_by'],
                    'created_at': row['created_at'],
                    'revoked_at': row['revoked_at'],
                    'is_active': bool(row['is_active']),
                    'notes': row['notes']
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get god rights users: {e}")
        return []


def get_revoked_god_rights_users() -> List[Dict]:
    """Get all users with revoked Founder Rights"""
    try:
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, auth_key_hash, delegated_by, created_at, revoked_at, notes
            FROM god_rights_auth
            WHERE is_active = 0
            ORDER BY revoked_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'user_id': row['user_id'],
                'auth_key_hash': row['auth_key_hash'],
                'delegated_by': row['delegated_by'],
                'created_at': row['created_at'],
                'revoked_at': row['revoked_at'],
                'notes': row['notes']
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get revoked god rights: {e}")
        return []
