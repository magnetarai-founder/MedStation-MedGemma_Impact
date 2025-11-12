"""
Permissions router for ElohimOS - RBAC management endpoints.

Thin router that delegates to api/services/permissions.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from typing import List, Optional

# Module-level safe imports
from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/permissions",
    tags=["permissions"],
    dependencies=[Depends(get_current_user)]
)


# ===== Permission Registry Endpoints =====

@router.get("/permissions", name="permissions_get_all")
async def get_all_permissions_endpoint(
    request: Request,
    category: Optional[str] = Query(None)
):
    """Get all permissions from the registry"""
    # Lazy imports
    from api.services import permissions
    from api.schemas.permission_models import PermissionModel
    from permission_engine import require_perm

    # Permission check
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_permissions(category)
        return [PermissionModel(**p) for p in result]
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Permission Profile Endpoints =====

@router.get("/profiles", name="permissions_get_profiles")
async def get_profiles_endpoint(
    request: Request,
    team_id: Optional[str] = Query(None)
):
    """Get all permission profiles"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionProfileModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_profiles(team_id)
        return [PermissionProfileModel(**p) for p in result]
    except Exception as e:
        logger.error(f"Failed to get profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles", name="permissions_create_profile")
async def create_profile_endpoint(request: Request):
    """Create a new permission profile"""
    from api.services import permissions
    from api.schemas.permission_models import CreateProfileRequest, PermissionProfileModel
    from permission_engine import require_perm

    user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        body_data = await request.json()
        body = CreateProfileRequest(**body_data)
        result = await permissions.create_profile(
            profile_name=body.profile_name,
            profile_description=body.profile_description,
            team_id=body.team_id,
            applies_to_role=body.applies_to_role,
            created_by=user["user_id"]
        )
        return PermissionProfileModel(**result)
    except Exception as e:
        logger.error(f"Failed to create profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", name="permissions_get_profile")
async def get_profile_endpoint(request: Request, profile_id: str):
    """Get a specific permission profile"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionProfileModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_profile(profile_id)
        return PermissionProfileModel(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profiles/{profile_id}", name="permissions_update_profile")
async def update_profile_endpoint(request: Request, profile_id: str):
    """Update a permission profile"""
    from api.services import permissions
    from api.schemas.permission_models import UpdateProfileRequest, PermissionProfileModel
    from permission_engine import require_perm

    user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        body_data = await request.json()
        body = UpdateProfileRequest(**body_data)

        # Build updates dictionary from request
        updates = {}
        if body.profile_name is not None:
            updates["profile_name"] = body.profile_name
        if body.profile_description is not None:
            updates["profile_description"] = body.profile_description
        if body.is_active is not None:
            updates["is_active"] = body.is_active

        result = await permissions.update_profile(
            profile_id=profile_id,
            updates=updates,
            modified_by=user["user_id"]
        )
        return PermissionProfileModel(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles/{profile_id}/grants", name="permissions_update_profile_grants")
async def update_profile_grants_endpoint(request: Request, profile_id: str):
    """
    Upsert permission grants for a profile

    Replaces existing grants for specified permissions.
    """
    from api.services import permissions
    from api.schemas.permission_models import ProfilePermissionGrant
    from permission_engine import require_perm

    user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        body_data = await request.json()
        grants_list = [ProfilePermissionGrant(**g) for g in body_data]

        # Convert Pydantic models to dicts
        grants_dicts = [g.dict() for g in grants_list]

        result = await permissions.update_profile_grants(
            profile_id=profile_id,
            grants=grants_dicts,
            modified_by=user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert profile grants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}/grants", name="permissions_get_profile_grants")
async def get_profile_grants_endpoint(request: Request, profile_id: str):
    """Get all permission grants for a profile"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_profile_grants(profile_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get profile grants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== User Assignment Endpoints =====

