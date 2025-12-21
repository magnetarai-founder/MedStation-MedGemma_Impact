"""
Permission Administration

High-level admin and service functions for permission management.
Handles permission registry, profiles, permission sets, and user assignments.

Extracted from services/permissions.py during Phase 3 modularization.
"""

import sqlite3
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

from .storage import get_db_connection

logger = logging.getLogger(__name__)


# ===== Permission Registry Functions =====

async def get_all_permissions(category: Optional[str] = None) -> List[Dict]:
    """
    Get all permissions from the registry.

    Args:
        category: Optional filter by category (feature, resource, system)

    Returns:
        List of permission dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()

    if category:
        cur.execute("""
            SELECT * FROM permissions
            WHERE category = ?
            ORDER BY category, subcategory, permission_key
        """, (category,))
    else:
        cur.execute("""
            SELECT * FROM permissions
            ORDER BY category, subcategory, permission_key
        """)

    rows = cur.fetchall()
    conn.close()

    permissions = []
    for row in rows:
        permissions.append({
            "permission_id": row['permission_id'],
            "permission_key": row['permission_key'],
            "permission_name": row['permission_name'],
            "permission_description": row['permission_description'],
            "category": row['category'],
            "subcategory": row['subcategory'],
            "permission_type": row['permission_type'],
            "is_system": bool(row['is_system']),
            "created_at": row['created_at']
        })

    return permissions


# ===== Permission Profile Functions =====

async def get_all_profiles(team_id: Optional[str] = None) -> List[Dict]:
    """
    Get all permission profiles, optionally filtered by team.

    Args:
        team_id: Optional team ID to filter by

    Returns:
        List of profile dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM permission_profiles
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    profiles = []
    for row in rows:
        profiles.append({
            "profile_id": row['profile_id'],
            "profile_name": row['profile_name'],
            "profile_description": row['profile_description'],
            "team_id": row['team_id'],
            "applies_to_role": row['applies_to_role'],
            "created_by": row['created_by'],
            "created_at": row['created_at'],
            "modified_at": row['modified_at'],
            "is_active": bool(row['is_active'])
        })

    return profiles


async def create_profile(
    profile_name: str,
    profile_description: Optional[str],
    team_id: Optional[str],
    applies_to_role: Optional[str],
    created_by: str
) -> Dict:
    """
    Create a new permission profile.

    Args:
        profile_name: Name of the profile
        profile_description: Optional description
        team_id: Optional team ID this profile belongs to
        applies_to_role: Optional role this profile applies to
        created_by: User ID creating the profile

    Returns:
        Created profile dictionary
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Generate profile ID
    profile_id = f"profile_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    cur.execute("""
        INSERT INTO permission_profiles (
            profile_id, profile_name, profile_description, team_id,
            applies_to_role, created_by, created_at, modified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile_id,
        profile_name,
        profile_description,
        team_id,
        applies_to_role,
        created_by,
        now,
        now,
        1
    ))

    conn.commit()
    conn.close()

    return {
        "profile_id": profile_id,
        "profile_name": profile_name,
        "profile_description": profile_description,
        "team_id": team_id,
        "applies_to_role": applies_to_role,
        "created_by": created_by,
        "created_at": now,
        "modified_at": now,
        "is_active": True
    }


