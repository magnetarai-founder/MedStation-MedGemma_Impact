"""
Workflow Service Layer
REST API and business logic for workflow operations
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Phase 2: Import permission decorators
# Phase 3: Import team-aware decorators and membership helpers
try:
    from .permission_engine import require_perm, require_perm_team
    from .auth_middleware import get_current_user
    from .team_service import is_team_member
    from .rate_limiter import rate_limiter, get_client_ip
except ImportError:
    from permission_engine import require_perm, require_perm_team
    from auth_middleware import get_current_user
    from team_service import is_team_member
    from rate_limiter import rate_limiter, get_client_ip

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
        WorkflowType,
        CreateWorkItemRequest,
        ClaimWorkItemRequest,
        CompleteStageRequest,
        CreateWorkflowRequest,
    )
    from .workflow_orchestrator import WorkflowOrchestrator
    from .workflow_storage import WorkflowStorage
    from .services.workflow_analytics import WorkflowAnalytics
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
        WorkflowType,
        CreateWorkItemRequest,
        ClaimWorkItemRequest,
        CompleteStageRequest,
        CreateWorkflowRequest,
    )
    from workflow_orchestrator import WorkflowOrchestrator
    from workflow_storage import WorkflowStorage
    from services.workflow_analytics import WorkflowAnalytics

try:
    from .workflow_p2p_sync import init_workflow_sync, get_workflow_sync
except ImportError:
    from workflow_p2p_sync import init_workflow_sync, get_workflow_sync

logger = logging.getLogger(__name__)

from fastapi import Depends
from auth_middleware import get_current_user
from utils import sanitize_for_log

router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    dependencies=[Depends(get_current_user)]  # Require auth for all workflow endpoints
)

# Initialize storage and orchestrator
storage = WorkflowStorage()
orchestrator = WorkflowOrchestrator(storage=storage)
analytics = WorkflowAnalytics(db_path=storage.db_path)

# P2P sync (will be initialized when P2P service starts)
workflow_sync = None

def setup_p2p_sync(peer_id: str):
    """Setup P2P sync when P2P service is ready"""
    global workflow_sync
    if not workflow_sync:
        workflow_sync = init_workflow_sync(orchestrator, storage, peer_id)
        logger.info(f"🔄 Workflow P2P sync initialized for peer {peer_id}")


# T3-1: Helper to get user's team_id for visibility checks
def get_user_team_id(user_id: str) -> Optional[str]:
    """
    Get user's primary team ID for visibility checks.

    Returns first team if user has multiple teams.
    Most users are in one team, so this is a reasonable default.
    """
    try:
        from api.services.team.members import get_user_teams
    except ImportError:
        from services.team.members import get_user_teams

    user_teams = get_user_teams(user_id)
    return user_teams[0]['id'] if user_teams else None


# ============================================
# WORKFLOW CRUD
# ============================================

@router.post("/workflows", response_model=Workflow)
@require_perm_team("workflows.create", level="write")
async def create_workflow(
    request: Request,
    body: CreateWorkflowRequest,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new workflow definition (Phase 3: team-aware)

    Args:
        request: Workflow creation request
        team_id: Optional team ID (if creating team workflow)
        current_user: Authenticated user

    Returns:
        Created workflow

    Phase 3: If team_id is provided, creates a team workflow.
    User must be a team member to create team workflows.
    """
    # Rate limit: 5 workflow creations per minute per user
    user_id = current_user.get("user_id", "unknown")
    if not rate_limiter.check_rate_limit(f"create_workflow:{user_id}", max_requests=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 5 workflow creations per minute.")
    try:
        user_id = current_user["user_id"]

        # Phase 3: Check team membership if creating team workflow
        if team_id:
            if not is_team_member(team_id, user_id):
                raise HTTPException(status_code=403, detail="Not a member of this team")

        # Build workflow from request
        workflow = Workflow(
            name=body.name,
            description=body.description,
            icon=body.icon,
            category=body.category,
            workflow_type=body.workflow_type or WorkflowType.TEAM_WORKFLOW,
            stages=[Stage(**stage) if isinstance(stage, dict) else Stage(**stage.model_dump()) for stage in body.stages],
            triggers=body.triggers,
            created_by=user_id,
        )

        # Register with orchestrator (Phase 3.5: now team-aware)
        orchestrator.register_workflow(workflow, user_id=user_id, team_id=team_id)

        team_context = f"team={team_id}" if team_id else "personal"
        logger.info(f"✨ Created workflow: {workflow.name} (ID: {workflow.id}) [{team_context}]")

        return workflow

    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows", response_model=List[Workflow])
@require_perm_team("workflows.view", level="read")
async def list_workflows(
    category: Optional[str] = None,
    enabled_only: bool = True,
    team_id: Optional[str] = None,
    workflow_type: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all workflows visible to user (T3-1: visibility-aware)

    Returns workflows based on visibility:
    - Personal workflows owned by the user
    - Team workflows for all teams the user is a member of
    - Global/system workflows

    Args:
        category: Filter by category
        enabled_only: Only return enabled workflows
        team_id: Optional specific team ID to filter (backward compat)
        workflow_type: Filter by workflow type ('local' or 'team')
        current_user: Authenticated user

    Returns:
        List of workflows visible to this user
    """
    user_id = current_user["user_id"]

    # T3-1: Get user's team for visibility (use helper)
    if not team_id:
        team_id = get_user_team_id(user_id)

    # Check team membership if team_id is specified
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Use orchestrator method with visibility-aware filtering
    workflows = orchestrator.list_workflows(
        user_id=user_id,
        category=category,
        enabled_only=enabled_only,
        team_id=team_id,
        workflow_type=workflow_type
    )

    return workflows


@router.get("/workflows/{workflow_id}", response_model=Workflow)
@require_perm("workflows.view", level="read")
async def get_workflow(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get workflow by ID with visibility check (T3-1)

    Args:
        workflow_id: Workflow ID
        current_user: Authenticated user

    Returns:
        Workflow definition

    Raises:
        HTTPException: If workflow not found or access denied
    """
    user_id = current_user["user_id"]
    team_id = get_user_team_id(user_id)  # T3-1: Get user's team for visibility

    workflow = orchestrator.get_workflow(workflow_id, user_id=user_id, team_id=team_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found or access denied: {workflow_id}")

    return workflow


@router.delete("/workflows/{workflow_id}")
@require_perm("workflows.delete", level="write")
async def delete_workflow(
    request: Request,
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete workflow (soft delete - sets enabled=False)

    Args:
        workflow_id: Workflow ID
        current_user: Authenticated user

    Returns:
        Success status
    """
    user_id = current_user["user_id"]
    team_id = get_user_team_id(user_id)  # T3-1

    workflow = orchestrator.get_workflow(workflow_id, user_id=user_id, team_id=team_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found or access denied: {workflow_id}")

    workflow.enabled = False
    workflow.updated_at = datetime.utcnow()

    logger.info(f"🗑️  Deleted workflow: {workflow.name}")

    # Persist change if storage is available
    try:
        if orchestrator.storage:
            orchestrator.storage.save_workflow(workflow, user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to persist workflow deletion: {e}")

    return {"status": "deleted", "workflow_id": workflow_id}


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
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 work item creations per minute.")

    try:
        user_id = current_user["user_id"]

        work_item = orchestrator.create_work_item(
            workflow_id=body.workflow_id,
            data=body.data,
            created_by=user_id,
            priority=body.priority or WorkItemPriority.NORMAL,
            tags=body.tags,
            user_id=user_id,
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
    user_id = current_user["user_id"]
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
    user_id = current_user["user_id"]
    # Use storage to ensure user isolation
    work_item = orchestrator.storage.get_work_item(work_item_id, user_id) if orchestrator.storage else None
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item not found or access denied: {work_item_id}")

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
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 claims per minute.")

    try:
        user_id = current_user["user_id"]
        # Correct call signature (positional only)
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
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 starts per minute.")

    try:
        user_id = current_user["user_id"]
        # Correct call signature (positional only)
        work_item = orchestrator.start_work(work_item_id, user_id)
        logger.info(f"▶️  Work item {work_item_id} started by {user_id}")
        return work_item

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        user_id = current_user["user_id"]

        work_item = orchestrator.complete_stage(
            work_item_id=body.work_item_id,
            user_id=user_id,
            stage_data=body.data,
            notes=body.notes,
        )

        if work_item.status == WorkItemStatus.COMPLETED:
            safe_work_item_id = sanitize_for_log(body.work_item_id)
            logger.info(f"🎉 Work item {safe_work_item_id} completed")
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
    user_id = current_user["user_id"]
    work_item = orchestrator.active_work_items.get(work_item_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item not found or access denied: {work_item_id}")

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

    # Persist cancellation
    try:
        if orchestrator.storage:
            orchestrator.storage.save_work_item(work_item, user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to persist work item cancellation: {e}")

    return work_item


# ============================================
# QUEUE OPERATIONS
# ============================================

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

    logger.info(f"📋 Queue for {role_name}: {len(queue)} items")

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

    logger.info(f"👤 My work for {user_id}: {len(my_work)} items")

    return my_work


# ============================================
# SLA & MONITORING
# ============================================

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

    logger.info(f"⏰ Overdue items: {len(overdue)}")

    return overdue


@router.get("/statistics/{workflow_id}")
async def get_workflow_statistics(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
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


# ============================================
# STARRING FUNCTIONALITY
# ============================================

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


# ============================================
# PHASE D: TEMPLATES
# ============================================

@router.get("/templates", response_model=List[Workflow])
@require_perm("workflows.view", level="read")
async def list_workflow_templates(
    category: Optional[str] = None,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List workflow templates (Phase D).

    Templates are workflows with is_template=True that can be instantiated
    into new workflows.

    Args:
        category: Optional category filter
        team_id: Optional team ID for team templates
        current_user: Authenticated user

    Returns:
        List of template workflows
    """
    user_id = current_user["user_id"]

    # T3-1: Get user's team for visibility
    if not team_id:
        team_id = get_user_team_id(user_id)

    # Check team membership if team_id is specified
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # T3-1: List all visible workflows, then filter for templates
    all_workflows = storage.list_workflows(
        user_id=user_id,
        category=category,
        enabled_only=True,
        team_id=team_id,
    )

    templates = [w for w in all_workflows if w.is_template]

    logger.info(f"📋 Listed {len(templates)} template(s)")
    return templates


@router.get("/templates/{template_id}", response_model=Workflow)
@require_perm("workflows.view", level="read")
async def get_workflow_template(
    template_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific workflow template (Phase D).

    Args:
        template_id: Template workflow ID
        current_user: Authenticated user

    Returns:
        Template workflow

    Raises:
        HTTPException: If not found or not a template
    """
    user_id = current_user["user_id"]
    team_id = get_user_team_id(user_id)  # T3-1

    workflow = storage.get_workflow(template_id, user_id=user_id, team_id=team_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    if not workflow.is_template:
        raise HTTPException(status_code=400, detail="Workflow is not a template")

    return workflow


class InstantiateTemplateRequest(BaseModel):
    """Request to instantiate a template"""
    name: Optional[str] = None  # Override template name
    description: Optional[str] = None  # Override template description
    team_id: Optional[str] = None  # Optional team ID for team workflow


@router.post("/templates/{template_id}/instantiate", response_model=Workflow)
@require_perm("workflows.create", level="write")
async def instantiate_template(
    request: Request,
    template_id: str,
    body: InstantiateTemplateRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new workflow from a template (Phase D).

    Args:
        template_id: Template workflow ID
        body: Instantiation request
        current_user: Authenticated user

    Returns:
        New workflow instance

    Raises:
        HTTPException: If template not found or instantiation fails
    """
    user_id = current_user["user_id"]
    user_team_id = get_user_team_id(user_id)  # T3-1

    # T3-1: Get template with visibility check
    template = storage.get_workflow(template_id, user_id=user_id, team_id=user_team_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    if not template.is_template:
        raise HTTPException(status_code=400, detail="Workflow is not a template")

    # Check team membership if creating team workflow
    if body.team_id:
        if not is_team_member(body.team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Create new workflow from template
    new_workflow = Workflow(
        name=body.name or f"{template.name} (Copy)",
        description=body.description or template.description,
        icon=template.icon,
        category=template.category,
        workflow_type=template.workflow_type,
        stages=template.stages.copy(),  # Deep copy stages
        triggers=template.triggers.copy(),  # Deep copy triggers
        enabled=True,
        allow_manual_creation=template.allow_manual_creation,
        require_approval_to_start=template.require_approval_to_start,
        is_template=False,  # Instance is not a template
        created_by=user_id,
        tags=template.tags.copy() if template.tags else [],
    )

    # Register with orchestrator
    orchestrator.register_workflow(new_workflow, user_id=user_id, team_id=body.team_id)

    logger.info(f"✨ Instantiated workflow from template {template_id}: {new_workflow.name} (ID: {new_workflow.id})")

    return new_workflow


# ============================================
# PHASE D: ANALYTICS
# ============================================

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


# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint with storage path info

    Returns:
        - status: Service health status
        - active_workflows: Count of active workflows in memory
        - active_work_items: Count of active work items in memory
        - storage_path: Path to workflow database (for ops diagnostics)
        - db_readable: Whether database is accessible
    """
    # Check if database is readable
    db_readable = False
    try:
        db_readable = storage.db_path.exists() and storage.db_path.is_file()
    except Exception:
        pass

    return {
        "status": "healthy",
        "active_workflows": len(orchestrator.workflows),
        "active_work_items": len(orchestrator.active_work_items),
        "storage_path": str(storage.db_path),
        "db_readable": db_readable,
    }
