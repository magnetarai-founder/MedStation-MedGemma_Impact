#!/usr/bin/env python3
"""
Agent Orchestrator API for ElohimOS - Thin Router

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
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any

# ElohimOS imports
try:
    from ..auth_middleware import get_current_user
    from ..rate_limiter import rate_limiter, get_client_ip
    from ..permission_engine import require_perm
    from ..audit_logger import get_audit_logger, AuditAction
    from ..config_paths import get_config_paths
except ImportError:
    from auth_middleware import get_current_user
    from rate_limiter import rate_limiter, get_client_ip
    from permission_engine import require_perm
    from audit_logger import get_audit_logger, AuditAction
    from config_paths import get_config_paths

PATHS = get_config_paths()

# Import all orchestration components
try:
    from .orchestration import (
        # Models
        RouteRequest, RouteResponse,
        PlanRequest, PlanResponse,
        ContextRequest, ContextResponse,
        ApplyRequest, ApplyResponse,
        CapabilitiesResponse,
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
except ImportError:
    from orchestration import (
        # Models
        RouteRequest, RouteResponse,
        PlanRequest, PlanResponse,
        ContextRequest, ContextResponse,
        ApplyRequest, ApplyResponse,
        CapabilitiesResponse,
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
async def get_models(current_user: Dict = Depends(get_current_user)):
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
        logger.info(f"Model settings updated by {current_user['username']}")
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Failed to update model settings: {e}")
        raise HTTPException(500, f"Failed to update settings: {str(e)}")


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
    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:route:{current_user['user_id']}",
        max_requests=60,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many route requests")

    try:
        # Pass user_id for learning-aware routing
        user_id = current_user.get('user_id')
        resp = route_input_logic(body.input, user_id=user_id)

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.CODE_ASSIST,
                details={'intent': resp.intent, 'input_preview': body.input[:100]}
            )

        return resp
    except Exception as e:
        logger.error(f"Routing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to route input")


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
    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:plan:{current_user['user_id']}",
        max_requests=30,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many plan requests")

    try:
        resp = generate_plan_logic(body.input, body.context_bundle)

        # Audit log
        audit_logger = get_audit_logger()
        if audit_logger:
            audit_logger.log(
                user_id=current_user['user_id'],
                action=AuditAction.CODE_ASSIST,
                details={
                    'action': 'plan_generated',
                    'steps': len(resp.steps),
                    'risks': len(resp.risks)
                }
            )

        return resp
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Planning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate plan. Please try again.")


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
    # Rate limit
    if not rate_limiter.check_rate_limit(
        f"agent:context:{current_user['user_id']}",
        max_requests=60,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many context requests")

    try:
        resp = build_context_bundle(body, current_user, PATHS)
        return resp
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Context building failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to build context. Please check repository path.")


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
    # Rate limit (more restrictive for apply)
    if not rate_limiter.check_rate_limit(
        f"agent:apply:{current_user['user_id']}",
        max_requests=10,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many apply requests")

    try:
        patches, patch_id, engine_used = apply_plan_logic(body, current_user)

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
            summary=f"Generated {len(patches)} patch(es) via {engine_used}" + (" (dry run)" if body.dry_run else ""),
            patch_id=patch_id
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Apply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply changes. Please check logs for details.")


@router.get("/models/validate")
async def validate_models(current_user: Dict = Depends(get_current_user)):
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
):
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
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Auto-fix failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to auto-fix models")
