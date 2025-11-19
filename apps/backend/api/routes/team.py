"""
Teams router for ElohimOS - Team management endpoints.

Thin router that delegates to api/services/team.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Body
from typing import List, Optional

# Module-level safe imports
from api.auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/", name="teams_create")
async def create_team_endpoint(request: Request):
    """Create a new team"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TeamResponse, CreateTeamRequest
    from permission_engine import require_perm
    from audit_logger import audit_log_sync, AuditAction

    # Permission check
    user = request.state.user
    require_perm("system.manage_users")(lambda: None)()

    try:
        body_data = await request.json()
        body = CreateTeamRequest(**body_data)
        tm = get_team_manager()
        result = await tm.create_team(body.name, body.description, body.creator_user_id)

        # Audit log
        audit_log_sync(
            user_id=user.get("user_id"),
            action=AuditAction.CREATE,
            resource_type="team",
            resource_id=result["team_id"],
            details={"team_name": body.name}
        )

        return TeamResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/invites", name="teams_create_invite")
async def create_invite_endpoint(request: Request, team_id: str):
    """Create a pending invite"""
    # Lazy imports
    from api.services.team import get_team_manager, require_team_admin
    from api.schemas.team_models import InviteRequest
    from permission_engine import require_perm
    from audit_logger import audit_log_sync

    # Permission check
    user = request.state.user
    require_perm("team.use")(lambda: None)()
    require_team_admin(team_id, user["user_id"])

    try:
        body_data = await request.json()
        body = InviteRequest(**body_data)
        tm = get_team_manager()
        result = await tm.create_invite(team_id, body.email_or_username, body.role, user["user_id"])

        # Audit log
        audit_log_sync(
            user_id=user["user_id"],
            action="team.invite.created",
            resource_type="team",
            resource_id=team_id,
            details={"invite_id": result["invite_id"], "role": body.role}
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invites/{invite_id}/accept", name="teams_accept_invite")
async def accept_invite_endpoint(request: Request, invite_id: str):
    """Accept an invite"""
    # Lazy imports
    from api.services.team import get_team_manager
    from permission_engine import get_permission_engine
    from audit_logger import audit_log_sync

    user = request.state.user

    try:
        tm = get_team_manager()
        result = await tm.accept_invite(invite_id, user["user_id"])

        # Invalidate permission cache
        get_permission_engine().invalidate_user_permissions(user["user_id"])

        # Audit log
        audit_log_sync(
            user_id=user["user_id"],
            action="team.invite.accepted",
            resource_type="team",
            resource_id=result["team_id"],
            details={"invite_id": invite_id}
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", name="teams_create_v2")
async def create_team_v2_endpoint(request: Request):
    """Create a new team (v2)"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TeamResponse, CreateTeamRequest

    try:
        body_data = await request.json()
        body = CreateTeamRequest(**body_data)
        tm = get_team_manager()
        result = await tm.create_team(body.name, body.description, body.creator_user_id)

        return TeamResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}", name="teams_get")
async def get_team_endpoint(request: Request, team_id: str):
    """Get team details"""
    # Lazy imports
    from api.services.team import get_team_manager

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/members", name="teams_get_members")
async def get_members_endpoint(request: Request, team_id: str):
    """Get team members"""
    # Lazy imports
    from api.services.team import get_team_manager, require_team_admin
    from permission_engine import require_perm

    # Permission check
    user = request.state.user
    require_perm("team.use")(lambda: None)()

    # Allow founder regardless of membership
    if user.get("role") != "founder_rights":
        require_team_admin(team_id, user["user_id"])

    try:
        tm = get_team_manager()
        members = await tm.get_team_members(team_id)
        return members
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{team_id}/members/{user_id}/role", name="teams_change_role")
async def change_role_endpoint(request: Request, team_id: str, user_id: str):
    """Change a member's role"""
    # Lazy imports
    from api.services.team import get_team_manager, is_team_member
    from api.schemas.team_models import ChangeRoleBody
    from permission_engine import require_perm, get_permission_engine
    from audit_logger import audit_log_sync

    # Permission check
    current_user = request.state.user
    require_perm("team.use")(lambda: None)()

    if current_user.get("role") != "founder_rights":
        caller_role = is_team_member(team_id, current_user["user_id"])
        if caller_role != "super_admin":
            raise HTTPException(status_code=403, detail="Team super_admin required")

    try:
        body_data = await request.json()
        body = ChangeRoleBody(**body_data)
        tm = get_team_manager()
        result = await tm.change_member_role(team_id, user_id, body.role)

        # Invalidate permission cache
        get_permission_engine().invalidate_user_permissions(user_id)

        # Audit log
        audit_log_sync(
            user_id=current_user["user_id"],
            action="team.member.role.changed",
            resource_type="team",
            resource_id=team_id,
            details={"member": user_id, "new_role": body.role}
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{team_id}/members/{user_id}", name="teams_remove_member")
async def remove_member_endpoint(request: Request, team_id: str, user_id: str):
    """Remove a team member"""
    # Lazy imports
    from api.services.team import get_team_manager, is_team_member
    from permission_engine import require_perm, get_permission_engine
    from audit_logger import audit_log_sync

    # Permission check
    current_user = request.state.user
    require_perm("team.use")(lambda: None)()

    if current_user.get("role") != "founder_rights":
        caller_role = is_team_member(team_id, current_user["user_id"])
        if caller_role != "super_admin":
            raise HTTPException(status_code=403, detail="Team super_admin required")

    try:
        tm = get_team_manager()
        result = await tm.remove_member(team_id, user_id)

        # Invalidate permission cache
        get_permission_engine().invalidate_user_permissions(user_id)

        # Audit log
        audit_log_sync(
            user_id=current_user["user_id"],
            action="team.member.removed",
            resource_type="team",
            resource_id=team_id,
            details={"member": user_id}
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/teams", name="teams_get_user_teams")
async def get_user_teams_endpoint(request: Request, user_id: str):
    """Get all teams a user is a member of"""
    # Lazy imports
    from api.services.team import get_team_manager
    import asyncio

    try:
        tm = get_team_manager()
        teams = await asyncio.to_thread(tm.get_user_teams, user_id)
        return {"user_id": user_id, "teams": teams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/invite-code", name="teams_get_invite_code")
async def get_invite_code_endpoint(request: Request, team_id: str):
    """Get active invite code for team"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import InviteCodeResponse

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        code = await tm.get_active_invite_code(team_id)

        if not code:
            raise HTTPException(status_code=404, detail="No active invite code found")

        return InviteCodeResponse(code=code, team_id=team_id, expires_at=None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/invite-code/regenerate", name="teams_regenerate_invite_code")
async def regenerate_invite_code_endpoint(request: Request, team_id: str):
    """Generate a new invite code"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import InviteCodeResponse

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        code = await tm.regenerate_invite_code(team_id)
        return InviteCodeResponse(code=code, team_id=team_id, expires_at=None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/join", name="teams_join")
async def join_team_endpoint(request: Request):
    """Join a team using an invite code"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import JoinTeamRequest, JoinTeamResponse
    from rate_limiter import rate_limiter, get_client_ip

    # Rate limit check
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"team:join:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 join attempts per minute.")

    try:
        body_data = await request.json()
        body = JoinTeamRequest(**body_data)
        tm = get_team_manager()

        # Validate invite code
        team_id = await tm.validate_invite_code(body.invite_code, client_ip)

        if not team_id:
            raise HTTPException(status_code=400, detail="Invalid, expired, or already used invite code")

        # Get team details
        team = await tm.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Join team
        success = await tm.join_team(team_id, body.user_id, role='member')

        if not success:
            raise HTTPException(status_code=400, detail="Failed to join team. You may already be a member.")

        return JoinTeamResponse(
            success=True,
            team_id=team_id,
            team_name=team['name'],
            user_role='member'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/{user_id}/role", name="teams_update_role")
async def update_role_endpoint(request: Request, team_id: str, user_id: str):
    """Update a team member's role"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import UpdateRoleRequest, UpdateRoleResponse

    try:
        body_data = await request.json()
        body = UpdateRoleRequest(**body_data)
        tm = get_team_manager()

        # Verify team exists
        team = await tm.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Validate role
        valid_roles = ['god_rights', 'super_admin', 'admin', 'member', 'guest']
        if body.new_role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")

        # Update role
        success, message = await tm.update_member_role(
            team_id=team_id,
            user_id=user_id,
            new_role=body.new_role,
            requesting_user_role=body.requesting_user_role,
            requesting_user_id=body.requesting_user_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UpdateRoleResponse(
            success=True,
            message=message,
            user_id=user_id,
            team_id=team_id,
            new_role=body.new_role
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/auto-promote", name="teams_auto_promote")
async def auto_promote_endpoint(request: Request, team_id: str, required_days: int = 7):
    """Auto-promote guests who have been members for X days"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import AutoPromoteResponse

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        results = await tm.auto_promote_guests(team_id, required_days)
        promoted_count = sum(1 for r in results if r['promoted'])

        return AutoPromoteResponse(
            promoted_users=results,
            total_promoted=promoted_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/{user_id}/instant-promote", name="teams_instant_promote")
async def instant_promote_endpoint(request: Request, team_id: str, user_id: str):
    """Instant promote a member"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import InstantPromoteRequest, InstantPromoteResponse

    try:
        body_data = await request.json()
        body = InstantPromoteRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.instant_promote(
            team_id=team_id,
            user_id=user_id,
            approved_by_user_id=body.approved_by_user_id,
            auth_type=body.auth_type
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return InstantPromoteResponse(success=True, message=message, user_id=user_id, team_id=team_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/{user_id}/delayed-promote", name="teams_delayed_promote")
async def delayed_promote_endpoint(request: Request, team_id: str, user_id: str):
    """Schedule a delayed promotion"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import DelayedPromoteRequest, DelayedPromoteResponse

    try:
        body_data = await request.json()
        body = DelayedPromoteRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.delayed_promote(
            team_id=team_id,
            user_id=user_id,
            delay_days=body.delay_days,
            approved_by_user_id=body.approved_by_user_id,
            reason=body.reason
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return DelayedPromoteResponse(success=True, message=message, user_id=user_id, team_id=team_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delayed-promotions/execute", name="teams_execute_delayed")
async def execute_delayed_endpoint(request: Request):
    """Execute delayed promotions that are due"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import ExecuteDelayedResponse

    try:
        tm = get_team_manager()
        results = await tm.execute_delayed_promotions()

        return ExecuteDelayedResponse(
            executed_promotions=results,
            total_executed=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/heartbeat", name="teams_heartbeat")
async def heartbeat_endpoint(request: Request, team_id: str):
    """Record member heartbeat"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import HeartbeatRequest, HeartbeatResponse

    try:
        body_data = await request.json()
        body = HeartbeatRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.record_heartbeat(team_id, body.user_id)

        return HeartbeatResponse(success=success, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/super-admins/status", name="teams_offline_status")
async def offline_status_endpoint(request: Request, team_id: str):
    """Get offline super admins status"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import OfflineSuperAdminsResponse

    try:
        tm = get_team_manager()
        offline_admins = await tm.get_offline_super_admins(team_id)

        return OfflineSuperAdminsResponse(
            offline_admins=offline_admins,
            count=len(offline_admins)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/promote-temp-admin", name="teams_promote_temp_admin")
async def promote_temp_admin_endpoint(request: Request, team_id: str):
    """Promote a temporary admin"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import PromoteTempAdminRequest, PromoteTempAdminResponse

    try:
        body_data = await request.json()
        body = PromoteTempAdminRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.promote_temp_admin(
            team_id=team_id,
            offline_super_admin_id=body.offline_super_admin_id,
            requesting_user_role=body.requesting_user_role
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return PromoteTempAdminResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/temp-promotions", name="teams_get_temp_promotions")
async def get_temp_promotions_endpoint(request: Request, team_id: str):
    """Get temporary promotions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TempPromotionsResponse

    try:
        tm = get_team_manager()
        temp_promotions = await tm.get_temp_promotions(team_id)

        return TempPromotionsResponse(
            temp_promotions=temp_promotions,
            count=len(temp_promotions)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/temp-promotions/{temp_promotion_id}/approve", name="teams_approve_temp")
async def approve_temp_endpoint(request: Request, team_id: str, temp_promotion_id: str):
    """Approve a temporary promotion"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import ApproveTempPromotionRequest, ApproveTempPromotionResponse

    try:
        body_data = await request.json()
        body = ApproveTempPromotionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.approve_temp_promotion(
            team_id=team_id,
            temp_promotion_id=temp_promotion_id,
            approved_by=body.approved_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return ApproveTempPromotionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/temp-promotions/{temp_promotion_id}/revert", name="teams_revert_temp")
async def revert_temp_endpoint(request: Request, team_id: str, temp_promotion_id: str):
    """Revert a temporary promotion"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import RevertTempPromotionRequest, RevertTempPromotionResponse

    try:
        body_data = await request.json()
        body = RevertTempPromotionRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.revert_temp_promotion(
            team_id=team_id,
            temp_promotion_id=temp_promotion_id,
            reverted_by=body.reverted_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return RevertTempPromotionResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/members/{user_id}/job-role", name="teams_update_job_role")
async def update_job_role_endpoint(request: Request, team_id: str, user_id: str):
    """Update a member's job role"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import UpdateJobRoleRequest, UpdateJobRoleResponse

    try:
        body_data = await request.json()
        body = UpdateJobRoleRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.update_job_role(
            team_id=team_id,
            user_id=user_id,
            job_role=body.job_role
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UpdateJobRoleResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/members/{user_id}/job-role", name="teams_get_job_role")
async def get_job_role_endpoint(request: Request, team_id: str, user_id: str):
    """Get a member's job role"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import JobRoleResponse

    try:
        tm = get_team_manager()
        job_role = await tm.get_job_role(team_id, user_id)

        return JobRoleResponse(user_id=user_id, job_role=job_role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/{team_id}/vault/items", name="teams_create_vault_item")
async def create_vault_item_endpoint(request: Request, team_id: str):
    """Create a new team vault item"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import CreateVaultItemRequest, CreateVaultItemResponse

    try:
        body_data = await request.json()
        body = CreateVaultItemRequest(**body_data)
        tm = get_team_manager()

        # Verify team exists
        team = await tm.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message, item_id = await tm.create_vault_item(
            team_id=team_id,
            item_name=body.item_name,
            item_type=body.item_type,
            content=body.content,
            created_by=body.created_by,
            mime_type=body.mime_type,
            metadata=body.metadata
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return CreateVaultItemResponse(success=True, message=message, item_id=item_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/vault/items", name="teams_list_vault_items")
async def list_vault_items_endpoint(request: Request, team_id: str, user_id: str, item_type: str = None):
    """List vault items accessible to user"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import ListVaultItemsResponse

    try:
        tm = get_team_manager()

        # Verify team exists
        team = await tm.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        items = await tm.list_vault_items(team_id, user_id, item_type)

        return ListVaultItemsResponse(
            team_id=team_id,
            user_id=user_id,
            items=items,
            count=len(items)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/vault/items/{item_id}", name="teams_get_vault_item")
async def get_vault_item_endpoint(request: Request, team_id: str, item_id: str):
    """Get vault item details"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import VaultItemDetail

    try:
        tm = get_team_manager()
        item = await tm.get_vault_item(team_id, item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Vault item not found")

        return VaultItemDetail(**item)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{team_id}/vault/items/{item_id}", name="teams_update_vault_item")
async def update_vault_item_endpoint(request: Request, team_id: str, item_id: str):
    """Update vault item"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import UpdateVaultItemRequest, UpdateVaultItemResponse

    try:
        body_data = await request.json()
        body = UpdateVaultItemRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.update_vault_item(
            team_id=team_id,
            item_id=item_id,
            content=body.content,
            updated_by=body.updated_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UpdateVaultItemResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{team_id}/vault/items/{item_id}", name="teams_delete_vault_item")
async def delete_vault_item_endpoint(request: Request, team_id: str, item_id: str):
    """Delete vault item"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import DeleteVaultItemRequest, DeleteVaultItemResponse

    try:
        body_data = await request.json()
        body = DeleteVaultItemRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.delete_vault_item(
            team_id=team_id,
            item_id=item_id,
            deleted_by=body.deleted_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return DeleteVaultItemResponse(success=True, message=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


# ===== Model Policy Routes (Sprint 5) =====

@router.get("/{team_id}/model-policy", name="teams_get_model_policy")
async def get_model_policy_endpoint(
    request: Request,
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get model policy for a team

    Returns policy with allowed_models and default_model
    """
    from api.services.team_model_policy import get_policy_service
    from permissions import require_perm_team

    # Check permission: team.manage_models
    await require_perm_team("team.manage_models", current_user, team_id)

    try:
        policy_service = get_policy_service()
        policy = policy_service.get_policy(team_id)

        # If no policy set, return empty policy
        if not policy:
            return {
                "team_id": team_id,
                "allowed_models": [],
                "default_model": None,
                "updated_at": None
            }

        return policy

    except Exception as e:
        logger.error(f"Failed to get model policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/model-policy", name="teams_set_model_policy")
async def set_model_policy_endpoint(
    request: Request,
    team_id: str,
    allowed_models: List[str] = Body(...),
    default_model: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Set model policy for a team

    Body:
        {
            "allowed_models": ["llama3.2:3b", "qwen2.5-coder:7b"],
            "default_model": "llama3.2:3b"  // optional
        }

    Validates:
        - default_model must be in allowed_models if provided
    """
    from api.services.team_model_policy import get_policy_service
    from permissions import require_perm_team
    from audit_logger import get_audit_logger, AuditAction

    # Check permission: team.manage_models
    await require_perm_team("team.manage_models", current_user, team_id)

    try:
        policy_service = get_policy_service()

        # Validate default_model
        if default_model and default_model not in allowed_models:
            raise HTTPException(
                status_code=400,
                detail=f"Default model '{default_model}' must be in allowed_models"
            )

        # Set policy
        success = policy_service.set_policy(team_id, allowed_models, default_model)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set model policy")

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user["user_id"],
                action=AuditAction.MODEL_POLICY_UPDATED,
                resource="team",
                resource_id=team_id,
                details={
                    "allowed_models": allowed_models,
                    "default_model": default_model
                }
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        # Return updated policy
        return policy_service.get_policy(team_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set model policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
