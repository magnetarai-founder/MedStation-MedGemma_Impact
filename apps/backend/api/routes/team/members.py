"""
Team members router - Handles team member management and role operations.

Extracted from team.py for better organization.
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


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
