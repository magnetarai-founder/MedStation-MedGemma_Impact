"""
Team permissions router - Handles workflow, queue, god rights, and vault permissions.

Extracted from team.py for better organization.
Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)
router = APIRouter()


# ===== User Permissions =====

class UserPermissionsResponse(BaseModel):
    can_access_documents: bool
    can_access_automation: bool
    can_access_vault: bool


@router.get(
    "/user/permissions",
    response_model=SuccessResponse[UserPermissionsResponse],
    status_code=status.HTTP_200_OK,
    name="get_user_permissions",
    summary="Get user permissions",
    description="Get current user's permissions for workspace features"
)
async def get_user_permissions(request: Request) -> SuccessResponse[UserPermissionsResponse]:
    """Get current user's permissions for workspace features"""
    try:
        # For now, return all true - can be enhanced with actual permission checks
        permissions_data = UserPermissionsResponse(
            can_access_documents=True,
            can_access_automation=True,
            can_access_vault=True
        )
        return SuccessResponse(
            data=permissions_data,
            message="User permissions retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get user permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve user permissions"
            ).model_dump()
        )


# ===== Workflow Permissions =====

@router.post(
    "/{team_id}/workflows/{workflow_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="teams_add_workflow_perm",
    summary="Add workflow permission",
    description="Add a permission to a workflow"
)
async def add_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str) -> SuccessResponse[Dict]:
    """Add workflow permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import AddWorkflowPermissionRequest, AddWorkflowPermissionResponse

    try:
        body_data = await request.json()
        body = AddWorkflowPermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.add_workflow_permission(
            team_id=team_id,
            workflow_id=workflow_id,
            permission_type=body.permission_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add workflow permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to add workflow permission"
            ).model_dump()
        )


@router.delete(
    "/{team_id}/workflows/{workflow_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_remove_workflow_perm",
    summary="Remove workflow permission",
    description="Remove a permission from a workflow"
)
async def remove_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str) -> SuccessResponse[Dict]:
    """Remove workflow permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import RemoveWorkflowPermissionRequest, RemoveWorkflowPermissionResponse

    try:
        body_data = await request.json()
        body = RemoveWorkflowPermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.remove_workflow_permission(
            team_id=team_id,
            workflow_id=workflow_id,
            permission_type=body.permission_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove workflow permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove workflow permission"
            ).model_dump()
        )


@router.get(
    "/{team_id}/workflows/{workflow_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_workflow_perms",
    summary="Get workflow permissions",
    description="Get all permissions for a workflow"
)
async def get_workflow_perms_endpoint(request: Request, team_id: str, workflow_id: str) -> SuccessResponse[Dict]:
    """Get workflow permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetWorkflowPermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_workflow_permissions(team_id, workflow_id)

        data = {
            "workflow_id": workflow_id,
            "team_id": team_id,
            "permissions": permissions
        }
        return SuccessResponse(
            data=data,
            message="Workflow permissions retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get workflow permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve workflow permissions"
            ).model_dump()
        )


@router.post(
    "/{team_id}/workflows/{workflow_id}/check-permission",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_check_workflow_perm",
    summary="Check workflow permission",
    description="Check if a user has a specific workflow permission"
)
async def check_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str) -> SuccessResponse[Dict]:
    """Check workflow permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CheckWorkflowPermissionRequest, CheckWorkflowPermissionResponse

    try:
        body_data = await request.json()
        body = CheckWorkflowPermissionRequest(**body_data)
        tm = get_team_manager()

        has_permission, message = await tm.check_workflow_permission(
            team_id=team_id,
            workflow_id=workflow_id,
            user_id=body.user_id,
            permission_type=body.permission_type
        )

        return SuccessResponse(
            data={"has_permission": has_permission},
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to check workflow permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to check workflow permission"
            ).model_dump()
        )


# ===== Queue CRUD + Permissions =====

@router.post(
    "/{team_id}/queues",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="teams_create_queue",
    summary="Create queue",
    description="Create a new queue for the team"
)
async def create_queue_endpoint(request: Request, team_id: str) -> SuccessResponse[Dict]:
    """Create a queue"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CreateQueueRequest, CreateQueueResponse

    try:
        body_data = await request.json()
        body = CreateQueueRequest(**body_data)
        tm = get_team_manager()

        success, message, queue_id = await tm.create_queue(
            team_id=team_id,
            queue_name=body.queue_name,
            queue_type=body.queue_type,
            description=body.description
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True, "queue_id": queue_id},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create queue: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to create queue"
            ).model_dump()
        )


@router.post(
    "/{team_id}/queues/{queue_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="teams_add_queue_perm",
    summary="Add queue permission",
    description="Add a permission to a queue"
)
async def add_queue_perm_endpoint(request: Request, team_id: str, queue_id: str) -> SuccessResponse[Dict]:
    """Add queue permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import AddQueuePermissionRequest, AddQueuePermissionResponse

    try:
        body_data = await request.json()
        body = AddQueuePermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.add_queue_permission(
            team_id=team_id,
            queue_id=queue_id,
            access_type=body.access_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add queue permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to add queue permission"
            ).model_dump()
        )


