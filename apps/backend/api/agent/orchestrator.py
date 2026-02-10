#!/usr/bin/env python3
"""
Agent Orchestrator API for MedStation - Thin Router

BACKWARDS COMPATIBILITY LAYER
This router delegates all business logic to the orchestration/ package.

Original monolithic implementation has been modularized into api/agent/orchestration/ package:
- orchestration/models.py - Pydantic request/response models
- orchestration/config.py - Agent configuration management
- orchestration/capabilities.py - Engine capability detection
- orchestration/model_settings.py - Model configuration and validation
- orchestration/routing.py - Intent classification
- orchestration/planning.py - Plan generation
- orchestration/context_bundle.py - Context bundle construction
- orchestration/apply.py - Plan application via Aider/Continue/Codex

Refactored during Phase 6.3d modularization.

All existing imports and /api/v1/agent/* endpoints continue to work unchanged.
"""

import logging
import time
from fastapi import APIRouter, Depends, Request
from typing import Dict, Any

from api.errors import http_400, http_403, http_404, http_429, http_500

# MedStation imports
from ..auth_middleware import get_current_user
from ..rate_limiter import rate_limiter, get_client_ip
from ..permission_engine import require_perm
from ..audit_logger import get_audit_logger, AuditAction
from ..config_paths import get_config_paths
from ..metrics import get_metrics
from ..utils import get_user_id, get_username

PATHS = get_config_paths()
metrics = get_metrics()

# Import all orchestration components
from .orchestration import (
    # Models
    RouteRequest, RouteResponse,
    PlanRequest, PlanResponse,
    ContextRequest, ContextResponse,
    ApplyRequest, ApplyResponse,
    CapabilitiesResponse,
    AgentSession, AgentSessionCreateRequest,  # Phase C
    # Logic functions
    get_capabilities_logic,
    get_agent_config,
    reload_config,
    get_models_overview,
    update_model_settings_logic,
    validate_models_logic,
    auto_fix_models_logic,
    route_input_logic,
    generate_plan_logic,
    build_context_bundle,
    apply_plan_logic,
)
# Phase C: Session management
from .orchestration.sessions import (
    create_agent_session,
    get_agent_session,
    list_agent_sessions_for_user,
    close_session,
    touch_session,
    update_session_plan,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# ==================== Endpoints ====================

@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(current_user: Dict = Depends(get_current_user)):
    """
    Get agent system capabilities and engine availability

    Returns information about which engines are available and
    provides helpful remediation messages for missing dependencies.

    No special permissions required - just authentication.
    """
    return get_capabilities_logic()


@router.get("/models")
async def get_models(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get model configuration and orchestrator status

    Returns:
    - orchestrator: {enabled: bool, model: str}
    - user_preferences: Models selected per task (only used if orchestrator disabled)
    - recommended_models: Tested models per task type (shown as "Tested & Recommended")
    - strict_models: Enforced models (e.g., data_engine locked to phi3.5)
    - available_models: All Ollama models currently available on system

    UI Behavior:
    - If orchestrator.enabled = true: Hide task-specific dropdowns, show toggle
    - If orchestrator.enabled = false: Show task-specific dropdowns with user preferences
    - Data engine is always locked to strict_models.data_engine
    """
    cfg = get_agent_config()
    return get_models_overview(cfg)


@router.post("/models/update")
@require_perm("settings.update")
async def update_model_settings(
    request: Request,
    body: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Update model settings and orchestrator configuration

    Accepts:
    - orchestrator.enabled: bool (toggle intelligent routing)
    - user_preferences: dict (task-specific model selections)

    Note: Only Founder/Super Admins can update these settings
    """
    try:
        result = update_model_settings_logic(body)
        logger.info(f"Model settings updated by {get_username(current_user)}")
        return result
    except FileNotFoundError as e:
        raise http_404(str(e))
    except Exception as e:
        logger.error(f"Failed to update model settings: {e}")
        raise http_500(f"Failed to update settings: {str(e)}")


@router.post("/route", response_model=RouteResponse)
@require_perm("code.use")
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
    start_time = time.perf_counter()
    user_id = current_user.get('user_id')

    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:route:{user_id}",
        max_requests=60,
        window_seconds=60
    ):
        raise http_429("Too many route requests")

    try:
        # T3-1: Validate session ownership if provided
        if body.session_id:
            session = get_agent_session(body.session_id)
            if not session or session.user_id != user_id:
                raise http_404("Session not found", resource="session")

        # Pass user_id for learning-aware routing
        resp = route_input_logic(body.input, user_id=user_id)

        # Phase C: Touch session if provided
        if body.session_id:
            touch_session(body.session_id)

        # Audit log (enhanced)
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.AGENT_ROUTE_COMPLETED,
                resource="agent_session" if body.session_id else "agent",
                resource_id=body.session_id,
                details={
                    'intent': resp.intent,
                    'model_hint': resp.model_hint,
                    'learning_used': resp.learning_used if hasattr(resp, 'learning_used') else None
                }
            )

        # Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.record("agent.route.calls", duration_ms, error=False)

        return resp
    except Exception as e:
        logger.error(f"Routing failed: {e}", exc_info=True)
        metrics.record("agent.route.calls", (time.perf_counter() - start_time) * 1000, error=True)
        raise http_500("Failed to route input")


