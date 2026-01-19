"""
Workflow CRUD Endpoints

Create, list, get, and delete workflow definitions.
"""

from fastapi import APIRouter, HTTPException, Request, Depends

from api.errors import http_400, http_403, http_404, http_429
from typing import List, Dict, Optional
from datetime import datetime, UTC
import logging

from ..dependencies import (
    orchestrator, storage,
    require_perm, require_perm_team,
    get_current_user, is_team_member,
    rate_limiter, get_user_id, get_user_team_id,
    Workflow, WorkflowType, Stage,
    CreateWorkflowRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


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
        raise http_429("Max 5 workflow creations per minute")
    try:
        user_id = get_user_id(current_user)

        # Phase 3: Check team membership if creating team workflow
        if team_id:
            if not is_team_member(team_id, user_id):
                raise http_403("Not a member of this team")

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
        logger.info(f"Created workflow: {workflow.name} (ID: {workflow.id}) [{team_context}]")

        return workflow

    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}")
        raise http_400(str(e))


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
    user_id = get_user_id(current_user)

    # T3-1: Get user's team for visibility (use helper)
    if not team_id:
        team_id = get_user_team_id(user_id)

    # Check team membership if team_id is specified
    if team_id:
        if not is_team_member(team_id, user_id):
            raise http_403("Not a member of this team")

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
    user_id = get_user_id(current_user)
    team_id = get_user_team_id(user_id)  # T3-1: Get user's team for visibility

    workflow = orchestrator.get_workflow(workflow_id, user_id=user_id, team_id=team_id)
    if not workflow:
        raise http_404(f"Workflow not found or access denied: {workflow_id}", resource="workflow")

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
    user_id = get_user_id(current_user)
    team_id = get_user_team_id(user_id)  # T3-1

    workflow = orchestrator.get_workflow(workflow_id, user_id=user_id, team_id=team_id)
    if not workflow:
        raise http_404(f"Workflow not found or access denied: {workflow_id}", resource="workflow")

    workflow.enabled = False
    workflow.updated_at = datetime.now(UTC)

    logger.info(f"Deleted workflow: {workflow.name}")

    # Persist change if storage is available
    try:
        if orchestrator.storage:
            orchestrator.storage.save_workflow(workflow, user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to persist workflow deletion: {e}")

    return {"status": "deleted", "workflow_id": workflow_id}


__all__ = ["router"]
