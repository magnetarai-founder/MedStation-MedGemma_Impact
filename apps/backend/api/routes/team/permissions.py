"""
Team permissions router - Handles workflow, queue, god rights, and vault permissions.

Extracted from team.py for better organization.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


# ===== User Permissions =====

class UserPermissionsResponse(BaseModel):
    can_access_documents: bool
    can_access_automation: bool
    can_access_vault: bool


@router.get("/permissions", name="get_user_permissions")
async def get_user_permissions(request: Request):
    """Get current user's permissions for workspace features"""
    # For now, return all true - can be enhanced with actual permission checks
    return UserPermissionsResponse(
        can_access_documents=True,
        can_access_automation=True,
        can_access_vault=True
    )


# ===== Workflow Permissions =====

@router.post("/{team_id}/workflows/{workflow_id}/permissions", name="teams_add_workflow_perm")
async def add_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return AddWorkflowPermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{team_id}/workflows/{workflow_id}/permissions", name="teams_remove_workflow_perm")
async def remove_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return RemoveWorkflowPermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/workflows/{workflow_id}/permissions", name="teams_get_workflow_perms")
async def get_workflow_perms_endpoint(request: Request, team_id: str, workflow_id: str):
    """Get workflow permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetWorkflowPermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_workflow_permissions(team_id, workflow_id)

        return GetWorkflowPermissionsResponse(
            workflow_id=workflow_id,
            team_id=team_id,
            permissions=permissions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/workflows/{workflow_id}/check-permission", name="teams_check_workflow_perm")
async def check_workflow_perm_endpoint(request: Request, team_id: str, workflow_id: str):
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

        return CheckWorkflowPermissionResponse(has_permission=has_permission, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Queue CRUD + Permissions =====

@router.post("/{team_id}/queues", name="teams_create_queue")
async def create_queue_endpoint(request: Request, team_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return CreateQueueResponse(success=True, message=message, queue_id=queue_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/queues/{queue_id}/permissions", name="teams_add_queue_perm")
async def add_queue_perm_endpoint(request: Request, team_id: str, queue_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return AddQueuePermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{team_id}/queues/{queue_id}/permissions", name="teams_remove_queue_perm")
async def remove_queue_perm_endpoint(request: Request, team_id: str, queue_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return RemoveQueuePermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/queues/{queue_id}/permissions", name="teams_get_queue_perms")
async def get_queue_perms_endpoint(request: Request, team_id: str, queue_id: str):
    """Get queue permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetQueuePermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_queue_permissions(team_id, queue_id)

        return GetQueuePermissionsResponse(
            queue_id=queue_id,
            team_id=team_id,
            permissions=permissions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/queues/{queue_id}/check-access", name="teams_check_queue_access")
async def check_queue_access_endpoint(request: Request, team_id: str, queue_id: str):
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

        return CheckQueueAccessResponse(has_access=has_access, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/queues/accessible/{user_id}", name="teams_get_accessible_queues")
async def get_accessible_queues_endpoint(request: Request, team_id: str, user_id: str):
    """Get accessible queues for a user"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetAccessibleQueuesResponse

    try:
        tm = get_team_manager()
        queues = await tm.get_accessible_queues(team_id, user_id)

        return GetAccessibleQueuesResponse(
            team_id=team_id,
            user_id=user_id,
            queues=queues,
            count=len(queues)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/queues/{queue_id}", name="teams_get_queue")
async def get_queue_endpoint(request: Request, team_id: str, queue_id: str):
    """Get queue details"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import QueueDetails

    try:
        tm = get_team_manager()
        queue = await tm.get_queue(team_id, queue_id)

        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        return QueueDetails(**queue)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== God Rights =====

@router.post("/god-rights/grant", name="teams_grant_god_rights")
async def grant_god_rights_endpoint(request: Request):
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
            raise HTTPException(status_code=400, detail=message)

        return GrantGodRightsResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/god-rights/revoke", name="teams_revoke_god_rights")
async def revoke_god_rights_endpoint(request: Request):
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
            raise HTTPException(status_code=400, detail=message)

        return RevokeGodRightsResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/god-rights/check", name="teams_check_god_rights")
async def check_god_rights_endpoint(request: Request):
    """Check god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CheckGodRightsRequest, CheckGodRightsResponse

    try:
        body_data = await request.json()
        body = CheckGodRightsRequest(**body_data)
        tm = get_team_manager()

        has_god_rights, message = await tm.check_god_rights(body.user_id)

        return CheckGodRightsResponse(has_god_rights=has_god_rights, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/god-rights/users", name="teams_get_god_rights_users")
async def get_god_rights_users_endpoint(request: Request):
    """Get god rights users"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetGodRightsUsersResponse

    try:
        tm = get_team_manager()
        users = await tm.get_god_rights_users()

        return GetGodRightsUsersResponse(users=users, count=len(users))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/god-rights/revoked", name="teams_get_revoked_god_rights")
async def get_revoked_god_rights_endpoint(request: Request):
    """Get revoked god rights"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetRevokedGodRightsResponse

    try:
        tm = get_team_manager()
        users = await tm.get_revoked_god_rights()

        return GetRevokedGodRightsResponse(users=users, count=len(users))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Vault Item Permissions =====

@router.post("/{team_id}/vault/items/{item_id}/permissions", name="teams_add_vault_perm")
async def add_vault_perm_endpoint(request: Request, team_id: str, item_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return AddVaultPermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{team_id}/vault/items/{item_id}/permissions", name="teams_remove_vault_perm")
async def remove_vault_perm_endpoint(request: Request, team_id: str, item_id: str):
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
            raise HTTPException(status_code=400, detail=message)

        return RemoveVaultPermissionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/vault/items/{item_id}/permissions", name="teams_get_vault_perms")
async def get_vault_perms_endpoint(request: Request, team_id: str, item_id: str):
    """Get vault permissions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import GetVaultPermissionsResponse

    try:
        tm = get_team_manager()
        permissions = await tm.get_vault_permissions(team_id, item_id)

        return GetVaultPermissionsResponse(
            item_id=item_id,
            team_id=team_id,
            permissions=permissions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/vault/items/{item_id}/check-permission", name="teams_check_vault_perm")
async def check_vault_perm_endpoint(request: Request, team_id: str, item_id: str):
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

        return CheckVaultPermissionResponse(has_permission=has_permission, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