@router.post("/plan", response_model=PlanResponse)
@require_perm("code.use")
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
    start_time = time.perf_counter()
    user_id = get_user_id(current_user)

    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:plan:{user_id}",
        max_requests=30,
        window_seconds=60
    ):
        raise http_429("Too many plan requests")

    try:
        # T3-1: Validate session ownership if provided
        if body.session_id:
            session = get_agent_session(body.session_id)
            if not session or session.user_id != user_id:
                raise http_404("Session not found", resource="session")

        resp = generate_plan_logic(body.input, body.context_bundle)

        # Phase C: Update session plan if provided
        if body.session_id:
            update_session_plan(body.session_id, resp.model_dump())

        # Audit log (enhanced)
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.AGENT_PLAN_GENERATED,
                resource="agent_session" if body.session_id else "agent",
                resource_id=body.session_id,
                details={
                    'num_steps': len(resp.steps),
                    'estimated_time_min': resp.estimated_time_min,
                    'risks_count': len(resp.risks)
                }
            )

        # Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.record("agent.plan.calls", duration_ms, error=False)

        return resp
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Planning failed: {e}", exc_info=True)
        metrics.record("agent.plan.calls", (time.perf_counter() - start_time) * 1000, error=True)
        raise http_500("Failed to generate plan. Please try again.")


@router.post("/context", response_model=ContextResponse)
@require_perm("code.use")
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
    start_time = time.perf_counter()
    user_id = get_user_id(current_user)

    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:context:{user_id}",
        max_requests=60,
        window_seconds=60
    ):
        raise http_429("Too many context requests")

    try:
        # T3-1: Validate session ownership if provided
        if body.session_id:
            session = get_agent_session(body.session_id)
            if not session or session.user_id != user_id:
                raise http_404("Session not found", resource="session")

        resp = build_context_bundle(body, current_user, PATHS)

        # Phase C: Touch session if provided
        if body.session_id:
            touch_session(body.session_id)

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            num_files = len(resp.relevant_files) if resp.relevant_files else 0
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.AGENT_CONTEXT_BUILT,
                resource="agent_session" if body.session_id else "agent",
                resource_id=body.session_id,
                details={
                    'repo_root': body.repo_root,
                    'num_files_in_bundle': num_files,
                    'has_git_history': hasattr(resp, 'git_info') and resp.git_info is not None
                }
            )

        # Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.record("agent.context.calls", duration_ms, error=False)

        return resp
    except PermissionError as e:
        metrics.record("agent.context.calls", (time.perf_counter() - start_time) * 1000, error=True)
        raise http_403(str(e))
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Context building failed: {e}", exc_info=True)
        metrics.record("agent.context.calls", (time.perf_counter() - start_time) * 1000, error=True)
        raise http_500("Failed to build context. Please check repository path.")


@router.post("/apply", response_model=ApplyResponse)
@require_perm("code.use")
@require_perm("code.edit")
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
    start_time = time.perf_counter()
    user_id = get_user_id(current_user)

    # Rate limit (more restrictive for apply)
    if not rate_limiter.check_rate_limit(
        f"agent:apply:{user_id}",
        max_requests=10,
        window_seconds=60
    ):
        raise http_429("Too many apply requests")

    try:
        # T3-1: Validate session ownership if provided
        if body.session_id:
            session = get_agent_session(body.session_id)
            if not session or session.user_id != user_id:
                raise http_404("Session not found", resource="session")

        patches, patch_id, engine_used = apply_plan_logic(body, current_user)

        # Phase C: Touch session if provided
        if body.session_id:
            touch_session(body.session_id)

        # Audit log (enhanced)
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.AGENT_APPLY_SUCCESS,
                resource="agent_session" if body.session_id else "agent",
                resource_id=body.session_id,
                details={
                    'repo_root': body.repo_root,
                    'files_changed_count': len(patches),
                    'engine_used': engine_used,
                    'model_used': body.model if hasattr(body, 'model') else None,
                    'patch_id': patch_id,
                    'dry_run': body.dry_run
                }
            )

        # Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.record("agent.apply.calls", duration_ms, error=False)

        return ApplyResponse(
            success=True,
            patches=patches,
            summary=f"Generated {len(patches)} patch(es) via {engine_used}" + (" (dry run)" if body.dry_run else ""),
            patch_id=patch_id
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Apply failed: {e}", exc_info=True)

        # Audit log failure
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.AGENT_APPLY_FAILURE,
                resource="agent_session" if body.session_id else "agent",
                resource_id=body.session_id,
                details={
                    'repo_root': body.repo_root,
                    'error_type': type(e).__name__,
                    'message': str(e)[:200]
                }
            )

        # Metrics
        metrics.record("agent.apply.calls", (time.perf_counter() - start_time) * 1000, error=True)
        metrics.record("agent.apply.failures", 0, error=True)

        raise http_500("Failed to apply changes. Please check logs for details.")