@router.delete(
    "/{team_id}/queues/{queue_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_remove_queue_perm",
    summary="Remove queue permission",
    description="Remove a permission from a queue"
)
async def remove_queue_perm_endpoint(request: Request, team_id: str, queue_id: str) -> SuccessResponse[Dict]:
    """Remove queue permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import RemoveQueuePermissionRequest, RemoveQueuePermissionResponse

    try:
        body_data = await request.json()
        body = RemoveQueuePermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.remove_queue_permission(
            team_id=team_id,
            queue_id=queue_id,
            access_type=body.access_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove queue permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove queue permission"
            ).model_dump()
        )


@router.get(
    "/{team_id}/queues/{queue_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_queue_perms",
    summary="Get queue permissions",
    description="Get all permissions for a queue"
)
async def get_queue_perms_endpoint(request: Request, team_id: str, queue_id: str) -> SuccessResponse[Dict]:
    """Get queue permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetQueuePermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_queue_permissions(team_id, queue_id)

        data = {
            "queue_id": queue_id,
            "team_id": team_id,
            "permissions": permissions
        }
        return SuccessResponse(
            data=data,
            message="Queue permissions retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get queue permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve queue permissions"
            ).model_dump()
        )


@router.post(
    "/{team_id}/queues/{queue_id}/check-access",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_check_queue_access",
    summary="Check queue access",
    description="Check if a user has access to a queue"
)
async def check_queue_access_endpoint(request: Request, team_id: str, queue_id: str) -> SuccessResponse[Dict]:
    """Check queue access"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CheckQueueAccessRequest, CheckQueueAccessResponse

    try:
        body_data = await request.json()
        body = CheckQueueAccessRequest(**body_data)
        tm = get_team_manager()

        has_access, message = await tm.check_queue_access(
            team_id=team_id,
            queue_id=queue_id,
            user_id=body.user_id,
            access_type=body.access_type
        )

        return SuccessResponse(
            data={"has_access": has_access},
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to check queue access: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to check queue access"
            ).model_dump()
        )


@router.get(
    "/{team_id}/queues/accessible/{user_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_accessible_queues",
    summary="Get accessible queues",
    description="Get all queues accessible to a user"
)
async def get_accessible_queues_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[Dict]:
    """Get accessible queues for a user"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetAccessibleQueuesResponse

    try:
        tm = get_team_manager()
        queues = await tm.get_accessible_queues(team_id, user_id)

        data = {
            "team_id": team_id,
            "user_id": user_id,
            "queues": queues,
            "count": len(queues)
        }
        return SuccessResponse(
            data=data,
            message="Accessible queues retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get accessible queues: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve accessible queues"
            ).model_dump()
        )


@router.get(
    "/{team_id}/queues/{queue_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_queue",
    summary="Get queue details",
    description="Get details of a specific queue"
)
async def get_queue_endpoint(request: Request, team_id: str, queue_id: str) -> SuccessResponse[Dict]:
    """Get queue details"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import QueueDetails

    try:
        tm = get_team_manager()
        queue = await tm.get_queue(team_id, queue_id)

        if not queue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error=ErrorCode.NOT_FOUND,
                    message="Queue not found"
                ).model_dump()
            )

        return SuccessResponse(
            data=queue,
            message="Queue retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get queue: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve queue"
            ).model_dump()
        )


# ===== God Rights =====

@router.post(
    "/god-rights/grant",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="teams_grant_god_rights",
    summary="Grant god rights",
    description="Grant god rights to a user"
)
async def grant_god_rights_endpoint(request: Request) -> SuccessResponse[Dict]:
    """Grant god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GrantGodRightsRequest, GrantGodRightsResponse

    try:
        body_data = await request.json()
        body = GrantGodRightsRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.grant_god_rights(
            user_id=body.user_id,
            delegated_by=body.delegated_by,
            auth_key=body.auth_key
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to grant god rights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to grant god rights"
            ).model_dump()
        )