@router.post("/profiles/{profile_id}/assign/{user_id}", name="permissions_assign_profile")
async def assign_profile_endpoint(request: Request, profile_id: str, user_id: str):
    """Assign a permission profile to a user"""
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.assign_profile_to_user(
            profile_id=profile_id,
            user_id=user_id,
            assigning_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profiles/{profile_id}/assign/{user_id}", name="permissions_unassign_profile")
async def unassign_profile_endpoint(request: Request, profile_id: str, user_id: str):
    """Unassign a permission profile from a user"""
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.unassign_profile_from_user(
            profile_id=profile_id,
            user_id=user_id,
            unassigning_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unassign profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/profiles", name="permissions_get_user_profiles")
async def get_user_profiles_endpoint(request: Request, user_id: str):
    """Get all permission profiles assigned to a user"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_user_profiles(user_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get user profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Permission Set Endpoints =====

@router.get("/permission-sets", name="permissions_get_permission_sets")
async def get_permission_sets_endpoint(request: Request):
    """List all permission sets"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionSetModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_permission_sets()
        return [PermissionSetModel(**s) for s in result]
    except Exception as e:
        logger.error(f"Failed to get permission sets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permission-sets", name="permissions_create_permission_set")
async def create_permission_set_endpoint(request: Request):
    """Create a new permission set"""
    from api.services import permissions
    from api.schemas.permission_models import CreatePermissionSetRequest, PermissionSetModel
    from permission_engine import require_perm

    user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        body_data = await request.json()
        body = CreatePermissionSetRequest(**body_data)
        result = await permissions.create_permission_set(
            set_name=body.set_name,
            set_description=body.set_description,
            team_id=body.team_id,
            created_by=user["user_id"]
        )
        return PermissionSetModel(**result)
    except Exception as e:
        logger.error(f"Failed to create permission set: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permission-sets/{set_id}/assign/{user_id}", name="permissions_assign_permission_set")
async def assign_permission_set_endpoint(
    request: Request,
    set_id: str,
    user_id: str,
    expires_at: Optional[str] = Query(None)
):
    """Assign a permission set to a user"""
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.assign_permission_set_to_user(
            set_id=set_id,
            user_id=user_id,
            expires_at=expires_at,
            assigning_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign permission set: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/permission-sets/{set_id}/assign/{user_id}", name="permissions_unassign_permission_set")
async def unassign_permission_set_endpoint(request: Request, set_id: str, user_id: str):
    """Unassign a permission set from a user"""
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.unassign_permission_set_from_user(
            set_id=set_id,
            user_id=user_id,
            unassigning_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unassign permission set: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permission-sets/{set_id}/grants", name="permissions_update_permission_set_grants")
async def update_permission_set_grants_endpoint(request: Request, set_id: str):
    """
    Upsert permission grants for a permission set (Phase 2.5)

    Similar to profile grants, but for permission sets.
    Permission sets override profiles in the resolution order.
    """
    from api.services import permissions
    from api.schemas.permission_models import PermissionSetGrant
    from permission_engine import require_perm

    user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        body_data = await request.json()
        grants_list = [PermissionSetGrant(**g) for g in body_data]

        # Convert Pydantic models to dicts
        grants_dicts = [g.dict() for g in grants_list]

        result = await permissions.update_permission_set_grants(
            set_id=set_id,
            grants=grants_dicts,
            modified_by=user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert permission set grants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permission-sets/{set_id}/grants", name="permissions_get_permission_set_grants")
async def get_permission_set_grants_endpoint(request: Request, set_id: str):
    """Get all permission grants for a permission set (Phase 2.5)"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_permission_set_grants(set_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission set grants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/permission-sets/{set_id}/grants/{permission_id}", name="permissions_delete_permission_set_grant")
async def delete_permission_set_grant_endpoint(
    request: Request,
    set_id: str,
    permission_id: str
):
    """Delete a specific permission grant from a permission set (Phase 2.5)"""
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.delete_permission_set_grant(
            set_id=set_id,
            permission_id=permission_id,
            deleting_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete permission set grant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Phase 2.5: Cache Invalidation =====

@router.post("/users/{user_id}/permissions/invalidate", name="permissions_invalidate_user_permissions")
async def invalidate_user_permissions_endpoint(request: Request, user_id: str):
    """
    Invalidate permission cache for a specific user (Phase 2.5)

    Forces the permission engine to reload user permissions from database on next check.
    Useful after manually modifying permissions or troubleshooting permission issues.
    """
    from api.services import permissions
    from permission_engine import require_perm

    current_user = request.state.user
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.invalidate_user_permissions(
            user_id=user_id,
            invalidating_user_id=current_user["user_id"]
        )
        return result
    except Exception as e:
        logger.error(f"Failed to invalidate permission cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
