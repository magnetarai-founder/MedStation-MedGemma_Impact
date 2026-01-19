"""
Team CRUD Routes

Handles team entity management (create, get details, list user teams).

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, HTTPException, Request, status

from api.routes.schemas import SuccessResponse
from api.errors import http_404, http_500

router = APIRouter(prefix="/api/v1/team", tags=["teams"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    name="teams_create",
    summary="Create team",
    description="Create a new team with specified name and description"
)
async def create_team_endpoint(request: Request) -> SuccessResponse:
    """Create a new team"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TeamResponse, CreateTeamRequest
    from permission_engine import require_perm
    from audit_logger import audit_log_sync, AuditAction
    import logging

    logger = logging.getLogger(__name__)

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

        return SuccessResponse(
            data=TeamResponse(**result),
            message=f"Team '{body.name}' created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create team", exc_info=True)
        raise http_500("Failed to create team")


@router.post(
    "/create",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    name="teams_create_v2",
    summary="Create team (v2)",
    description="Create a new team (alternative endpoint)"
)
async def create_team_v2_endpoint(request: Request) -> SuccessResponse:
    """Create a new team (v2)"""
    # Lazy imports
    from api.services.team import get_team_manager
    from api.schemas.team_models import TeamResponse, CreateTeamRequest
    import logging

    logger = logging.getLogger(__name__)

    try:
        body_data = await request.json()
        body = CreateTeamRequest(**body_data)
        tm = get_team_manager()
        result = await tm.create_team(body.name, body.description, body.creator_user_id)

        return SuccessResponse(
            data=TeamResponse(**result),
            message=f"Team '{body.name}' created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create team (v2)", exc_info=True)
        raise http_500("Failed to create team")


@router.get(
    "/{team_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_get",
    summary="Get team details",
    description="Get team details by team ID"
)
async def get_team_endpoint(request: Request, team_id: str) -> SuccessResponse:
    """Get team details"""
    # Lazy imports
    from api.services.team import get_team_manager
    import logging

    logger = logging.getLogger(__name__)

    try:
        tm = get_team_manager()
        team = await tm.get_team(team_id)

        if not team:
            raise http_404("Team not found", resource="team")

        return SuccessResponse(
            data=team,
            message="Team retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get team {team_id}", exc_info=True)
        raise http_500("Failed to retrieve team")


@router.get(
    "/user/{user_id}/teams",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    name="teams_get_user_teams",
    summary="Get user teams",
    description="Get all teams a user is a member of"
)
async def get_user_teams_endpoint(request: Request, user_id: str) -> SuccessResponse:
    """Get all teams a user is a member of"""
    # Lazy imports
    from api.services.team import get_team_manager
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    try:
        tm = get_team_manager()
        teams = await tm.get_user_teams(user_id)

        return SuccessResponse(
            data={"user_id": user_id, "teams": teams},
            message=f"Retrieved {len(teams)} team(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get teams for user {user_id}", exc_info=True)
        raise http_500("Failed to retrieve user teams")
