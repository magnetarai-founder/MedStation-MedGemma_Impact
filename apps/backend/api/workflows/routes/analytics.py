"""
Workflow Analytics Endpoints

Comprehensive analytics for workflow performance.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging

from ..dependencies import (
    storage, analytics,
    require_perm,
    get_current_user,
    get_user_team_id,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analytics/{workflow_id}")
@require_perm("workflows.view", level="read")
async def get_workflow_analytics(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get comprehensive analytics for a workflow (Phase D).

    Returns metrics including:
    - Total/completed/in-progress items
    - Average cycle time
    - Per-stage metrics (entered, completed, avg time)

    Args:
        workflow_id: Workflow ID
        current_user: Authenticated user

    Returns:
        Analytics dictionary
    """
    user_id = current_user["user_id"]
    team_id = get_user_team_id(user_id)  # T3-1

    # T3-1: Verify access to workflow with visibility check
    workflow = storage.get_workflow(workflow_id, user_id=user_id, team_id=team_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found or access denied")

    # Compute analytics
    analytics_data = analytics.get_workflow_analytics(
        workflow_id=workflow_id,
        user_id=user_id,
    )

    return analytics_data


__all__ = ["router"]
