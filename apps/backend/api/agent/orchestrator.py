#!/usr/bin/env python3
"""
Agent Orchestrator API for ElohimOS
Integrates Aider + Continue + Codex for terminal-first AI coding
"""

import logging
import os
import subprocess
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

# ==================== Config Loading ====================

import yaml

CONFIG_PATH = Path(__file__).parent / "agent.config.yaml"

def load_agent_config() -> Dict[str, Any]:
    """Load agent configuration from YAML"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded agent config from {CONFIG_PATH}")
                return config
        except Exception as e:
            logger.error(f"Failed to load agent config: {e}")

    # Defaults if config missing
    logger.warning("Using default agent config (agent.config.yaml not found)")
    return {
        "engine_order": ["aider"],  # Aider only by default
        "models": {
            "planner": "ollama/deepseek-r1:8b",
            "coder": "ollama/qwen2.5-coder:32b",
            "committer": "ollama/llama3.1:8b"
        },
        "verify": {"enabled": True, "timeout_sec": 120},
        "commit": {"enabled": True, "branch_strategy": "patch-branches"},
        "security": {"strict_workspace": True}
    }

AGENT_CONFIG = load_agent_config()


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
    files: Optional[List[str]] = Field(None, description="Files to edit (if not specified, Aider will determine)")
    session_id: Optional[str] = Field(None, description="Workspace session ID for unified context")
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
    cfg = AGENT_CONFIG

    # Get available Ollama models
    available_models = []
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]  # First column is model name
                    available_models.append(f"ollama/{model_name}")
    except Exception as e:
        logger.warning(f"Failed to get Ollama models: {e}")

    return {
        "orchestrator": cfg.get("orchestrator", {"enabled": True, "model": "ollama/qwen2.5-coder:1.5b-base"}),
        "user_preferences": cfg.get("user_model_preferences", {}),
        "recommended_models": cfg.get("recommended_models", {}),
        "strict_models": cfg.get("strict_models", {}),
        "available_models": available_models,
        "note": "When orchestrator is enabled, it automatically selects models. When disabled, you choose per task."
    }


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
        # Load current config
        if not CONFIG_PATH.exists():
            raise HTTPException(404, "Config file not found")

        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)

        # Update orchestrator if provided
        if "orchestrator" in body:
            if "enabled" in body["orchestrator"]:
                config["orchestrator"]["enabled"] = body["orchestrator"]["enabled"]

        # Update user preferences if provided
        if "user_preferences" in body:
            if "user_model_preferences" not in config:
                config["user_model_preferences"] = {}
            config["user_model_preferences"].update(body["user_preferences"])

        # Write updated config
        with open(CONFIG_PATH, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

        # Reload config in memory
        global AGENT_CONFIG
        AGENT_CONFIG = load_agent_config()

        logger.info(f"Model settings updated by {current_user['username']}")

        return {
            "success": True,
            "message": "Model settings updated successfully",
            "orchestrator": config.get("orchestrator"),
            "user_preferences": config.get("user_model_preferences")
        }

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
        # Log full error server-side, return generic message to client
        logger.error(f"Route failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to route request. Please try again.")


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
        # Build context bundle
        # TODO: Integrate with Continue's context providers

        file_tree_slice = []
        if body.repo_root:
            repo_path = Path(body.repo_root).resolve()

            # Security: Validate repo_root is within user's code_workspaces
            # This matches the pattern used in code_operations.py for consistent security
            user_id = current_user['user_id']
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id

            # Allow user's home directory for convenience (can be disabled via env var)
            # Set ELOHIM_STRICT_WORKSPACE=1 to restrict to code_workspaces only
            allowed_roots = [user_workspace_root]
            if not os.getenv("ELOHIM_STRICT_WORKSPACE", "").lower() in ("1", "true", "yes"):
                user_home = Path.home()
                allowed_roots.append(user_home)

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
                                try:
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
                                except subprocess.TimeoutExpired:
                                    # On timeout, skip this commit but continue with others
                                    logger.warning(f"Git show timeout for {commit_hash}, skipping")
                                    continue
                except subprocess.TimeoutExpired:
                    # On timeout getting commits, return empty list but don't fail the whole request
                    logger.warning(f"Git log timeout for {repo_path}, proceeding without git context")
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
        # Get config
        cfg = AGENT_CONFIG
        engines = cfg.get("engine_order", ["aider"])
        coder_model = body.model or cfg["models"]["coder"]

        # Get paths
        project_root = Path(os.getcwd()).parent.parent.parent
        venv_path = project_root / "venv"
        if not venv_path.exists():
            venv_path = Path.home() / ".virtualenvs" / "elohimos"

        repo_root = Path(body.repo_root) if body.repo_root else project_root

        # Get files and context
        files = body.files or []
        context_snippets = []

        # Try engines in order until one succeeds
        proposal = None
        engine_used = None

        for engine_name in engines:
            try:
                logger.info(f"Trying engine: {engine_name}")

                if engine_name == "aider":
                    from .engines.aider_engine import AiderEngine
                    engine = AiderEngine(
                        model=coder_model,
                        venv_path=venv_path,
                        repo_root=repo_root
                    )
                    proposal = engine.propose(body.input, files, context_snippets)

                elif engine_name == "continue":
                    from .engines.continue_engine import ContinueEngine
                    engine = ContinueEngine(model=coder_model)
                    proposal = engine.propose(body.input, files, context_snippets)

                else:
                    logger.warning(f"Unknown engine: {engine_name}")
                    continue

                # Check if we got a valid diff
                if proposal and proposal.diff.strip():
                    engine_used = engine_name
                    logger.info(f"✓ {engine_name} generated diff ({len(proposal.diff)} chars)")
                    break
                else:
                    logger.warning(f"✗ {engine_name} returned empty diff")

            except Exception as e:
                logger.warning(f"✗ {engine_name} failed: {e}")
                continue

        # If no engine succeeded, fail
        if not proposal or not proposal.diff.strip():
            raise HTTPException(
                status_code=500,
                detail="No engine generated a diff. Check logs for details."
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
                from ..workspace_session import get_workspace_session_manager

                context_mgr = get_unified_context()
                ws_mgr = get_workspace_session_manager()

                # Get or create workspace session for this repo
                workspace_session_id = body.session_id
                if not workspace_session_id and body.repo_root:
                    workspace_session_id = ws_mgr.get_or_create_for_workspace(
                        user_id=current_user['user_id'],
                        workspace_root=body.repo_root
                    )

                if workspace_session_id:
                    context_mgr.add_entry(
                        user_id=current_user['user_id'],
                        session_id=workspace_session_id,
                        source='agent',
                        entry_type='patch',
                        content=proposal.description,
                        metadata={
                            'patch_id': patch_id,
                            'files': apply_result.get('files', []),
                            'lines': apply_result.get('lines', 0),
                            'repo_root': body.repo_root
                        }
                    )
                else:
                    logger.warning("No session_id or repo_root provided, skipping unified context")
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
            summary=f"Generated {len(patches)} patch(es) via {engine_used}" + (" (dry run)" if body.dry_run else ""),
            patch_id=patch_id
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log full error server-side, return generic message to client
        logger.error(f"Apply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply changes. Please check logs for details.")
