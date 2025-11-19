"""
Team invitations router - Handles team invite and join operations.

Extracted from team.py for better organization.
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


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
