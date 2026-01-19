"""
Work Item CRUD and Action Endpoints

Create, list, get work items + claim, start, complete, cancel actions.
"""

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from api.errors import http_400, http_404, http_429, http_500
from typing import List, Dict, Optional
from datetime import datetime, UTC
import logging

from ..dependencies import (
    orchestrator, workflow_sync,
    require_perm, get_current_user,
    rate_limiter,
    WorkItem, WorkItemStatus, WorkItemPriority,
    CreateWorkItemRequest, CompleteStageRequest, StageTransition,
)

from api.utils import sanitize_for_log, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# WORK ITEM CRUD
# ============================================

@router.post("/work-items", response_model=WorkItem)
@require_perm("workflows.create", level="write")
async def create_work_item(
    request: Request,
    body: CreateWorkItemRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new work item

    Args:
        request: Work item creation request
        current_user: Authenticated user

    Returns:
        Created work item

    Raises:
        HTTPException: If workflow not found
    """
    # Rate limit: 30 work item creations per minute per user
    user_id = current_user.get("user_id", "unknown")
    if not rate_limiter.check_rate_limit(f"create_work_item:{user_id}", max_requests=30, window_seconds=60):
        raise http_429("Rate limit exceeded. Max 30 work item creations per minute.")

    try:
        user_id = get_user_id(current_user)

        work_item = orchestrator.create_work_item(
            workflow_id=body.workflow_id,
            data=body.data,
            created_by=user_id,
            priority=body.priority or WorkItemPriority.NORMAL,
            tags=body.tags,
            user_id=user_id,
        )

        logger.info(f"Created work item: {work_item.id}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_created(work_item))
            except Exception as e:
                logger.error(f"Failed to broadcast work item creation: {e}")

        return work_item

    except ValueError as e:
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"Failed to create work item: {str(e)}")
        raise http_500(str(e))


@router.get("/work-items", response_model=List[WorkItem])
@require_perm("workflows.view", level="read")
async def list_work_items(
    workflow_id: Optional[str] = None,
    status: Optional[WorkItemStatus] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[WorkItemPriority] = None,
    limit: int = Query(default=50, le=100),
    current_user: Dict = Depends(get_current_user)
):
    """
    List work items with filters

    Args:
        workflow_id: Filter by workflow
        status: Filter by status
        assigned_to: Filter by assigned user
        priority: Filter by priority
        limit: Max results
        current_user: Authenticated user

    Returns:
        List of work items
    """
    user_id = get_user_id(current_user)
    # Use orchestrator method that filters by user_id
    items = orchestrator.list_work_items(
        user_id=user_id,
        workflow_id=workflow_id,
        status=status,
        assigned_to=assigned_to,
        priority=priority,
        limit=limit
    )

    return items


@router.get("/work-items/{work_item_id}", response_model=WorkItem)
async def get_work_item(
    work_item_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get work item by ID

    Args:
        work_item_id: Work item ID
        current_user: Authenticated user

    Returns:
        Work item

    Raises:
        HTTPException: If not found or access denied
    """
    user_id = get_user_id(current_user)
    # Use storage to ensure user isolation
    work_item = orchestrator.storage.get_work_item(work_item_id, user_id) if orchestrator.storage else None
    if not work_item:
        raise http_404(f"Work item not found or access denied: {work_item_id}", resource="work_item")

    return work_item


# ============================================
# WORK ITEM ACTIONS
# ============================================

@router.post("/work-items/{work_item_id}/claim", response_model=WorkItem)
@require_perm("workflows.edit", level="write")
async def claim_work_item(
    request: Request,
    work_item_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Claim a work item from queue

    Args:
        work_item_id: Work item ID
        current_user: Authenticated user

    Returns:
        Updated work item

    Raises:
        HTTPException: If cannot be claimed
    """
    # Rate limit: 60 claims per minute per user
    user_id = current_user.get("user_id", "unknown")
    if not rate_limiter.check_rate_limit(f"claim_work_item:{user_id}", max_requests=60, window_seconds=60):
        raise http_429("Rate limit exceeded. Max 60 claims per minute.")

    try:
        user_id = get_user_id(current_user)
        # Correct call signature (positional only)
        work_item = orchestrator.claim_work_item(work_item_id, user_id)
        logger.info(f"Work item {work_item_id} claimed by {user_id}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_claimed(work_item, user_id))
            except Exception as e:
                logger.error(f"Failed to broadcast work item claim: {e}")

        return work_item

    except ValueError as e:
        raise http_400(str(e))


@router.post("/work-items/{work_item_id}/start", response_model=WorkItem)
@require_perm("workflows.edit", level="write")
async def start_work(
    request: Request,
    work_item_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Start work on claimed item

    Args:
        work_item_id: Work item ID
        current_user: Authenticated user

    Returns:
        Updated work item
    """
    # Rate limit: 60 starts per minute per user
    user_id = current_user.get("user_id", "unknown")
    if not rate_limiter.check_rate_limit(f"start_work_item:{user_id}", max_requests=60, window_seconds=60):
        raise http_429("Rate limit exceeded. Max 60 starts per minute.")

    try:
        user_id = get_user_id(current_user)
        # Correct call signature (positional only)
        work_item = orchestrator.start_work(work_item_id, user_id)
        logger.info(f"Work item {work_item_id} started by {user_id}")
        return work_item

    except ValueError as e:
        raise http_400(str(e))


@router.post("/work-items/{work_item_id}/complete", response_model=WorkItem)
@require_perm("workflows.edit", level="write")
async def complete_stage(
    request: Request,
    body: CompleteStageRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Complete current stage and transition to next

    Args:
        request: Stage completion request
        current_user: Authenticated user

    Returns:
        Updated work item (possibly in new stage)

    Raises:
        HTTPException: If cannot complete
    """
    try:
        user_id = get_user_id(current_user)

        work_item = orchestrator.complete_stage(
            work_item_id=body.work_item_id,
            user_id=user_id,
            stage_data=body.data,
            notes=body.notes,
        )

        if work_item.status == WorkItemStatus.COMPLETED:
            safe_work_item_id = sanitize_for_log(body.work_item_id)
            logger.info(f"Work item {safe_work_item_id} completed")
        else:
            logger.info(f"Stage completed, transitioned to: {work_item.current_stage_name}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_completed(work_item))
            except Exception as e:
                logger.error(f"Failed to broadcast work item completion: {e}")

        return work_item

    except ValueError as e:
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"Failed to complete stage: {str(e)}")
        raise http_500(str(e))


@router.post("/work-items/{work_item_id}/cancel", response_model=WorkItem)
@require_perm("workflows.edit", level="write")
async def cancel_work_item(
    request: Request,
    work_item_id: str,
    reason: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Cancel a work item

    Args:
        work_item_id: Work item ID
        reason: Optional cancellation reason
        current_user: Authenticated user

    Returns:
        Updated work item
    """
    user_id = get_user_id(current_user)
    work_item = orchestrator.active_work_items.get(work_item_id)
    if not work_item:
        raise http_404(f"Work item not found or access denied: {work_item_id}", resource="work_item")

    work_item.status = WorkItemStatus.CANCELLED
    work_item.updated_at = datetime.now(UTC)
    work_item.completed_at = datetime.now(UTC)

    # Add to history
    transition = StageTransition(
        from_stage_id=work_item.current_stage_id,
        to_stage_id=None,
        transitioned_by=user_id,
        notes=f"Cancelled: {reason}" if reason else "Cancelled"
    )
    work_item.history.append(transition)

    logger.info(f"Work item {work_item_id} cancelled by {user_id}")

    # Persist cancellation
    try:
        if orchestrator.storage:
            orchestrator.storage.save_work_item(work_item, user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to persist work item cancellation: {e}")

    return work_item


__all__ = ["router"]
