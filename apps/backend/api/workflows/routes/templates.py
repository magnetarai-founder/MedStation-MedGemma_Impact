"""
Workflow Templates Endpoints

List, get, and instantiate workflow templates.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

from ..dependencies import (
    orchestrator, storage,
    require_perm,
    get_current_user, is_team_member,
    get_user_team_id,
    Workflow,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class InstantiateTemplateRequest(BaseModel):
    """Request to instantiate a template"""
    name: Optional[str] = None  # Override template name
    description: Optional[str] = None  # Override template description
    team_id: Optional[str] = None  # Optional team ID for team workflow


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

    logger.info(f"Listed {len(templates)} template(s)")
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

    logger.info(f"Instantiated workflow from template {template_id}: {new_workflow.name} (ID: {new_workflow.id})")

    return new_workflow


__all__ = ["router"]
