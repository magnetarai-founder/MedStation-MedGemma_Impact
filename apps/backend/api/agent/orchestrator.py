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
    from ..config_paths import get_config_paths
except ImportError:
    from auth_middleware import get_current_user
    from rate_limiter import rate_limiter, get_client_ip
    from permission_engine import require_perm
    from audit_logger import get_audit_logger, AuditAction
    from config_paths import get_config_paths

PATHS = get_config_paths()

# Agent components
from .patchbus import PatchBus, ChangeProposal
from .intent_classifier import Phi3IntentClassifier as IntentClassifier
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


class EngineCapability(BaseModel):
    """Single engine capability"""
    name: str
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None
    remediation: Optional[str] = None


class CapabilitiesResponse(BaseModel):
    """Agent capabilities response"""
    engines: List[EngineCapability]
    features: Dict[str, bool]


# ==================== Endpoints ====================

@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(current_user: Dict = Depends(get_current_user)):
    """
    Get agent system capabilities and engine availability

    Returns information about which engines are available and
    provides helpful remediation messages for missing dependencies.

    No special permissions required - just authentication.
    """
    import shutil
    import subprocess

    engines = []

    # Check Aider
    aider_available = False
    aider_error = None
    aider_version = None
    aider_remediation = None

    try:
        # Detect venv from sys.executable or climb to project root
        import sys
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # Running in venv, use current venv
            venv_path = Path(sys.executable).parent.parent
        else:
            # Not in venv, try project root
            project_root = Path(os.getcwd()).parent.parent.parent
            venv_path = project_root / "venv"

        aider_path = venv_path / "bin" / "aider"

        if aider_path.exists():
            result = subprocess.run(
                [str(aider_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                aider_available = True
                aider_version = result.stdout.strip()
        else:
            aider_error = "Aider not found in venv"
            aider_remediation = f"Install Aider: source {venv_path}/bin/activate && pip install aider-chat"
    except Exception as e:
        aider_error = str(e)
        aider_remediation = "Check Aider installation and ensure venv is properly configured"

    engines.append(EngineCapability(
        name="aider",
        available=aider_available,
        version=aider_version,
        error=aider_error,
        remediation=aider_remediation
    ))

    # Check Continue
    continue_available = False
    continue_error = None
    continue_version = None
    continue_remediation = None

    try:
        cn_path = shutil.which("cn") or shutil.which("continue")
        if cn_path:
            result = subprocess.run(
                [cn_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                continue_available = True
                continue_version = result.stdout.strip()
        else:
            continue_error = "Continue CLI not found on PATH"
            continue_remediation = "Install Continue: npm install -g @continuedev/continue"
    except Exception as e:
        continue_error = str(e)
        continue_remediation = "Install Continue CLI or add it to PATH"

    engines.append(EngineCapability(
        name="continue",
        available=continue_available,
        version=continue_version,
        error=continue_error,
        remediation=continue_remediation
    ))

    # Check Codex (always available - uses subprocess/patch)
    engines.append(EngineCapability(
        name="codex",
        available=True,
        version="builtin"
    ))

    # Check Ollama (for bash intelligence)
    ollama_available = False
    ollama_error = None
    ollama_remediation = None

    try:
        if shutil.which("ollama"):
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            ollama_available = result.returncode == 0
        else:
            ollama_error = "Ollama not found on PATH"
            ollama_remediation = "Install Ollama from https://ollama.ai"
    except Exception as e:
        ollama_error = str(e)
        ollama_remediation = "Ensure Ollama is running and accessible"

    engines.append(EngineCapability(
        name="ollama",
        available=ollama_available,
        error=ollama_error,
        remediation=ollama_remediation
    ))

    # Feature flags
    features = {
        "unified_context": True,
        "bash_intelligence": ollama_available,
        "patch_apply": True,
        "dry_run": True,
        "rollback": True,
        "git_integration": shutil.which("git") is not None
    }

    return CapabilitiesResponse(
        engines=engines,
        features=features
    )


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
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(
        f"agent:route:{current_user['user_id']}",
        max_requests=60,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many route requests")

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
        # Use enhanced planner
        planner = EnhancedPlanner()

        # Generate plan (EnhancedPlanner.plan returns a Plan dataclass)
        plan_result = planner.plan(
            description=body.input,
            files=[]  # TODO: extract files from context_bundle
        )

        # Map Plan dataclass to our response format
        steps = []
        for step in plan_result.steps:
            steps.append(PlanStep(
                description=step.description,
                risk_level=step.risk,
                estimated_files=step.files
            ))

        risks = plan_result.risks
        requires_confirmation = plan_result.requires_approval

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
            estimated_time_min=plan_result.estimated_time_min,
            model_used=plan_result.model_used
        )

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


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
        # Build context bundle
        # TODO: Integrate with Continue's context providers

        file_tree_slice = []
        if body.repo_root:
            repo_path = Path(body.repo_root).resolve()

            # Security: Validate repo_root is within user's code_workspaces
            # This matches the pattern used in code_operations.py for consistent security
            user_id = current_user['user_id']
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id

            # Also allow user's home directory for convenience
            user_home = Path.home()
            allowed_roots = [user_workspace_root, user_home]

            is_allowed = False
            for allowed_root in allowed_roots:
                try:
                    repo_path.relative_to(allowed_root)
                    is_allowed = True
                    break
                except ValueError:
                    continue

            if not is_allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: repo_root must be within your workspace ({user_workspace_root}) or home directory"
                )

            if repo_path.exists():
                # Get top-level structure
                file_tree_slice = [
                    str(p.relative_to(repo_path))
                    for p in repo_path.rglob('*')
                    if p.is_file() and not any(part.startswith('.') for part in p.parts)
                ][:50]  # Limit to 50 files

        # Get recent git diffs if repo has git
        recent_diffs = []
        if body.repo_root and Path(body.repo_root).exists():
            repo_path = Path(body.repo_root).resolve()
            git_dir = repo_path / ".git"

            if git_dir.exists():
                import subprocess
                try:
                    # Get recent commits (last 5)
                    result = subprocess.run(
                        ["git", "-C", str(repo_path), "log", "--oneline", "-5"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        commits = result.stdout.strip().split('\n')
                        for commit in commits[:3]:  # Limit to 3 most recent
                            if commit:
                                commit_hash = commit.split()[0]
                                # Get diff for this commit
                                diff_result = subprocess.run(
                                    ["git", "-C", str(repo_path), "show", "--stat", commit_hash],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if diff_result.returncode == 0:
                                    recent_diffs.append({
                                        "commit": commit,
                                        "diff_stat": diff_result.stdout[:500]  # Truncate
                                    })
                except Exception as e:
                    logger.warning(f"Failed to get git diffs: {e}")

        # TODO: Get embeddings hits (future: integrate with UnifiedEmbedder)
        embeddings_hits = []

        # Get recent chat snippets from unified context
        chat_snippets = []
        if body.session_id:
            try:
                from ..unified_context import get_unified_context
                context_mgr = get_unified_context()
                recent_entries = context_mgr.get_recent_context(
                    user_id=current_user['user_id'],
                    max_entries=10,
                    sources=['chat']
                )
                chat_snippets = [
                    f"{entry.content[:100]}..." for entry in recent_entries
                ]
            except Exception as e:
                logger.warning(f"Failed to get chat snippets: {e}")

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
        # Import aider engine and patchbus
        from .engines.aider_engine import AiderEngine
        from pathlib import Path

        # Get venv path (use project root venv or default)
        # Climb up to project root from server cwd (apps/backend/api)
        project_root = Path(os.getcwd()).parent.parent.parent
        venv_path = project_root / "venv"
        if not venv_path.exists():
            venv_path = Path.home() / ".virtualenvs" / "elohimos"

        # Get repo root from request or use project root
        repo_root = Path(body.repo_root) if body.repo_root else project_root

        # Initialize Aider with correct signature
        aider = AiderEngine(
            model=body.model or 'qwen2.5-coder:32b',
            venv_path=venv_path,
            repo_root=repo_root
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
            # Apply via PatchBus with repo_root
            apply_result = PatchBus.apply(proposal, repo_root=body.repo_root)

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

            # Add to unified context for persistence
            try:
                from ..unified_context import get_unified_context
                context_mgr = get_unified_context()
                context_mgr.add_entry(
                    user_id=current_user['user_id'],
                    session_id=body.repo_root or 'default',  # Use repo_root as session_id
                    source='agent',
                    entry_type='patch',
                    content=proposal.description,
                    metadata={
                        'patch_id': patch_id,
                        'files': apply_result.get('files', []),
                        'lines': apply_result.get('lines', 0)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to add patch to unified context: {e}")

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
