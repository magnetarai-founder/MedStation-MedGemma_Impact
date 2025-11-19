"""
Agent Orchestration - Request/Response Models

Pydantic models for all agent API endpoints:
- Route: Intent classification and routing
- Plan: Plan generation
- Context: Context bundle construction
- Apply: Plan application via Aider/Continue/Codex
- Capabilities: Engine availability checking
- Model Settings: Model configuration

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ==================== Route Models ====================

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


# ==================== Plan Models ====================

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


# ==================== Context Models ====================

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


# ==================== Apply Models ====================

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


# ==================== Capabilities Models ====================

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
