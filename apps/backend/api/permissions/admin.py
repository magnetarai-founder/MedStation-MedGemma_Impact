"""
Permission Administration

High-level admin and service functions for permission management.
Handles permission registry, profiles, permission sets, and user assignments.

Extracted from services/permissions.py during Phase 3 modularization.
Profile and Permission Set functions further extracted during P2 decomposition.
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime, UTC

from .storage import get_db_connection
from api.errors import http_404

# Import and re-export from submodules for backward compatibility
from .profiles import (
    get_all_profiles,
    create_profile,
    get_profile,
    update_profile,
    update_profile_grants,
    get_profile_grants,
)
from .sets import (
    get_all_permission_sets,
    create_permission_set,
    assign_permission_set_to_user,
    unassign_permission_set_from_user,
    update_permission_set_grants,
    get_permission_set_grants,
    delete_permission_set_grant,
)

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
    from audit_logger import audit_log_sync, AuditAction  # Lazy import
    from permission_engine import get_permission_engine  # Lazy import

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    if not cur.fetchone():
        conn.close()
        raise http_404("Profile not found", resource="profile")

    # Check if user exists
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise http_404("User not found", resource="user")

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
        raise http_404("Assignment not found", resource="user_permission_profile")

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
