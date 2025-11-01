"""
Workflow Service Layer
REST API and business logic for workflow operations
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from .workflow_models import (
        Workflow,
        WorkItem,
        Stage,
        WorkItemStatus,
        WorkItemPriority,
        StageType,
        AssignmentType,
        WorkflowTriggerType,
        CreateWorkItemRequest,
        ClaimWorkItemRequest,
        CompleteStageRequest,
        CreateWorkflowRequest,
    )
    from .workflow_orchestrator import WorkflowOrchestrator
    from .workflow_storage import WorkflowStorage
except ImportError:
    from workflow_models import (
        Workflow,
        WorkItem,
        Stage,
        WorkItemStatus,
        WorkItemPriority,
        StageType,
        AssignmentType,
        WorkflowTriggerType,
        CreateWorkItemRequest,
        ClaimWorkItemRequest,
        CompleteStageRequest,
        CreateWorkflowRequest,
    )
    from workflow_orchestrator import WorkflowOrchestrator
    from workflow_storage import WorkflowStorage

try:
    from .workflow_p2p_sync import init_workflow_sync, get_workflow_sync
except ImportError:
    from workflow_p2p_sync import init_workflow_sync, get_workflow_sync

logger = logging.getLogger(__name__)

from fastapi import Depends
from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    dependencies=[Depends(get_current_user)]  # Require auth for all workflow endpoints
)

# Initialize storage and orchestrator
storage = WorkflowStorage()
orchestrator = WorkflowOrchestrator(storage=storage)

# P2P sync (will be initialized when P2P service starts)
workflow_sync = None

def setup_p2p_sync(peer_id: str):
    """Setup P2P sync when P2P service is ready"""
    global workflow_sync
    if not workflow_sync:
        workflow_sync = init_workflow_sync(orchestrator, storage, peer_id)
        logger.info(f"🔄 Workflow P2P sync initialized for peer {peer_id}")


# ============================================
# WORKFLOW CRUD
# ============================================

@router.post("/workflows", response_model=Workflow)
async def create_workflow(request: Request, body: CreateWorkflowRequest, created_by: str = "system"):
    """
    Create a new workflow definition

    Args:
        request: Workflow creation request
        created_by: User ID creating the workflow

    Returns:
        Created workflow
    """
    try:
        # Build workflow from request
        workflow = Workflow(
            name=body.name,
            description=body.description,
            icon=body.icon,
            category=body.category,
            stages=[Stage(**stage) if isinstance(stage, dict) else Stage(**stage.model_dump()) for stage in body.stages],
            triggers=body.triggers,
            created_by=created_by,
        )

        # Register with orchestrator
        orchestrator.register_workflow(workflow)

        logger.info(f"✨ Created workflow: {workflow.name} (ID: {workflow.id})")

        return workflow

    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows", response_model=List[Workflow])
async def list_workflows(
    category: Optional[str] = None,
    enabled_only: bool = True
):
    """
    List all workflows

    Args:
        category: Filter by category
        enabled_only: Only return enabled workflows

    Returns:
        List of workflows
    """
    workflows = list(orchestrator.workflows.values())

    # Apply filters
    if category:
        workflows = [w for w in workflows if w.category == category]
    if enabled_only:
        workflows = [w for w in workflows if w.enabled]

    return workflows


@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """
    Get workflow by ID

    Args:
        workflow_id: Workflow ID

    Returns:
        Workflow definition

    Raises:
        HTTPException: If workflow not found
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    return workflow


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(request: Request, workflow_id: str):
    """
    Delete workflow (soft delete - sets enabled=False)

    Args:
        workflow_id: Workflow ID

    Returns:
        Success status
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    workflow.enabled = False
    workflow.updated_at = datetime.utcnow()

    logger.info(f"🗑️  Deleted workflow: {workflow.name}")

    return {"status": "deleted", "workflow_id": workflow_id}


# ============================================
# WORK ITEM CRUD
# ============================================

@router.post("/work-items", response_model=WorkItem)
async def create_work_item(request: Request, body: CreateWorkItemRequest, created_by: str = "system"):
    """
    Create a new work item

    Args:
        request: Work item creation request
        created_by: User ID creating the item

    Returns:
        Created work item

    Raises:
        HTTPException: If workflow not found
    """
    try:
        work_item = orchestrator.create_work_item(
            workflow_id=body.workflow_id,
            data=body.data,
            created_by=created_by,
            priority=body.priority or WorkItemPriority.NORMAL,
            tags=body.tags,
        )

        logger.info(f"✨ Created work item: {work_item.id}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_created(work_item))
            except Exception as e:
                logger.error(f"Failed to broadcast work item creation: {e}")

        return work_item

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create work item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work-items", response_model=List[WorkItem])
async def list_work_items(
    workflow_id: Optional[str] = None,
    status: Optional[WorkItemStatus] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[WorkItemPriority] = None,
    limit: int = Query(default=50, le=100),
):
    """
    List work items with filters

    Args:
        workflow_id: Filter by workflow
        status: Filter by status
        assigned_to: Filter by assigned user
        priority: Filter by priority
        limit: Max results

    Returns:
        List of work items
    """
    items = list(orchestrator.active_work_items.values())

    # Apply filters
    if workflow_id:
        items = [w for w in items if w.workflow_id == workflow_id]
    if status:
        items = [w for w in items if w.status == status]
    if assigned_to:
        items = [w for w in items if w.assigned_to == assigned_to]
    if priority:
        items = [w for w in items if w.priority == priority]

    # Sort by created_at desc
    items.sort(key=lambda w: w.created_at, reverse=True)

    return items[:limit]


@router.get("/work-items/{work_item_id}", response_model=WorkItem)
async def get_work_item(work_item_id: str):
    """
    Get work item by ID

    Args:
        work_item_id: Work item ID

    Returns:
        Work item

    Raises:
        HTTPException: If not found
    """
    work_item = orchestrator.active_work_items.get(work_item_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item not found: {work_item_id}")

    return work_item


# ============================================
# WORK ITEM ACTIONS
# ============================================

@router.post("/work-items/{work_item_id}/claim", response_model=WorkItem)
async def claim_work_item(request: Request, work_item_id: str, user_id: str):
    """
    Claim a work item from queue

    Args:
        work_item_id: Work item ID
        user_id: User claiming the item

    Returns:
        Updated work item

    Raises:
        HTTPException: If cannot be claimed
    """
    try:
        work_item = orchestrator.claim_work_item(work_item_id, user_id)
        logger.info(f"👤 Work item {work_item_id} claimed by {user_id}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_claimed(work_item, user_id))
            except Exception as e:
                logger.error(f"Failed to broadcast work item claim: {e}")

        return work_item

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-items/{work_item_id}/start", response_model=WorkItem)
async def start_work(request: Request, work_item_id: str, user_id: str):
    """
    Start work on claimed item

    Args:
        work_item_id: Work item ID
        user_id: User starting work

    Returns:
        Updated work item
    """
    try:
        work_item = orchestrator.start_work(work_item_id, user_id)
        logger.info(f"▶️  Work item {work_item_id} started by {user_id}")
        return work_item

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-items/{work_item_id}/complete", response_model=WorkItem)
async def complete_stage(request: Request, body: CompleteStageRequest, user_id: str = "system"):
    """
    Complete current stage and transition to next

    Args:
        request: Stage completion request
        user_id: User completing the stage

    Returns:
        Updated work item (possibly in new stage)

    Raises:
        HTTPException: If cannot complete
    """
    try:
        work_item = orchestrator.complete_stage(
            work_item_id=body.work_item_id,
            user_id=user_id,
            stage_data=body.data,
            notes=body.notes,
        )

        if work_item.status == WorkItemStatus.COMPLETED:
            logger.info(f"🎉 Work item {body.work_item_id} completed")
        else:
            logger.info(f"✅ Stage completed, transitioned to: {work_item.current_stage_name}")

        # Broadcast to P2P mesh
        if workflow_sync:
            try:
                import asyncio
                asyncio.create_task(workflow_sync.broadcast_work_item_completed(work_item))
            except Exception as e:
                logger.error(f"Failed to broadcast work item completion: {e}")

        return work_item

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to complete stage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/work-items/{work_item_id}/cancel", response_model=WorkItem)
async def cancel_work_item(request: Request, work_item_id: str, user_id: str, reason: Optional[str] = None):
    """
    Cancel a work item

    Args:
        work_item_id: Work item ID
        user_id: User cancelling
        reason: Optional cancellation reason

    Returns:
        Updated work item
    """
    work_item = orchestrator.active_work_items.get(work_item_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item not found: {work_item_id}")

    work_item.status = WorkItemStatus.CANCELLED
    work_item.updated_at = datetime.utcnow()
    work_item.completed_at = datetime.utcnow()

    # Add to history
    try:
        from .workflow_models import StageTransition
    except ImportError:
        from workflow_models import StageTransition
    transition = StageTransition(
        from_stage_id=work_item.current_stage_id,
        to_stage_id=None,
        transitioned_by=user_id,
        notes=f"Cancelled: {reason}" if reason else "Cancelled"
    )
    work_item.history.append(transition)

    logger.info(f"❌ Work item {work_item_id} cancelled by {user_id}")

    return work_item


# ============================================
# QUEUE OPERATIONS
# ============================================

@router.get("/queues/{workflow_id}/role/{role_name}", response_model=List[WorkItem])
async def get_queue_for_role(
    workflow_id: str,
    role_name: str,
    stage_id: Optional[str] = None,
):
    """
    Get work items in queue for a role

    Args:
        workflow_id: Workflow ID
        role_name: Role name
        stage_id: Optional stage filter

    Returns:
        List of work items available for this role
    """
    queue = orchestrator.get_queue_for_role(
        workflow_id=workflow_id,
        role_name=role_name,
        stage_id=stage_id,
    )

    logger.info(f"📋 Queue for {role_name}: {len(queue)} items")

    return queue


@router.get("/my-work/{user_id}", response_model=List[WorkItem])
async def get_my_active_work(user_id: str):
    """
    Get all work items assigned to user

    Args:
        user_id: User ID

    Returns:
        List of user's active work items
    """
    my_work = orchestrator.get_my_active_work(user_id)

    logger.info(f"👤 My work for {user_id}: {len(my_work)} items")

    return my_work


# ============================================
# SLA & MONITORING
# ============================================

@router.get("/overdue", response_model=List[WorkItem])
async def get_overdue_items():
    """
    Get all overdue work items

    Returns:
        List of overdue work items
    """
    overdue = orchestrator.check_overdue_items()

    logger.info(f"⏰ Overdue items: {len(overdue)}")

    return overdue


@router.get("/statistics/{workflow_id}")
async def get_workflow_statistics(workflow_id: str):
    """
    Get statistics for a workflow

    Args:
        workflow_id: Workflow ID

    Returns:
        Dictionary of statistics
    """
    stats = orchestrator.get_workflow_statistics(workflow_id)

    return stats


# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_workflows": len(orchestrator.workflows),
        "active_work_items": len(orchestrator.active_work_items),
    }
