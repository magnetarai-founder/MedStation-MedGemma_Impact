"""
Model Recommendations API - Sprint 6 Theme C (Ticket C3)

GET /api/v1/models/recommendations - Get recommended models based on task and performance
"""

from fastapi import APIRouter, Depends, Query, Request
from typing import Literal, Optional
import logging

from api.dependencies import get_current_user
from api.services.recommendations import get_recommendations_service, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"]
)


@router.get("/recommendations", name="get_model_recommendations")
async def get_model_recommendations(
    request: Request,
    task: TaskType = Query("general", description="Task type: code, chat, analysis, or general"),
    limit: int = Query(3, ge=1, le=10, description="Maximum number of recommendations"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get intelligent model recommendations based on performance metrics

    Recommendations are:
    - Filtered by team policy (allowed_models)
    - Scored based on latency, satisfaction, and efficiency
    - Weighted according to task type

    Args:
        task: Type of task (code, chat, analysis, general)
        limit: Maximum number of recommendations (1-10)

    Returns:
        List of recommended models with scores, reasons, and metrics
    """
    user_id = current_user["user_id"]
    team_id = current_user.get("team_id")

    try:
        recommendations_service = get_recommendations_service()

        recommendations = recommendations_service.get_recommendations(
            task=task,
            team_id=team_id,
            user_id=user_id,
            limit=limit
        )

        return {
            "task": task,
            "recommendations": recommendations,
            "count": len(recommendations)
        }

    except Exception as e:
        logger.error(f"Failed to get model recommendations: {e}", exc_info=True)
        return {
            "task": task,
            "recommendations": [],
            "count": 0,
            "error": "Failed to generate recommendations"
        }
