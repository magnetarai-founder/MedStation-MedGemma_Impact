"""
Team Invitations Routes

Handles team invite and join operations.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, HTTPException, Request, status

from api.routes.schemas import SuccessResponse
from api.errors import http_400, http_404, http_429, http_500
from api.utils import get_user_id

router = APIRouter(prefix="/api/v1/team", tags=["team-invitations"])


@router.post(
    "/{team_id}/invites",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    name="teams_create_invite",
    summary="Create team invite",
    description="Create a pending invite for a user to join the team"
)
async def create_invite_endpoint(request: Request, team_id: str) -> SuccessResponse:
    """Create a pending invite"""
    # Lazy imports
    from api.services.team import get_team_manager, require_team_admin
    from api.schemas.team_models import InviteRequest
    from permission_engine import require_perm
    from audit_logger import audit_log_sync
    import logging

    logger = logging.getLogger(__name__)

    # Permission check
    user = request.state.user
    require_perm("team.use")(lambda: None)()
    require_team_admin(team_id, get_user_id(user))

    try:
        body_data = await request.json()
        body = InviteRequest(**body_data)
        tm = get_team_manager()
        result = await tm.create_invite(team_id, body.email_or_username, body.role, get_user_id(user))

        # Audit log
        audit_log_sync(
            user_id=get_user_id(user),
            action="team.invite.created",
            resource_type="team",
            resource_id=team_id,
            details={"invite_id": result["invite_id"], "role": body.role}
        )

        return SuccessResponse(
            data=result,
            message=f"Invite created successfully for '{body.email_or_username}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create invite for team {team_id}", exc_info=True)
        raise http_500("Failed to create invite")


@router.post(
    "/invites/{invite_id}/accept",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_accept_invite",
    summary="Accept team invite",
    description="Accept a pending team invitation"
)
async def accept_invite_endpoint(request: Request, invite_id: str) -> SuccessResponse:
    """Accept an invite"""
    # Lazy imports
    from api.services.team import get_team_manager
    from permission_engine import get_permission_engine
    from audit_logger import audit_log_sync
    import logging

    logger = logging.getLogger(__name__)

    user = request.state.user

    try:
        tm = get_team_manager()
        result = await tm.accept_invite(invite_id, get_user_id(user))

        # Invalidate permission cache
        get_permission_engine().invalidate_user_permissions(get_user_id(user))

        # Audit log
        audit_log_sync(
            user_id=get_user_id(user),
            action="team.invite.accepted",
            resource_type="team",
            resource_id=result["team_id"],
            details={"invite_id": invite_id}
        )

        return SuccessResponse(
            data=result,
            message="Invite accepted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to accept invite {invite_id}", exc_info=True)
        raise http_500("Failed to accept invite")


@router.get(
    "/{team_id}/invite-code",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_get_invite_code",
    summary="Get invite code",
    description="Get active invite code for team"
)
async def get_invite_code_endpoint(request: Request, team_id: str) -> SuccessResponse:
    """Get active invite code for team"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import InviteCodeResponse
    import logging

    logger = logging.getLogger(__name__)

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise http_404("Team not found", resource="team")

        code = await tm.get_active_invite_code(team_id)

        if not code:
            raise http_404("No active invite code found", resource="invite_code")

        return SuccessResponse(
            data=InviteCodeResponse(code=code, team_id=team_id, expires_at=None),
            message="Invite code retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get invite code for team {team_id}", exc_info=True)
        raise http_500("Failed to retrieve invite code")


@router.post(
    "/{team_id}/invite-code/regenerate",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_regenerate_invite_code",
    summary="Regenerate invite code",
    description="Generate a new invite code for team"
)
async def regenerate_invite_code_endpoint(request: Request, team_id: str) -> SuccessResponse:
    """Generate a new invite code"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import InviteCodeResponse
    import logging

    logger = logging.getLogger(__name__)

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise http_404("Team not found", resource="team")

        code = await tm.regenerate_invite_code(team_id)

        return SuccessResponse(
            data=InviteCodeResponse(code=code, team_id=team_id, expires_at=None),
            message="Invite code regenerated successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to regenerate invite code for team {team_id}", exc_info=True)
        raise http_500("Failed to regenerate invite code")


@router.post(
    "/join",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_join",
    summary="Join team",
    description="Join a team using an invite code (rate limited: 10 attempts per minute)"
)
async def join_team_endpoint(request: Request) -> SuccessResponse:
    """Join a team using an invite code"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import JoinTeamRequest, JoinTeamResponse
    from rate_limiter import rate_limiter, get_client_ip
    import logging

    logger = logging.getLogger(__name__)

    # Rate limit check
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"team:join:{client_ip}", max_requests=10, window_seconds=60):
        raise http_429("Rate limit exceeded. Max 10 join attempts per minute")

    try:
        body_data = await request.json()
        body = JoinTeamRequest(**body_data)
        tm = get_team_manager()

        # Validate invite code
        team_id = await tm.validate_invite_code(body.invite_code, client_ip)

        if not team_id:
            raise http_400("Invalid, expired, or already used invite code")

        # Get team details
        team = await tm.get_team(team_id)
        if not team:
            raise http_404("Team not found", resource="team")

        # Join team
        success = await tm.join_team(team_id, body.user_id, role='member')

        if not success:
            raise http_400("Failed to join team. You may already be a member")

        join_response = JoinTeamResponse(
            success=True,
            team_id=team_id,
            team_name=team['name'],
            user_role='member'
        )

        return SuccessResponse(
            data=join_response,
            message=f"Successfully joined team '{team['name']}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to join team", exc_info=True)
        raise http_500("Failed to join team")
