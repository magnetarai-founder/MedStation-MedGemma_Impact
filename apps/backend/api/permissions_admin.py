"""
Permission Administration API

Admin endpoints for managing RBAC system:
- Permission registry
- Permission profiles
- Permission sets
- User assignments

All endpoints require system.manage_permissions permission (Super Admin/Founder only by default).
"""

import sqlite3
import logging
import json
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

try:
    from .permission_engine import require_perm
    from .auth_middleware import get_current_user
except ImportError:
    from permission_engine import require_perm
    from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


# ===== Pydantic Models =====

class PermissionModel(BaseModel):
    """Permission model"""
    permission_id: str
    permission_key: str
    permission_name: str
    permission_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    permission_type: str  # "boolean", "level", "scope"
    is_system: bool = False
    created_at: str


class PermissionProfileModel(BaseModel):
    """Permission profile model"""
    profile_id: str
    profile_name: str
    profile_description: Optional[str] = None
    team_id: Optional[str] = None
    applies_to_role: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    modified_at: str
    is_active: bool = True


class ProfilePermissionGrant(BaseModel):
    """Permission grant for a profile"""
    permission_id: str
    is_granted: bool = True
    permission_level: Optional[str] = None  # "none", "read", "write", "admin"
    permission_scope: Optional[dict] = None


class CreateProfileRequest(BaseModel):
    """Request to create a permission profile"""
    profile_name: str
    profile_description: Optional[str] = None
    team_id: Optional[str] = None
    applies_to_role: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    """Request to update a permission profile"""
    profile_name: Optional[str] = None
    profile_description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionSetModel(BaseModel):
    """Permission set model"""
    permission_set_id: str
    set_name: str
    set_description: Optional[str] = None
    team_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    is_active: bool = True


class CreatePermissionSetRequest(BaseModel):
    """Request to create a permission set"""
    set_name: str
    set_description: Optional[str] = None
    team_id: Optional[str] = None


class AssignProfileRequest(BaseModel):
    """Request to assign a profile to a user"""
    user_id: str


class AssignPermissionSetRequest(BaseModel):
    """Request to assign a permission set to a user"""
    user_id: str
    expires_at: Optional[str] = None


# ===== Helper Functions =====