@router.get("/models/validate")
async def validate_models(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Validate model configuration and provide setup guidance

    Returns validation status, errors, warnings, and suggested fixes
    """
    cfg = get_agent_config()
    return validate_models_logic(cfg)


@router.post("/models/auto-fix")
@require_perm("settings.update")
async def auto_fix_models(
    request: Request,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Automatically fix model configuration using intelligent defaults

    This will:
    1. Auto-select compatible models for each task
    2. Update agent.config.yaml with working models
    3. Validate the fixes
    """
    try:
        result = auto_fix_models_logic(current_user)
        return result
    except ValueError as e:
        raise http_400(str(e))
    except ImportError as e:
        raise http_500(str(e))
    except Exception as e:
        logger.error(f"Auto-fix failed: {e}", exc_info=True)
        raise http_500("Failed to auto-fix models")


# ==================== Agent Sessions (Phase C) ====================

@router.post("/sessions", response_model=AgentSession)
@require_perm("code.use")
async def create_agent_session_endpoint(
    request: Request,
    body: AgentSessionCreateRequest,
    current_user: Dict = Depends(get_current_user),
):
    """
    Create a new agent workspace session (Phase C).

    Sessions provide stateful context for agent operations:
    - Tie together user, repo_root, and ongoing plans
    - Track activity and workspace state
    - Enable session-aware agent calls

    Args:
        body: Session creation request with repo_root and optional work_item

    Returns:
        Created AgentSession with unique session ID
    """
    user_id = get_user_id(current_user)

    try:
        session = create_agent_session(
            user_id=user_id,
            repo_root=body.repo_root,
            attached_work_item_id=body.attached_work_item_id,
        )
        logger.info(f"Created agent session {session.id} for user {user_id}")
        return session
    except Exception as e:
        logger.error(f"Failed to create agent session: {e}", exc_info=True)
        raise http_500(str(e))


@router.get("/sessions", response_model=list[AgentSession])
@require_perm("code.use")
async def list_agent_sessions_endpoint(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    active_only: bool = False,
):
    """
    List all agent sessions for current user.

    Args:
        active_only: If true, only return sessions with status='active'

    Returns:
        List of AgentSession objects, ordered by last_activity_at DESC
    """
    user_id = get_user_id(current_user)

    try:
        sessions = list_agent_sessions_for_user(user_id, active_only=active_only)
        return sessions
    except Exception as e:
        logger.error(f"Failed to list agent sessions: {e}", exc_info=True)
        raise http_500(str(e))


@router.get("/sessions/{session_id}", response_model=AgentSession)
@require_perm("code.use")
async def get_agent_session_endpoint(
    session_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a specific agent session by ID.

    Args:
        session_id: Session identifier

    Returns:
        AgentSession object

    Raises:
        404: If session not found or user doesn't have access
    """
    user_id = get_user_id(current_user)

    try:
        session = get_agent_session(session_id)

        if not session or session.user_id != user_id:
            raise http_404("Session not found", resource="session")

        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent session {session_id}: {e}", exc_info=True)
        raise http_500(str(e))


@router.post("/sessions/{session_id}/close", response_model=AgentSession)
@require_perm("code.use")
async def close_agent_session_endpoint(
    session_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user),
):
    """
    Close (archive) an agent session.

    Sets session status to 'archived' and updates last_activity_at.

    Args:
        session_id: Session identifier

    Returns:
        Updated AgentSession object

    Raises:
        404: If session not found or user doesn't have access
    """
    user_id = get_user_id(current_user)

    try:
        # Verify ownership
        session = get_agent_session(session_id)
        if not session or session.user_id != user_id:
            raise http_404("Session not found", resource="session")

        # Close the session
        close_session(session_id)

        # Reload updated session
        updated = get_agent_session(session_id)
        logger.info(f"Closed agent session {session_id}")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close agent session {session_id}: {e}", exc_info=True)
        raise http_500(str(e))
