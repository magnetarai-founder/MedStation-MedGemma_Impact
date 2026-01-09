"""
Permission Profile Management

Handles permission profiles - named sets of permissions that can be assigned to users.
Profiles are role-based (e.g., "Admin", "Editor") and define what permissions a user has.

Extracted from admin.py during P2 decomposition.
"""

import sqlite3
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

from .storage import get_db_connection

logger = logging.getLogger(__name__)


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


__all__ = [
    "get_all_profiles",
    "create_profile",
    "get_profile",
    "update_profile",
    "update_profile_grants",
    "get_profile_grants",
]
