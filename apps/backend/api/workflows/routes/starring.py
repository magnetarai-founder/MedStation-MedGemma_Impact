"""
Starring Functionality Endpoints

Star/unstar workflows and list starred workflows.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
import logging

from ..dependencies import (
    orchestrator,
    require_perm,
    get_current_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/workflows/{workflow_id}/star")
@require_perm("workflows.view", level="read")
async def star_workflow(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Star a workflow (max 5 per workflow type)

    Args:
        workflow_id: Workflow ID to star
        current_user: Authenticated user

    Returns:
        Success status and message
    """
    user_id = current_user["user_id"]

    success = orchestrator.storage.star_workflow(workflow_id, user_id)

    if success:
        return {"success": True, "message": "Workflow starred successfully"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Cannot star workflow. You may have reached the limit of 5 starred workflows per type."
        )


@router.delete("/workflows/{workflow_id}/star")
@require_perm("workflows.view", level="read")
async def unstar_workflow(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Unstar a workflow

    Args:
        workflow_id: Workflow ID to unstar
        current_user: Authenticated user

    Returns:
        Success status
    """
    user_id = current_user["user_id"]

    orchestrator.storage.unstar_workflow(workflow_id, user_id)

    return {"success": True, "message": "Workflow unstarred successfully"}


@router.get("/workflows/starred/list")
@require_perm("workflows.view", level="read")
async def get_starred_workflows(
    workflow_type: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get list of starred workflow IDs for current user

    Args:
        workflow_type: Optional filter by workflow type ('local' or 'team')
        current_user: Authenticated user

    Returns:
        List of starred workflow IDs
    """
    user_id = current_user["user_id"]

    starred_ids = orchestrator.storage.get_starred_workflows(user_id, workflow_type)

    return {"starred_workflows": starred_ids}


__all__ = ["router"]
