"""
Team members router - Handles team member management and role operations.

Extracted from team.py for better organization.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, HTTPException, Request, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{team_id}/members",
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    name="teams_get_members"
)
async def get_members_endpoint(request: Request, team_id: str) -> SuccessResponse[list]:
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
        return SuccessResponse(data=members, message="Team members retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team members for team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve team members"
            ).model_dump()
        )


@router.put(
    "/{team_id}/members/{user_id}/role",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_change_role"
)
async def change_role_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Team super_admin required"
                ).model_dump()
            )

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

        return SuccessResponse(data=result, message="Member role changed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change role for user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to change member role"
            ).model_dump()
        )


@router.delete(
    "/{team_id}/members/{user_id}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_remove_member"
)
async def remove_member_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Team super_admin required"
                ).model_dump()
            )

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

        return SuccessResponse(data=result, message="Team member removed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove user {user_id} from team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove team member"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/{user_id}/role",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_update_role"
)
async def update_role_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Team not found"
                ).model_dump()
            )

        # Validate role
        valid_roles = ['god_rights', 'super_admin', 'admin', 'member', 'guest']
        if body.new_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                ).model_dump()
            )

        # Update role
        success, message = await tm.update_member_role(
            team_id=team_id,
            user_id=user_id,
            new_role=body.new_role,
            requesting_user_role=body.requesting_user_role,
            requesting_user_id=body.requesting_user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = UpdateRoleResponse(
            success=True,
            message=message,
            user_id=user_id,
            team_id=team_id,
            new_role=body.new_role
        )
        return SuccessResponse(data=result.model_dump(), message="Team member role updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update role for user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update member role"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/auto-promote",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_auto_promote"
)
async def auto_promote_endpoint(request: Request, team_id: str, required_days: int = 7) -> SuccessResponse[dict]:
    """Auto-promote guests who have been members for X days"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import AutoPromoteResponse

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Team not found"
                ).model_dump()
            )

        results = await tm.auto_promote_guests(team_id, required_days)
        promoted_count = sum(1 for r in results if r['promoted'])

        result = AutoPromoteResponse(
            promoted_users=results,
            total_promoted=promoted_count
        )
        return SuccessResponse(data=result.model_dump(), message=f"Auto-promoted {promoted_count} team members")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-promote members in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to auto-promote members"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/{user_id}/instant-promote",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_instant_promote"
)
async def instant_promote_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = InstantPromoteResponse(success=True, message=message, user_id=user_id, team_id=team_id)
        return SuccessResponse(data=result.model_dump(), message="Member promoted instantly")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to instant promote user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to instant promote member"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/{user_id}/delayed-promote",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_delayed_promote"
)
async def delayed_promote_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = DelayedPromoteResponse(success=True, message=message, user_id=user_id, team_id=team_id)
        return SuccessResponse(data=result.model_dump(), message="Delayed promotion scheduled")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule delayed promotion for user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to schedule delayed promotion"
            ).model_dump()
        )


@router.post(
    "/delayed-promotions/execute",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_execute_delayed"
)
async def execute_delayed_endpoint(request: Request) -> SuccessResponse[dict]:
    """Execute delayed promotions that are due"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import ExecuteDelayedResponse

    try:
        tm = get_team_manager()
        results = await tm.execute_delayed_promotions()

        result = ExecuteDelayedResponse(
            executed_promotions=results,
            total_executed=len(results)
        )
        return SuccessResponse(data=result.model_dump(), message=f"Executed {len(results)} delayed promotions")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute delayed promotions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to execute delayed promotions"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/heartbeat",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_heartbeat"
)
async def heartbeat_endpoint(request: Request, team_id: str) -> SuccessResponse[dict]:
    """Record member heartbeat"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import HeartbeatRequest, HeartbeatResponse

    try:
        body_data = await request.json()
        body = HeartbeatRequest(**body_data)
        tm = get_team_manager()

        success, message = await tm.record_heartbeat(team_id, body.user_id)

        result = HeartbeatResponse(success=success, message=message)
        return SuccessResponse(data=result.model_dump(), message="Heartbeat recorded")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record heartbeat for team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to record heartbeat"
            ).model_dump()
        )


@router.get(
    "/{team_id}/super-admins/status",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_offline_status"
)
async def offline_status_endpoint(request: Request, team_id: str) -> SuccessResponse[dict]:
    """Get offline super admins status"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import OfflineSuperAdminsResponse

    try:
        tm = get_team_manager()
        offline_admins = await tm.get_offline_super_admins(team_id)

        result = OfflineSuperAdminsResponse(
            offline_admins=offline_admins,
            count=len(offline_admins)
        )
        return SuccessResponse(data=result.model_dump(), message="Offline super admins retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get offline super admins for team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get offline super admins"
            ).model_dump()
        )


@router.post(
    "/{team_id}/promote-temp-admin",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_promote_temp_admin"
)
async def promote_temp_admin_endpoint(request: Request, team_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = PromoteTempAdminResponse(success=True, message=message)
        return SuccessResponse(data=result.model_dump(), message="Temporary admin promoted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to promote temp admin in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to promote temporary admin"
            ).model_dump()
        )


@router.get(
    "/{team_id}/temp-promotions",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_temp_promotions"
)
async def get_temp_promotions_endpoint(request: Request, team_id: str) -> SuccessResponse[dict]:
    """Get temporary promotions"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TempPromotionsResponse

    try:
        tm = get_team_manager()
        temp_promotions = await tm.get_temp_promotions(team_id)

        result = TempPromotionsResponse(
            temp_promotions=temp_promotions,
            count=len(temp_promotions)
        )
        return SuccessResponse(data=result.model_dump(), message="Temporary promotions retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get temp promotions for team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get temporary promotions"
            ).model_dump()
        )


@router.post(
    "/{team_id}/temp-promotions/{temp_promotion_id}/approve",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_approve_temp"
)
async def approve_temp_endpoint(request: Request, team_id: str, temp_promotion_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = ApproveTempPromotionResponse(success=True, message=message)
        return SuccessResponse(data=result.model_dump(), message="Temporary promotion approved")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve temp promotion {temp_promotion_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to approve temporary promotion"
            ).model_dump()
        )


@router.post(
    "/{team_id}/temp-promotions/{temp_promotion_id}/revert",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_revert_temp"
)
async def revert_temp_endpoint(request: Request, team_id: str, temp_promotion_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = RevertTempPromotionResponse(success=True, message=message)
        return SuccessResponse(data=result.model_dump(), message="Temporary promotion reverted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revert temp promotion {temp_promotion_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to revert temporary promotion"
            ).model_dump()
        )


@router.post(
    "/{team_id}/members/{user_id}/job-role",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_update_job_role"
)
async def update_job_role_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=message
                ).model_dump()
            )

        result = UpdateJobRoleResponse(success=True, message=message)
        return SuccessResponse(data=result.model_dump(), message="Job role updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job role for user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update job role"
            ).model_dump()
        )


@router.get(
    "/{team_id}/members/{user_id}/job-role",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="teams_get_job_role"
)
async def get_job_role_endpoint(request: Request, team_id: str, user_id: str) -> SuccessResponse[dict]:
    """Get a member's job role"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import JobRoleResponse

    try:
        tm = get_team_manager()
        job_role = await tm.get_job_role(team_id, user_id)

        result = JobRoleResponse(user_id=user_id, job_role=job_role)
        return SuccessResponse(data=result.model_dump(), message="Job role retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job role for user {user_id} in team {team_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get job role"
            ).model_dump()
        )
