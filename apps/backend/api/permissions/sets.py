"""
Permission Set Management

Handles permission sets - named bundles of permissions that can be assigned to users.
Unlike profiles (role-based), sets are feature bundles (e.g., "Reports Module")
and support expiration dates for temporary access.

Extracted from admin.py during P2 decomposition.
"""

import sqlite3
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime, UTC

from .storage import get_db_connection

logger = logging.getLogger(__name__)


# ===== Permission Set Functions =====

async def get_all_permission_sets() -> List[Dict]:
    """
    Get all permission sets.

    Returns:
        List of permission set dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM permission_sets
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    sets = []
    for row in rows:
        sets.append({
            "permission_set_id": row['permission_set_id'],
            "set_name": row['set_name'],
            "set_description": row['set_description'],
            "team_id": row['team_id'],
            "created_by": row['created_by'],
            "created_at": row['created_at'],
            "is_active": bool(row['is_active'])
        })

    return sets


async def create_permission_set(
    set_name: str,
    set_description: Optional[str],
    team_id: Optional[str],
    created_by: str
) -> Dict:
    """
    Create a new permission set.

    Args:
        set_name: Name of the permission set
        set_description: Optional description
        team_id: Optional team ID this set belongs to
        created_by: User ID creating the set

    Returns:
        Created permission set dictionary
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Generate set ID
    set_id = f"permset_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    cur.execute("""
        INSERT INTO permission_sets (
            permission_set_id, set_name, set_description, team_id,
            created_by, created_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        set_id,
        set_name,
        set_description,
        team_id,
        created_by,
        now,
        1
    ))

    conn.commit()
    conn.close()

    return {
        "permission_set_id": set_id,
        "set_name": set_name,
        "set_description": set_description,
        "team_id": team_id,
        "created_by": created_by,
        "created_at": now,
        "is_active": True
    }


