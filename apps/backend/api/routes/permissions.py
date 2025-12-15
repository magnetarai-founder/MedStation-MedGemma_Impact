"""
Permissions router for ElohimOS - RBAC management endpoints.

Thin router that delegates to api/services/permissions.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, Query, status
from typing import List, Optional, Dict, Any

# Module-level safe imports
try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/permissions",
    tags=["permissions"],
    dependencies=[Depends(get_current_user)]
)


# ===== Permission Registry Endpoints =====

@router.get(
    "/permissions",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_all"
)
async def get_all_permissions_endpoint(
    request: Request,
    category: Optional[str] = Query(None)
) -> SuccessResponse[List[Dict]]:
    """Get all permissions from the registry"""
    # Lazy imports
    from api.services import permissions
    from api.schemas.permission_models import PermissionModel
    from permission_engine import require_perm

    # Permission check
    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_permissions(category)
        data = [PermissionModel(**p).model_dump() for p in result]
        return SuccessResponse(
            data=data,
            message=f"Retrieved {len(data)} permissions"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permissions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get permissions"
            ).model_dump()
        )


# ===== Permission Profile Endpoints =====

@router.get(
    "/profiles",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_profiles"
)
async def get_profiles_endpoint(
    request: Request,
    team_id: Optional[str] = Query(None)
) -> SuccessResponse[List[Dict]]:
    """Get all permission profiles"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionProfileModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_profiles(team_id)
        data = [PermissionProfileModel(**p).model_dump() for p in result]
        return SuccessResponse(
            data=data,
            message=f"Retrieved {len(data)} permission profiles"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profiles", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get permission profiles"
            ).model_dump()
        )


@router.post(
    "/profiles",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="permissions_create_profile"
)
async def create_profile_endpoint(request: Request) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=PermissionProfileModel(**result).model_dump(),
            message="Permission profile created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create permission profile"
            ).model_dump()
        )


@router.get(
    "/profiles/{profile_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_get_profile"
)
async def get_profile_endpoint(request: Request, profile_id: str) -> SuccessResponse[Dict]:
    """Get a specific permission profile"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionProfileModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_profile(profile_id)
        return SuccessResponse(
            data=PermissionProfileModel(**result).model_dump(),
            message="Permission profile retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get permission profile"
            ).model_dump()
        )


@router.put(
    "/profiles/{profile_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_update_profile"
)
async def update_profile_endpoint(request: Request, profile_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=PermissionProfileModel(**result).model_dump(),
            message="Permission profile updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update permission profile"
            ).model_dump()
        )


@router.post(
    "/profiles/{profile_id}/grants",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_update_profile_grants"
)
async def update_profile_grants_endpoint(request: Request, profile_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Profile grants updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert profile grants", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update profile grants"
            ).model_dump()
        )


@router.get(
    "/profiles/{profile_id}/grants",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_profile_grants"
)
async def get_profile_grants_endpoint(request: Request, profile_id: str) -> SuccessResponse[List[Dict]]:
    """Get all permission grants for a profile"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_profile_grants(profile_id)
        return SuccessResponse(
            data=result,
            message="Profile grants retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile grants", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get profile grants"
            ).model_dump()
        )


# ===== User Assignment Endpoints =====

@router.post(
    "/profiles/{profile_id}/assign/{user_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="permissions_assign_profile"
)
async def assign_profile_endpoint(request: Request, profile_id: str, user_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Profile assigned to user successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to assign profile to user"
            ).model_dump()
        )


@router.delete(
    "/profiles/{profile_id}/assign/{user_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_unassign_profile"
)
async def unassign_profile_endpoint(request: Request, profile_id: str, user_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Profile unassigned from user successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unassign profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unassign profile from user"
            ).model_dump()
        )


