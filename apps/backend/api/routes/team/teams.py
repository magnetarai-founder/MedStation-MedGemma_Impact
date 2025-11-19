"""
Team CRUD Routes

Handles team entity management:
- Create team
- Get team details
- List user teams
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


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


@router.get("/user/{user_id}/teams", name="teams_get_user_teams")
async def get_user_teams_endpoint(request: Request, user_id: str):
    """Get all teams a user is a member of"""
    # Lazy imports
    from api.services.team import get_team_manager
    import asyncio

    try:
        tm = get_team_manager()
        teams = await tm.get_user_teams(user_id)
        return {"user_id": user_id, "teams": teams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