@router.post(
    "/god-rights/revoke",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_revoke_god_rights",
    summary="Revoke god rights",
    description="Revoke god rights from a user"
)
async def revoke_god_rights_endpoint(request: Request) -> SuccessResponse[Dict]:
    """Revoke god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import RevokeGodRightsRequest, RevokeGodRightsResponse

    try:
        body_data = await request.json()
        body = RevokeGodRightsRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.revoke_god_rights(
            user_id=body.user_id,
            revoked_by=body.revoked_by
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke god rights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to revoke god rights"
            ).model_dump()
        )


@router.post(
    "/god-rights/check",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_check_god_rights",
    summary="Check god rights",
    description="Check if a user has god rights"
)
async def check_god_rights_endpoint(request: Request) -> SuccessResponse[Dict]:
    """Check god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CheckGodRightsRequest, CheckGodRightsResponse

    try:
        body_data = await request.json()
        body = CheckGodRightsRequest(**body_data)
        tm = get_team_manager()

        has_god_rights, message = await tm.check_god_rights(body.user_id)

        return SuccessResponse(
            data={"has_god_rights": has_god_rights},
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to check god rights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to check god rights"
            ).model_dump()
        )


@router.get(
    "/god-rights/users",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_god_rights_users",
    summary="Get god rights users",
    description="Get all users with god rights"
)
async def get_god_rights_users_endpoint(request: Request) -> SuccessResponse[Dict]:
    """Get god rights users"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetGodRightsUsersResponse

    try:
        tm = get_team_manager()
        users = await tm.get_god_rights_users()

        return SuccessResponse(
            data={"users": users, "count": len(users)},
            message="God rights users retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get god rights users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve god rights users"
            ).model_dump()
        )


@router.get(
    "/god-rights/revoked",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_revoked_god_rights",
    summary="Get revoked god rights",
    description="Get all users with revoked god rights"
)
async def get_revoked_god_rights_endpoint(request: Request) -> SuccessResponse[Dict]:
    """Get revoked god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetRevokedGodRightsResponse

    try:
        tm = get_team_manager()
        users = await tm.get_revoked_god_rights()

        return SuccessResponse(
            data={"users": users, "count": len(users)},
            message="Revoked god rights retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get revoked god rights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve revoked god rights"
            ).model_dump()
        )


# ===== Vault Item Permissions =====

@router.post(
    "/{team_id}/vault/items/{item_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="teams_add_vault_perm",
    summary="Add vault permission",
    description="Add a permission to a vault item"
)
async def add_vault_perm_endpoint(request: Request, team_id: str, item_id: str) -> SuccessResponse[Dict]:
    """Add vault permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import AddVaultPermissionRequest, AddVaultPermissionResponse

    try:
        body_data = await request.json()
        body = AddVaultPermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.add_vault_permission(
            team_id=team_id,
            item_id=item_id,
            permission_type=body.permission_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add vault permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to add vault permission"
            ).model_dump()
        )


@router.delete(
    "/{team_id}/vault/items/{item_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_remove_vault_perm",
    summary="Remove vault permission",
    description="Remove a permission from a vault item"
)
async def remove_vault_perm_endpoint(request: Request, team_id: str, item_id: str) -> SuccessResponse[Dict]:
    """Remove vault permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import RemoveVaultPermissionRequest, RemoveVaultPermissionResponse

    try:
        body_data = await request.json()
        body = RemoveVaultPermissionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.remove_vault_permission(
            team_id=team_id,
            item_id=item_id,
            permission_type=body.permission_type,
            grant_type=body.grant_type,
            grant_value=body.grant_value
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        return SuccessResponse(
            data={"success": True},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove vault permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove vault permission"
            ).model_dump()
        )


@router.get(
    "/{team_id}/vault/items/{item_id}/permissions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_vault_perms",
    summary="Get vault permissions",
    description="Get all permissions for a vault item"
)
async def get_vault_perms_endpoint(request: Request, team_id: str, item_id: str) -> SuccessResponse[Dict]:
    """Get vault permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetVaultPermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_vault_permissions(team_id, item_id)

        data = {
            "item_id": item_id,
            "team_id": team_id,
            "permissions": permissions
        }
        return SuccessResponse(
            data=data,
            message="Vault permissions retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get vault permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve vault permissions"
            ).model_dump()
        )


@router.post(
    "/{team_id}/vault/items/{item_id}/check-permission",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="teams_check_vault_perm",
    summary="Check vault permission",
    description="Check if a user has a specific vault permission"
)
async def check_vault_perm_endpoint(request: Request, team_id: str, item_id: str) -> SuccessResponse[Dict]:
    """Check vault permission"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CheckVaultPermissionRequest, CheckVaultPermissionResponse

    try:
        body_data = await request.json()
        body = CheckVaultPermissionRequest(**body_data)
        tm = get_team_manager()

        has_permission, reason = await tm.check_vault_permission(
            team_id=team_id,
            item_id=item_id,
            user_id=body.user_id,
            permission_type=body.permission_type
        )

        return SuccessResponse(
            data={"has_permission": has_permission, "reason": reason},
            message="Vault permission check completed"
        )
    except Exception as e:
        logger.error(f"Failed to check vault permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorCode.INTERNAL_ERROR,
                message="Failed to check vault permission"
            ).model_dump()
        )