def get_db_connection() -> sqlite3.Connection:
    """Get database connection"""
    try:
        from auth_middleware import auth_service
    except ImportError:
        from .auth_middleware import auth_service

    conn = sqlite3.connect(str(auth_service.db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ===== Permission Registry Endpoints =====

@router.get("/permissions", response_model=List[PermissionModel])
@require_perm("system.manage_permissions")
async def list_permissions(
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all permissions in registry

    Filter by category: feature, resource, system
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
        permissions.append(PermissionModel(
            permission_id=row['permission_id'],
            permission_key=row['permission_key'],
            permission_name=row['permission_name'],
            permission_description=row['permission_description'],
            category=row['category'],
            subcategory=row['subcategory'],
            permission_type=row['permission_type'],
            is_system=bool(row['is_system']),
            created_at=row['created_at']
        ))

    return permissions


# ===== Permission Profile Endpoints =====

@router.get("/profiles", response_model=List[PermissionProfileModel])
@require_perm("system.manage_permissions")
async def list_profiles(current_user: Dict = Depends(get_current_user)):
    """List all permission profiles"""
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
        profiles.append(PermissionProfileModel(
            profile_id=row['profile_id'],
            profile_name=row['profile_name'],
            profile_description=row['profile_description'],
            team_id=row['team_id'],
            applies_to_role=row['applies_to_role'],
            created_by=row['created_by'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            is_active=bool(row['is_active'])
        ))

    return profiles


@router.post("/profiles", response_model=PermissionProfileModel)
@require_perm("system.manage_permissions")
async def create_profile(
    request: CreateProfileRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new permission profile"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Generate profile ID
    import uuid
    profile_id = f"profile_{uuid.uuid4().hex[:12]}"

    now = datetime.utcnow().isoformat()

    try:
        cur.execute("""
            INSERT INTO permission_profiles (
                profile_id, profile_name, profile_description, team_id,
                applies_to_role, created_by, created_at, modified_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            request.profile_name,
            request.profile_description,
            request.team_id,
            request.applies_to_role,
            current_user['user_id'],
            now,
            now,
            1
        ))

        conn.commit()

        profile = PermissionProfileModel(
            profile_id=profile_id,
            profile_name=request.profile_name,
            profile_description=request.profile_description,
            team_id=request.team_id,
            applies_to_role=request.applies_to_role,
            created_by=current_user['user_id'],
            created_at=now,
            modified_at=now,
            is_active=True
        )

        conn.close()
        return profile

    except Exception as e:
        conn.close()
        logger.error(f"Failed to create profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")


@router.get("/profiles/{profile_id}", response_model=PermissionProfileModel)
@require_perm("system.manage_permissions")
async def get_profile(
    profile_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific permission profile"""
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

    return PermissionProfileModel(
        profile_id=row['profile_id'],
        profile_name=row['profile_name'],
        profile_description=row['profile_description'],
        team_id=row['team_id'],
        applies_to_role=row['applies_to_role'],
        created_by=row['created_by'],
        created_at=row['created_at'],
        modified_at=row['modified_at'],
        is_active=bool(row['is_active'])
    )


@router.put("/profiles/{profile_id}", response_model=PermissionProfileModel)
@require_perm("system.manage_permissions")
async def update_profile(
    profile_id: str,
    request: UpdateProfileRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Update a permission profile"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    existing = cur.fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    # Build update statement
    updates = []
    params = []

    if request.profile_name is not None:
        updates.append("profile_name = ?")
        params.append(request.profile_name)

    if request.profile_description is not None:
        updates.append("profile_description = ?")
        params.append(request.profile_description)

    if request.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if request.is_active else 0)

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("modified_at = ?")
    params.append(datetime.utcnow().isoformat())

    params.append(profile_id)

    try:
        cur.execute(f"""
            UPDATE permission_profiles
            SET {', '.join(updates)}
            WHERE profile_id = ?
        """, params)

        conn.commit()

        # Fetch updated profile
        cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
        row = cur.fetchone()

        conn.close()

        return PermissionProfileModel(
            profile_id=row['profile_id'],
            profile_name=row['profile_name'],
            profile_description=row['profile_description'],
            team_id=row['team_id'],
            applies_to_role=row['applies_to_role'],
            created_by=row['created_by'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            is_active=bool(row['is_active'])
        )

    except Exception as e:
        conn.close()
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.post("/profiles/{profile_id}/grants")
@require_perm("system.manage_permissions")
async def upsert_profile_grants(
    profile_id: str,
    grants: List[ProfilePermissionGrant],
    current_user: Dict = Depends(get_current_user)
):
    """
    Upsert permission grants for a profile

    Replaces existing grants for specified permissions.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if profile exists
    cur.execute("SELECT * FROM permission_profiles WHERE profile_id = ?", (profile_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        for grant in grants:
            # Convert scope dict to JSON if present
            scope_json = json.dumps(grant.permission_scope) if grant.permission_scope else None

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
                grant.permission_id,
                1 if grant.is_granted else 0,
                grant.permission_level,
                scope_json
            ))

        conn.commit()
        conn.close()

        return {"status": "success", "grants_updated": len(grants)}

    except Exception as e:
        conn.close()
        logger.error(f"Failed to upsert grants: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upsert grants: {str(e)}")


@router.get("/profiles/{profile_id}/grants")
@require_perm("system.manage_permissions")
async def get_profile_grants(
    profile_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get all permission grants for a profile"""
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
            except:
                pass

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


# ===== User Assignment Endpoints =====

@router.post("/profiles/{profile_id}/assign/{user_id}")
@require_perm("system.manage_permissions")
async def assign_profile_to_user(
    profile_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Assign a permission profile to a user"""
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

    try:
        now = datetime.utcnow().isoformat()

        cur.execute("""
            INSERT INTO user_permission_profiles (
                user_id, profile_id, assigned_by, assigned_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, profile_id) DO UPDATE SET
                assigned_by = excluded.assigned_by,
                assigned_at = excluded.assigned_at
        """, (user_id, profile_id, current_user['user_id'], now))

        conn.commit()
        conn.close()

        return {"status": "success", "user_id": user_id, "profile_id": profile_id}

    except Exception as e:
        conn.close()
        logger.error(f"Failed to assign profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign profile: {str(e)}")


@router.delete("/profiles/{profile_id}/assign/{user_id}")
@require_perm("system.manage_permissions")
async def unassign_profile_from_user(
    profile_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Unassign a permission profile from a user"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM user_permission_profiles
            WHERE user_id = ? AND profile_id = ?
        """, (user_id, profile_id))

        conn.commit()
        deleted = cur.rowcount
        conn.close()

        if deleted == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"status": "success", "user_id": user_id, "profile_id": profile_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Failed to unassign profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unassign profile: {str(e)}")


@router.get("/users/{user_id}/profiles")
@require_perm("system.manage_permissions")
async def get_user_profiles(
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get all permission profiles assigned to a user"""
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


# ===== Permission Set Endpoints =====

@router.get("/permission-sets", response_model=List[PermissionSetModel])
@require_perm("system.manage_permissions")
async def list_permission_sets(current_user: Dict = Depends(get_current_user)):
    """List all permission sets"""
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
        sets.append(PermissionSetModel(
            permission_set_id=row['permission_set_id'],
            set_name=row['set_name'],
            set_description=row['set_description'],
            team_id=row['team_id'],
            created_by=row['created_by'],
            created_at=row['created_at'],
            is_active=bool(row['is_active'])
        ))

    return sets


@router.post("/permission-sets", response_model=PermissionSetModel)
@require_perm("system.manage_permissions")
async def create_permission_set(
    request: CreatePermissionSetRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new permission set"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Generate set ID
    import uuid
    set_id = f"permset_{uuid.uuid4().hex[:12]}"

    now = datetime.utcnow().isoformat()

    try:
        cur.execute("""
            INSERT INTO permission_sets (
                permission_set_id, set_name, set_description, team_id,
                created_by, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            set_id,
            request.set_name,
            request.set_description,
            request.team_id,
            current_user['user_id'],
            now,
            1
        ))

        conn.commit()

        perm_set = PermissionSetModel(
            permission_set_id=set_id,
            set_name=request.set_name,
            set_description=request.set_description,
            team_id=request.team_id,
            created_by=current_user['user_id'],
            created_at=now,
            is_active=True
        )

        conn.close()
        return perm_set

    except Exception as e:
        conn.close()
        logger.error(f"Failed to create permission set: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create permission set: {str(e)}")


@router.post("/permission-sets/{set_id}/assign/{user_id}")
@require_perm("system.manage_permissions")
async def assign_permission_set_to_user(
    set_id: str,
    user_id: str,
    expires_at: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Assign a permission set to a user"""
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

    try:
        now = datetime.utcnow().isoformat()

        cur.execute("""
            INSERT INTO user_permission_sets (
                user_id, permission_set_id, assigned_by, assigned_at, expires_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, permission_set_id) DO UPDATE SET
                assigned_by = excluded.assigned_by,
                assigned_at = excluded.assigned_at,
                expires_at = excluded.expires_at
        """, (user_id, set_id, current_user['user_id'], now, expires_at))

        conn.commit()
        conn.close()

        return {"status": "success", "user_id": user_id, "permission_set_id": set_id}

    except Exception as e:
        conn.close()
        logger.error(f"Failed to assign permission set: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign permission set: {str(e)}")


@router.delete("/permission-sets/{set_id}/assign/{user_id}")
@require_perm("system.manage_permissions")
async def unassign_permission_set_from_user(
    set_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Unassign a permission set from a user"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM user_permission_sets
            WHERE user_id = ? AND permission_set_id = ?
        """, (user_id, set_id))

        conn.commit()
        deleted = cur.rowcount
        conn.close()

        if deleted == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"status": "success", "user_id": user_id, "permission_set_id": set_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Failed to unassign permission set: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unassign permission set: {str(e)}")
