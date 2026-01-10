"""
Founder Rights (God Rights) Operations

Manages Founder Rights - elevated privileges for system founders/owners.
These are the highest-level permissions that bypass normal role restrictions.

Founder Rights features:
- Auth key hash storage for additional verification
- Delegation tracking (who granted the rights)
- Revocation with audit trail
- Active/inactive state management

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


__all__ = [
    "get_god_rights_record",
    "get_active_god_rights_record",
    "create_god_rights_record",
    "reactivate_god_rights_record",
    "revoke_god_rights_record",
    "get_all_god_rights_users",
    "get_revoked_god_rights_users",
]