async def get_profile(profile_id: str) -> Dict:
    """
    Get a specific permission profile.

    Args:
        profile_id: ID of the profile to retrieve

    Returns:
        Profile dictionary

    Raises:
        HTTPException: If profile not found
    """
    from fastapi import HTTPException  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM permission_profiles
        WHERE profile_id = ?
    """, (profile_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "profile_id": row['profile_id'],
        "profile_name": row['profile_name'],
        "profile_description": row['profile_description'],
        "team_id": row['team_id'],
        "applies_to_role": row['applies_to_role'],
        "created_by": row['created_by'],
        "created_at": row['created_at'],
        "modified_at": row['modified_at'],
        "is_active": bool(row['is_active'])
    }


async def update_profile(
    profile_id: str,
    updates: Dict[str, Any],
    modified_by: str
) -> Dict:
    """
    Update a permission profile.

    Args:
        profile_id: ID of the profile to update
        updates: Dictionary of fields to update (profile_name, profile_description, is_active)
        modified_by: User ID making the update

    Returns:
        Updated profile dictionary

    Raises:
        HTTPException: If profile not found or no fields to update
    """
    from fastapi import HTTPException  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    existing = cur.fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    # Build update statement
    update_parts = []
    params = []

    if "profile_name" in updates and updates["profile_name"] is not None:
        update_parts.append("profile_name = ?")
        params.append(updates["profile_name"])

    if "profile_description" in updates and updates["profile_description"] is not None:
        update_parts.append("profile_description = ?")
        params.append(updates["profile_description"])

    if "is_active" in updates and updates["is_active"] is not None:
        update_parts.append("is_active = ?")
        params.append(1 if updates["is_active"] else 0)

    if not update_parts:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    update_parts.append("modified_at = ?")
    params.append(datetime.now(UTC).isoformat())

    params.append(profile_id)

    cur.execute(f"""
        UPDATE permission_profiles
        SET {', '.join(update_parts)}
        WHERE profile_id = ?
    """, params)

    conn.commit()

    # Fetch updated profile
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    row = cur.fetchone()
    conn.close()

    return {
        "profile_id": row['profile_id'],
        "profile_name": row['profile_name'],
        "profile_description": row['profile_description'],
        "team_id": row['team_id'],
        "applies_to_role": row['applies_to_role'],
        "created_by": row['created_by'],
        "created_at": row['created_at'],
        "modified_at": row['modified_at'],
        "is_active": bool(row['is_active'])
    }


async def update_profile_grants(
    profile_id: str,
    grants: List[Dict],
    modified_by: str
) -> Dict:
    """
    Upsert permission grants for a profile.

    Args:
        profile_id: ID of the profile
        grants: List of grant dictionaries with permission_id, is_granted, permission_level, permission_scope
        modified_by: User ID making the changes

    Returns:
        Success status with count of grants updated

    Raises:
        HTTPException: If profile not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    for grant in grants:
        # Convert scope dict to JSON if present
        scope_json = json.dumps(grant.get("permission_scope")) if grant.get("permission_scope") else None

        cur.execute("""
            INSERT INTO profile_permissions (
                profile_id, permission_id, is_granted, permission_level, permission_scope
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, permission_id) DO UPDATE SET
                is_granted = excluded.is_granted,
                permission_level = excluded.permission_level,
                permission_scope = excluded.permission_scope
        """, (
            profile_id,
            grant["permission_id"],
            1 if grant.get("is_granted", True) else 0,
            grant.get("permission_level"),
            scope_json
        ))

    conn.commit()

    # Invalidate cache for all users with this profile (before closing connection)
    engine = get_permission_engine()
    cur.execute("SELECT user_id FROM user_permission_profiles WHERE profile_id = ?", (profile_id,))
    affected_users = [row['user_id'] for row in cur.fetchall()]

    conn.close()

    # Invalidate cache for affected users
    for user_id in affected_users:
        engine.invalidate_user_permissions(user_id)

    # Audit log - Profile permissions modified
    audit_log_sync(
        user_id=modified_by,
        action=AuditAction.PERMISSION_MODIFIED,
        resource="permission_profile",
        resource_id=profile_id,
        details={
            "grants_updated": len(grants),
            "permissions": [grant["permission_id"] for grant in grants],
            "affected_users": len(affected_users)
        }
    )

    return {"status": "success", "grants_updated": len(grants)}


async def get_profile_grants(profile_id: str) -> List[Dict]:
    """
    Get all permission grants for a profile.

    Args:
        profile_id: ID of the profile

    Returns:
        List of grant dictionaries with permission details
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT pp.*, p.permission_key, p.permission_name, p.permission_type
        FROM profile_permissions pp
        JOIN permissions p ON pp.permission_id = p.permission_id
        WHERE pp.profile_id = ?
        ORDER BY p.category, p.subcategory, p.permission_key
    """, (profile_id,))

    rows = cur.fetchall()
    conn.close()

    grants = []
    for row in rows:
        scope_data = None
        if row['permission_scope']:
            try:
                scope_data = json.loads(row['permission_scope'])
            except (json.JSONDecodeError, TypeError):
                pass  # Invalid JSON in scope

        grants.append({
            "permission_id": row['permission_id'],
            "permission_key": row['permission_key'],
            "permission_name": row['permission_name'],
            "permission_type": row['permission_type'],
            "is_granted": bool(row['is_granted']),
            "permission_level": row['permission_level'],
            "permission_scope": scope_data
        })

    return grants


# ===== User Assignment Functions =====

