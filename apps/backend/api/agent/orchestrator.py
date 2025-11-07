#!/usr/bin/env python3
"""
Agent Orchestrator API for ElohimOS
Integrates Aider + Continue + Codex for terminal-first AI coding
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pathlib import Path

# ElohimOS imports
try:
    from ..auth_middleware import get_current_user
    from ..rate_limiter import rate_limiter, get_client_ip
    from ..permission_engine import require_perm
    from ..audit_logger import get_audit_logger, AuditAction
except ImportError:
    from auth_middleware import get_current_user
    from rate_limiter import rate_limiter, get_client_ip
    from permission_engine import require_perm
    from audit_logger import get_audit_logger, AuditAction

# Agent components
from .patchbus import PatchBus, ChangeProposal
from .intent_classifier import IntentClassifier
from .planner_enhanced import EnhancedPlanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# ==================== Request/Response Models ====================

class RouteRequest(BaseModel):
    """Request to route user input"""
    input: str = Field(..., description="User's natural language input")
    cwd: Optional[str] = Field(None, description="Current working directory")
    repo_root: Optional[str] = Field(None, description="Repository root path")


class RouteResponse(BaseModel):
    """Response from routing"""
    intent: str = Field(..., description="Detected intent: shell, code_edit, question")
    confidence: float = Field(..., description="Confidence score 0-1")
    model_hint: Optional[str] = Field(None, description="Suggested model for task")
    next_action: str = Field(..., description="Suggested next step")


class PlanRequest(BaseModel):
    """Request to generate a plan"""
    input: str = Field(..., description="User requirement")
    context_bundle: Optional[Dict[str, Any]] = Field(None, description="Context from /agent/context")
    model: Optional[str] = Field(None, description="Model to use for planning")


class PlanStep(BaseModel):
    """Single plan step"""
    description: str
    risk_level: str  # low, medium, high
    estimated_files: int = 0


class PlanResponse(BaseModel):
    """Response from planning"""
    steps: List[PlanStep]
    risks: List[str]
    requires_confirmation: bool
    estimated_time_min: int
    model_used: str


class ContextRequest(BaseModel):
    """Request for context bundle"""
    session_id: Optional[str] = None
    cwd: Optional[str] = None
    repo_root: Optional[str] = None
    open_files: List[str] = Field(default_factory=list)


class ContextResponse(BaseModel):
    """Context bundle response"""
    file_tree_slice: List[str]
    recent_diffs: List[Dict[str, Any]]
    embeddings_hits: List[str]
    chat_snippets: List[str]
    active_models: List[str]


class ApplyRequest(BaseModel):
    """Request to apply a plan via Aider"""
    plan_id: Optional[str] = None
    input: str = Field(..., description="Requirement or task description")
    repo_root: Optional[str] = None
    model: Optional[str] = Field(None, description="Model for Aider")
    dry_run: bool = Field(False, description="Preview only, don't apply")


class FilePatch(BaseModel):
    """Single file patch"""
    path: str
    patch_text: str
    summary: str


class ApplyResponse(BaseModel):
    """Response from apply"""
    success: bool
    patches: List[FilePatch]
    summary: str
    patch_id: Optional[str] = None


# ==================== Endpoints ====================

@router.post("/route", response_model=RouteResponse)
async def route_input(
    request: Request,
    body: RouteRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Route user input to determine intent

    Rate limited: 60 requests/min per user
    Permission required: code.use
    """
    # Rate limit
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(
        f"agent:route:{current_user['user_id']}",
        max_requests=60,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many route requests")

    # Permission check
    require_perm(current_user['user_id'], 'code.use')

    try:
        # Use intent classifier
        classifier = IntentClassifier()
        intent_result = classifier.classify(body.input)

        # Map to our response format
        intent_type = intent_result.get('type', 'question')
        confidence = intent_result.get('confidence', 0.5)

        # Model hints based on intent
        model_hint = None
        if intent_type == 'code_edit':
            model_hint = 'qwen2.5-coder:32b'
        elif intent_type == 'question':
            model_hint = 'deepseek-r1:32b'

        # Next action suggestion
        next_action = "call /agent/plan" if intent_type == 'code_edit' else "answer directly"

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=current_user['user_id'],
                action=AuditAction.CODE_ASSIST,
                details={'intent': intent_type, 'input_preview': body.input[:100]}
            )

        return RouteResponse(
            intent=intent_type,
            confidence=confidence,
            model_hint=model_hint,
            next_action=next_action
        )

    except Exception as e:
        logger.error(f"Route failed: {e}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(
    request: Request,
    body: PlanRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate execution plan for a code task

    Rate limited: 30 requests/min per user
    Permission required: code.use
    """
    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:plan:{current_user['user_id']}",
        max_requests=30,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many plan requests")

    # Permission check
    require_perm(current_user['user_id'], 'code.use')

    try:
        # Use enhanced planner
        planner = EnhancedPlanner()

        # Generate plan
        plan_result = planner.plan(
            task_description=body.input,
            context=body.context_bundle or {}
        )

        # Map to our response format
        steps = []
        for step in plan_result.get('steps', []):
            steps.append(PlanStep(
                description=step.get('description', ''),
                risk_level=step.get('risk', 'low'),
                estimated_files=step.get('files', 0)
            ))

        risks = plan_result.get('risks', [])
        requires_confirmation = plan_result.get('requires_approval', False)

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=current_user['user_id'],
                action=AuditAction.CODE_ASSIST,
                details={
                    'action': 'plan_generated',
                    'steps': len(steps),
                    'risks': len(risks)
                }
            )

        return PlanResponse(
            steps=steps,
            risks=risks,
            requires_confirmation=requires_confirmation,
            estimated_time_min=len(steps) * 2,  # Rough estimate
            model_used=body.model or 'deepseek-r1:32b'
        )

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


@router.post("/context", response_model=ContextResponse)
async def get_context_bundle(
    request: Request,
    body: ContextRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get contextual information bundle

    Rate limited: 60 requests/min per user
    Permission required: code.use
    """
    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:context:{current_user['user_id']}",
        max_requests=60,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many context requests")

    # Permission check
    require_perm(current_user['user_id'], 'code.use')

    try:
        # Build context bundle
        # TODO: Integrate with Continue's context providers

        file_tree_slice = []
        if body.repo_root:
            repo_path = Path(body.repo_root)
            if repo_path.exists():
                # Get top-level structure
                file_tree_slice = [
                    str(p.relative_to(repo_path))
                    for p in repo_path.rglob('*')
                    if p.is_file() and not any(part.startswith('.') for part in p.parts)
                ][:50]  # Limit to 50 files

        # TODO: Get recent diffs from git
        recent_diffs = []

        # TODO: Get embeddings hits
        embeddings_hits = []

        # TODO: Get recent chat snippets
        chat_snippets = []

        # Get active models
        active_models = ['qwen2.5-coder:32b', 'deepseek-r1:32b', 'codestral:22b']

        return ContextResponse(
            file_tree_slice=file_tree_slice,
            recent_diffs=recent_diffs,
            embeddings_hits=embeddings_hits,
            chat_snippets=chat_snippets,
            active_models=active_models
        )

    except Exception as e:
        logger.error(f"Context building failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context failed: {str(e)}")


@router.post("/apply", response_model=ApplyResponse)
async def apply_plan(
    request: Request,
    body: ApplyRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Apply a plan via Aider and return patches

    Rate limited: 10 requests/min per user (heavyweight operation)
    Permissions required: code.use + code.edit
    """
    # Rate limit (more restrictive for apply)
    if not rate_limiter.check_rate_limit(
        f"agent:apply:{current_user['user_id']}",
        max_requests=10,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many apply requests")

    # Permission check (elevated)
    require_perm(current_user['user_id'], 'code.use')
    require_perm(current_user['user_id'], 'code.edit')

    try:
        # Import aider engine and patchbus
        from .engines.aider_engine import AiderEngine
        from pathlib import Path

        # Get venv path (use current venv or default)
        venv_path = Path(os.getcwd()) / "venv"
        if not venv_path.exists():
            venv_path = Path.home() / ".virtualenvs" / "elohimos"

        # Initialize Aider with correct signature
        aider = AiderEngine(
            model=body.model or 'qwen2.5-coder:32b',
            venv_path=venv_path
        )

        # Get files from context or empty list
        files = []
        context_snippets = []

        # Call propose() method (returns ChangeProposal)
        proposal = aider.propose(
            description=body.input,
            files=files,
            context_snippets=context_snippets
        )

        # If dry run, just preview the diff
        if body.dry_run:
            patches = [FilePatch(
                path='<unified>',
                patch_text=proposal.diff,
                summary=proposal.description
            )]
            patch_id = None
        else:
            # Apply via PatchBus
            apply_result = PatchBus.apply(proposal)

            if not apply_result.get('success'):
                raise HTTPException(
                    status_code=500,
                    detail=f"Patch application failed: {apply_result.get('message')}"
                )

            patch_id = apply_result.get('patch_id')

            # Convert to patches for response
            patches = [FilePatch(
                path=f,
                patch_text=proposal.diff,
                summary=f"Applied changes to {f}"
            ) for f in apply_result.get('files', [])]

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=current_user['user_id'],
                action=AuditAction.CODE_EDIT,
                details={
                    'patches': len(patches),
                    'dry_run': body.dry_run,
                    'patch_id': patch_id,
                    'files': [p.path for p in patches]
                }
            )

        return ApplyResponse(
            success=True,
            patches=patches,
            summary=f"Generated {len(patches)} patch(es)" + (" (dry run)" if body.dry_run else ""),
            patch_id=patch_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Apply failed: {e}")
        raise HTTPException(status_code=500, detail=f"Apply failed: {str(e)}")
