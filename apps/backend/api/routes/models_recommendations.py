"""
Model Recommendations Routes

Provides intelligent model recommendations based on task type and performance metrics.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from typing import Dict, Any
import logging

# Auth
try:
    from api.auth_middleware import get_current_user
except ImportError:
    from ..auth_middleware import get_current_user
try:
    from api.utils import get_user_id
except ImportError:
    from ..utils import get_user_id
from api.services.recommendations import get_recommendations_service, TaskType
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"]
)


@router.get(
    "/recommendations",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_model_recommendations",
    summary="Get model recommendations",
    description="Get intelligent model recommendations based on task type and performance metrics"
)
async def get_model_recommendations(
    request: Request,
    task: TaskType = Query("general", description="Task type: code, chat, analysis, or general"),
    limit: int = Query(3, ge=1, le=10, description="Maximum number of recommendations"),
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get intelligent model recommendations based on performance metrics

    Recommendations are:
    - Filtered by team policy (allowed_models)
    - Scored based on latency, satisfaction, and efficiency
    - Weighted according to task type
    """
    user_id = get_user_id(current_user)
    team_id = current_user.get("team_id")

    try:
        recommendations_service = get_recommendations_service()

        recommendations = recommendations_service.get_recommendations(
            task=task,
            team_id=team_id,
            user_id=user_id,
            limit=limit
        )

        return SuccessResponse(
            data={
                "task": task,
                "recommendations": recommendations,
                "count": len(recommendations)
            },
            message=f"Retrieved {len(recommendations)} model recommendation(s) for {task} task"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get model recommendations", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to generate model recommendations"
            ).model_dump()
        )