async def assign_profile_to_user(
    profile_id: str,
    user_id: str,
    assigning_user_id: str
) -> Dict:
    """
    Assign a permission profile to a user.

    Args:
        profile_id: ID of the profile to assign
        user_id: ID of the user to assign to
        assigning_user_id: ID of the user making the assignment

    Returns:
        Success status with user_id and profile_id

    Raises:
        HTTPException: If profile or user not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    # Check if user exists
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(UTC).isoformat()

    cur.execute("""
        INSERT INTO user_permission_profiles (
            user_id, profile_id, assigned_by, assigned_at
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, profile_id) DO UPDATE SET
            assigned_by = excluded.assigned_by,
            assigned_at = excluded.assigned_at
    """, (user_id, profile_id, assigning_user_id, now))

    conn.commit()
    conn.close()

    # Audit log - Profile granted to user
    audit_log_sync(
        user_id=assigning_user_id,
        action=AuditAction.PROFILE_GRANTED,
        resource="permission_profile",
        resource_id=profile_id,
        details={
            "target_user_id": user_id,
            "profile_id": profile_id
        }
    )

    # Invalidate user's permission cache
    engine = get_permission_engine()
    engine.invalidate_user_permissions(user_id)

    return {"status": "success", "user_id": user_id, "profile_id": profile_id}


async def unassign_profile_from_user(
    profile_id: str,
    user_id: str,
    unassigning_user_id: str
) -> Dict:
    """
    Unassign a permission profile from a user.

    Args:
        profile_id: ID of the profile to unassign
        user_id: ID of the user to unassign from
        unassigning_user_id: ID of the user making the unassignment

    Returns:
        Success status with user_id and profile_id

    Raises:
        HTTPException: If assignment not found
    """
    from fastapi import HTTPException  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM user_permission_profiles
        WHERE user_id = ? AND profile_id = ?
    """, (user_id, profile_id))

    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Audit log - Profile revoked from user
    audit_log_sync(
        user_id=unassigning_user_id,
        action=AuditAction.PROFILE_REVOKED,
        resource="permission_profile",
        resource_id=profile_id,
        details={
            "target_user_id": user_id,
            "profile_id": profile_id
        }
    )

    # Invalidate user's permission cache
    engine = get_permission_engine()
    engine.invalidate_user_permissions(user_id)

    return {"status": "success", "user_id": user_id, "profile_id": profile_id}


async def get_user_profiles(user_id: str) -> List[Dict]:
    """
    Get all permission profiles assigned to a user.

    Args:
        user_id: ID of the user

    Returns:
        List of profile dictionaries with assignment info
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT pp.*, upp.assigned_by, upp.assigned_at
        FROM user_permission_profiles upp
        JOIN permission_profiles pp ON upp.profile_id = pp.profile_id
        WHERE upp.user_id = ?
        ORDER BY upp.assigned_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    profiles = []
    for row in rows:
        profiles.append({
            "profile_id": row['profile_id'],
            "profile_name": row['profile_name'],
            "profile_description": row['profile_description'],
            "applies_to_role": row['applies_to_role'],
            "is_active": bool(row['is_active']),
            "assigned_by": row['assigned_by'],
            "assigned_at": row['assigned_at']
        })

    return profiles


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


# ===== Cache Invalidation Functions =====

async def invalidate_user_permissions(user_id: str, invalidating_user_id: str) -> Dict:
    """
    Invalidate permission cache for a specific user.

    Forces the permission engine to reload user permissions from database on next check.
    Useful after manually modifying permissions or troubleshooting permission issues.

    Args:
        user_id: ID of the user whose cache to invalidate
        invalidating_user_id: ID of the user performing the invalidation

    Returns:
        Success status with user_id and cache_invalidated flag
    """
    from permission_engine import get_permission_engine  # Lazy import
    from audit_logger import audit_log_sync, AuditAction  # Lazy import

    engine = get_permission_engine()
    engine.invalidate_user_permissions(user_id)

    # Audit log - Cache invalidation (using PERMISSION_MODIFIED as closest match)
    audit_log_sync(
        user_id=invalidating_user_id,
        action=AuditAction.PERMISSION_MODIFIED,
        resource="permission_cache",
        resource_id=user_id,
        details={
            "action": "cache_invalidation",
            "target_user_id": user_id
        }
    )

    return {"status": "success", "user_id": user_id, "cache_invalidated": True}
