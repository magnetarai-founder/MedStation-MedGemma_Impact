"""
Queue Operations Endpoints

Role-based queue retrieval and user's active work.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import logging

from ..dependencies import (
    orchestrator,
    get_current_user,
    WorkItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/queues/{workflow_id}/role/{role_name}", response_model=List[WorkItem])
async def get_queue_for_role(
    workflow_id: str,
    role_name: str,
    stage_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get work items in queue for a role

    Args:
        workflow_id: Workflow ID
        role_name: Role name
        stage_id: Optional stage filter
        current_user: Authenticated user

    Returns:
        List of work items available for this role
    """
    user_id = current_user["user_id"]
    queue = orchestrator.get_queue_for_role(
        workflow_id=workflow_id,
        role_name=role_name,
        stage_id=stage_id,
        user_id=user_id,
    )

    logger.info(f"Queue for {role_name}: {len(queue)} items")

    return queue


@router.get("/my-work/{user_id}", response_model=List[WorkItem])
async def get_my_active_work(
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get all work items assigned to user

    Args:
        user_id: User ID (must match authenticated user)
        current_user: Authenticated user

    Returns:
        List of user's active work items
    """
    authenticated_user_id = current_user["user_id"]

    # Verify the user is requesting their own work
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot view other users' work")

    # Correct call signature
    my_work = orchestrator.get_my_active_work(authenticated_user_id)

    logger.info(f"My work for {user_id}: {len(my_work)} items")

    return my_work


__all__ = ["router"]
