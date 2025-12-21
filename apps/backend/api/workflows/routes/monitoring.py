"""
SLA & Monitoring Endpoints

Overdue items and workflow statistics.
"""

from fastapi import APIRouter, Depends
from typing import Any, Dict, List
import logging

from ..dependencies import (
    orchestrator,
    get_current_user,
    WorkItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overdue", response_model=List[WorkItem])
async def get_overdue_items(current_user: Dict = Depends(get_current_user)):
    """
    Get all overdue work items

    Args:
        current_user: Authenticated user

    Returns:
        List of overdue work items
    """
    user_id = current_user["user_id"]
    overdue = orchestrator.check_overdue_items(user_id=user_id)

    logger.info(f"Overdue items: {len(overdue)}")

    return overdue


@router.get("/statistics/{workflow_id}")
async def get_workflow_statistics(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get statistics for a workflow

    Args:
        workflow_id: Workflow ID
        current_user: Authenticated user

    Returns:
        Dictionary of statistics
    """
    user_id = current_user["user_id"]
    stats = orchestrator.get_workflow_statistics(workflow_id, user_id=user_id)

    return stats


__all__ = ["router"]