@router.get(
    "/users/{user_id}/profiles",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_user_profiles"
)
async def get_user_profiles_endpoint(request: Request, user_id: str) -> SuccessResponse[List[Dict]]:
    """Get all permission profiles assigned to a user"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_user_profiles(user_id)
        return SuccessResponse(
            data=result,
            message="User profiles retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profiles", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get user profiles"
            ).model_dump()
        )


# ===== Permission Set Endpoints =====

@router.get(
    "/permission-sets",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_permission_sets"
)
async def get_permission_sets_endpoint(request: Request) -> SuccessResponse[List[Dict]]:
    """List all permission sets"""
    from api.services import permissions
    from api.schemas.permission_models import PermissionSetModel
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_all_permission_sets()
        data = [PermissionSetModel(**s).model_dump() for s in result]
        return SuccessResponse(
            data=data,
            message=f"Retrieved {len(data)} permission sets"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission sets", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get permission sets"
            ).model_dump()
        )


@router.post(
    "/permission-sets",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="permissions_create_permission_set"
)
async def create_permission_set_endpoint(request: Request) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=PermissionSetModel(**result).model_dump(),
            message="Permission set created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create permission set", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create permission set"
            ).model_dump()
        )


@router.post(
    "/permission-sets/{set_id}/assign/{user_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="permissions_assign_permission_set"
)
async def assign_permission_set_endpoint(
    request: Request,
    set_id: str,
    user_id: str,
    expires_at: Optional[str] = Query(None)
) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Permission set assigned to user successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign permission set", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to assign permission set to user"
            ).model_dump()
        )


@router.delete(
    "/permission-sets/{set_id}/assign/{user_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_unassign_permission_set"
)
async def unassign_permission_set_endpoint(request: Request, set_id: str, user_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Permission set unassigned from user successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unassign permission set", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unassign permission set from user"
            ).model_dump()
        )


@router.post(
    "/permission-sets/{set_id}/grants",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_update_permission_set_grants"
)
async def update_permission_set_grants_endpoint(request: Request, set_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Permission set grants updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert permission set grants", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update permission set grants"
            ).model_dump()
        )


@router.get(
    "/permission-sets/{set_id}/grants",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="permissions_get_permission_set_grants"
)
async def get_permission_set_grants_endpoint(request: Request, set_id: str) -> SuccessResponse[List[Dict]]:
    """Get all permission grants for a permission set (Phase 2.5)"""
    from api.services import permissions
    from permission_engine import require_perm

    require_perm("system.manage_permissions")(lambda: None)()

    try:
        result = await permissions.get_permission_set_grants(set_id)
        return SuccessResponse(
            data=result,
            message="Permission set grants retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission set grants", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get permission set grants"
            ).model_dump()
        )


@router.delete(
    "/permission-sets/{set_id}/grants/{permission_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_delete_permission_set_grant"
)
async def delete_permission_set_grant_endpoint(
    request: Request,
    set_id: str,
    permission_id: str
) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="Permission set grant deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete permission set grant", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete permission set grant"
            ).model_dump()
        )


# ===== Phase 2.5: Cache Invalidation =====

@router.post(
    "/users/{user_id}/permissions/invalidate",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_invalidate_user_permissions"
)
async def invalidate_user_permissions_endpoint(request: Request, user_id: str) -> SuccessResponse[Dict]:
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
        return SuccessResponse(
            data=result,
            message="User permissions cache invalidated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate permission cache", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to invalidate permission cache"
            ).model_dump()
        )


# ===== Effective Permissions Endpoint =====

@router.get(
    "/effective",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="permissions_get_effective"
)
async def get_effective_permissions_endpoint(
    request: Request,
    team_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get effective permissions for the current user (read-only view)

    Returns:
        {
            "user_id": str,
            "role": str,
            "is_founder": bool,
            "team_id": str | None,
            "effective_permissions": {
                "permission_key": true | level | scope,
                ...
            }
        }
    """
    from permission_engine import get_permission_engine

    # Permission check is done via Depends(get_current_user) already

    try:
        engine = get_permission_engine()
        user_id = current_user["user_id"]

        # Get user's role
        role = current_user.get("role", "user")
        is_founder = role == "founder"

        # Get effective permissions by loading user context
        context = engine.load_user_context(user_id, team_id)

        data = {
            "user_id": user_id,
            "role": role,
            "is_founder": is_founder,
            "team_id": team_id,
            "effective_permissions": context.effective_permissions
        }

        return SuccessResponse(
            data=data,
            message="Effective permissions retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get effective permissions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get effective permissions"
            ).model_dump()
        )
