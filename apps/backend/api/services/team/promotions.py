"""
Team Promotions Operations

Handles delayed (scheduled) and temporary promotions within teams.

Delayed Promotions: Schedule role changes for future dates (e.g., promote after probation period)
Temporary Promotions: Acting super-admin when primary is absent (e.g., vacation coverage)

Extracted from storage.py during P2 decomposition.
"""

import sqlite3
import logging
from typing import Optional, List, Dict

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


__all__ = [
    # Delayed promotions
    "check_existing_delayed_promotion",
    "create_delayed_promotion_record",
    "get_pending_delayed_promotions",
    "mark_delayed_promotion_executed",
    # Temporary promotions
    "get_most_senior_admin",
    "check_existing_temp_promotion",
    "create_temp_promotion_record",
    "get_active_temp_promotions",
    "get_temp_promotion_details",
    "update_temp_promotion_status",
]