async def assign_permission_set_to_user(
    set_id: str,
    user_id: str,
    expires_at: Optional[str],
    assigning_user_id: str
) -> Dict:
    """
    Assign a permission set to a user.

    Args:
        set_id: ID of the permission set to assign
        user_id: ID of the user to assign to
        expires_at: Optional expiration timestamp
        assigning_user_id: ID of the user making the assignment

    Returns:
        Success status with user_id and permission_set_id

    Raises:
        HTTPException: If permission set or user not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if set exists
    cur.execute("SELECT * FROM permission_sets WHERE permission_set_id = ?", (set_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Permission set not found")

    # Check if user exists
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(UTC).isoformat()

    cur.execute("""
        INSERT INTO user_permission_sets (
            user_id, permission_set_id, assigned_by, assigned_at, expires_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, permission_set_id) DO UPDATE SET
            assigned_by = excluded.assigned_by,
            assigned_at = excluded.assigned_at,
            expires_at = excluded.expires_at
    """, (user_id, set_id, assigning_user_id, now, expires_at))

    conn.commit()
    conn.close()

    # Audit log - Permission set granted to user
    audit_log_sync(
        user_id=assigning_user_id,
        action=AuditAction.PERMISSION_SET_GRANTED,
        resource="permission_set",
        resource_id=set_id,
        details={
            "target_user_id": user_id,
            "permission_set_id": set_id,
            "expires_at": expires_at
        }
    )

    # Invalidate user's permission cache
    engine = get_permission_engine()
    engine.invalidate_user_permissions(user_id)

    return {"status": "success", "user_id": user_id, "permission_set_id": set_id}


async def unassign_permission_set_from_user(
    set_id: str,
    user_id: str,
    unassigning_user_id: str
) -> Dict:
    """
    Unassign a permission set from a user.

    Args:
        set_id: ID of the permission set to unassign
        user_id: ID of the user to unassign from
        unassigning_user_id: ID of the user making the unassignment

    Returns:
        Success status with user_id and permission_set_id

    Raises:
        HTTPException: If assignment not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM user_permission_sets
        WHERE user_id = ? AND permission_set_id = ?
    """, (user_id, set_id))

    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Audit log - Permission set revoked from user
    audit_log_sync(
        user_id=unassigning_user_id,
        action=AuditAction.PERMISSION_SET_REVOKED,
        resource="permission_set",
        resource_id=set_id,
        details={
            "target_user_id": user_id,
            "permission_set_id": set_id
        }
    )

    # Invalidate user's permission cache
    engine = get_permission_engine()
    engine.invalidate_user_permissions(user_id)

    return {"status": "success", "user_id": user_id, "permission_set_id": set_id}


async def update_permission_set_grants(
    set_id: str,
    grants: List[Dict],
    modified_by: str
) -> Dict:
    """
    Upsert permission grants for a permission set.

    Args:
        set_id: ID of the permission set
        grants: List of grant dictionaries with permission_id, is_granted, permission_level, permission_scope
        modified_by: User ID making the changes

    Returns:
        Success status with count of grants updated

    Raises:
        HTTPException: If permission set not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Verify permission set exists
    cur.execute("SELECT permission_set_id FROM permission_sets WHERE permission_set_id = ?", (set_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Permission set not found")

    # Upsert grants
    now = datetime.now(UTC).isoformat()
    for grant in grants:
        cur.execute("""
            INSERT INTO permission_set_permissions (
                permission_set_id, permission_id, is_granted, permission_level, permission_scope, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(permission_set_id, permission_id) DO UPDATE SET
                is_granted = excluded.is_granted,
                permission_level = excluded.permission_level,
                permission_scope = excluded.permission_scope
        """, (
            set_id,
            grant["permission_id"],
            grant.get("is_granted", True),
            grant.get("permission_level"),
            grant.get("permission_scope"),
            now
        ))

    conn.commit()

    # Invalidate cache for all users with this set (before closing connection)
    engine = get_permission_engine()
    cur.execute("SELECT user_id FROM user_permission_sets WHERE permission_set_id = ?", (set_id,))
    affected_users = [row[0] for row in cur.fetchall()]

    conn.close()

    # Invalidate cache for affected users
    for user_id in affected_users:
        engine.invalidate_user_permissions(user_id)

    # Audit log - Permission set modified
    audit_log_sync(
        user_id=modified_by,
        action=AuditAction.PERMISSION_MODIFIED,
        resource="permission_set",
        resource_id=set_id,
        details={
            "grants_updated": len(grants),
            "permissions": [grant["permission_id"] for grant in grants],
            "affected_users": len(affected_users)
        }
    )

    return {"status": "success", "permission_set_id": set_id, "grants_updated": len(grants)}


async def get_permission_set_grants(set_id: str) -> Dict:
    """
    Get all permission grants for a permission set.

    Args:
        set_id: ID of the permission set

    Returns:
        Dictionary with permission_set_id and list of grants

    Raises:
        HTTPException: If permission set not found
    """
    from fastapi import HTTPException  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Verify permission set exists
    cur.execute("SELECT permission_set_id FROM permission_sets WHERE permission_set_id = ?", (set_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Permission set not found")

    # Get grants
    cur.execute("""
        SELECT psp.permission_id, psp.is_granted, psp.permission_level, psp.permission_scope,
               p.permission_key, p.permission_name, p.permission_type
        FROM permission_set_permissions psp
        JOIN permissions p ON psp.permission_id = p.permission_id
        WHERE psp.permission_set_id = ?
        ORDER BY p.category, p.permission_key
    """, (set_id,))

    grants = []
    for row in cur.fetchall():
        grants.append({
            "permission_id": row[0],
            "is_granted": bool(row[1]),
            "permission_level": row[2],
            "permission_scope": row[3],
            "permission_key": row[4],
            "permission_name": row[5],
            "permission_type": row[6]
        })

    conn.close()
    return {"permission_set_id": set_id, "grants": grants}


async def delete_permission_set_grant(
    set_id: str,
    permission_id: str,
    deleting_user_id: str
) -> Dict:
    """
    Delete a specific permission grant from a permission set.

    Args:
        set_id: ID of the permission set
        permission_id: ID of the permission to remove
        deleting_user_id: ID of the user making the deletion

    Returns:
        Success status with permission_set_id and permission_id

    Raises:
        HTTPException: If grant not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM permission_set_permissions
        WHERE permission_set_id = ? AND permission_id = ?
    """, (set_id, permission_id))

    conn.commit()
    deleted = cur.rowcount

    if deleted == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Grant not found")

    # Invalidate cache for users with this set (before closing connection)
    engine = get_permission_engine()
    cur.execute("SELECT user_id FROM user_permission_sets WHERE permission_set_id = ?", (set_id,))
    affected_users = [row[0] for row in cur.fetchall()]

    conn.close()

    # Invalidate cache for affected users
    for user_id in affected_users:
        engine.invalidate_user_permissions(user_id)

    # Audit log - Permission revoked from set
    audit_log_sync(
        user_id=deleting_user_id,
        action=AuditAction.PERMISSION_REVOKED,
        resource="permission_set",
        resource_id=set_id,
        details={
            "permission_id": permission_id,
            "affected_users": len(affected_users)
        }
    )

    return {"status": "success", "permission_set_id": set_id, "permission_id": permission_id}


__all__ = [
    "get_all_permission_sets",
    "create_permission_set",
    "assign_permission_set_to_user",
    "unassign_permission_set_from_user",
    "update_permission_set_grants",
    "get_permission_set_grants",
    "delete_permission_set_grant",
]
