"""
Agent Orchestration Package

Modular orchestration logic for agent endpoints:
- Models: Pydantic request/response models
- Config: Agent configuration management
- Capabilities: Engine availability detection
- Model Settings: Model configuration and validation
- Routing: Intent classification
- Planning: Plan generation
- Context Bundle: Context building with security
- Apply: Plan application via engines

Created during Phase 6.3d modularization.
"""

# Models
from .models import (
    RouteRequest, RouteResponse,
    PlanRequest, PlanStep, PlanResponse,
    ContextRequest, ContextResponse,
    ApplyRequest, FilePatch, ApplyResponse,
    EngineCapability, CapabilitiesResponse,
    AgentSession, AgentSessionCreateRequest,  # Phase C
)

# Config
from .config import get_agent_config, reload_config, CONFIG_PATH

# Capabilities
from .capabilities import get_capabilities_logic

# Model Settings
from .model_settings import (
    get_models_overview,
    update_model_settings_logic,
    validate_models_logic,
    auto_fix_models_logic,
)

# Routing
from .routing import route_input_logic

# Planning
from .planning import generate_plan_logic

# Context Bundle
from .context_bundle import build_context_bundle

# Apply
from .apply import apply_plan_logic


__all__ = [
    # Models
    'RouteRequest', 'RouteResponse',
    'PlanRequest', 'PlanStep', 'PlanResponse',
    'ContextRequest', 'ContextResponse',
    'ApplyRequest', 'FilePatch', 'ApplyResponse',
    'EngineCapability', 'CapabilitiesResponse',
    'AgentSession', 'AgentSessionCreateRequest',  # Phase C

    # Config
    'get_agent_config', 'reload_config', 'CONFIG_PATH',

    # Logic functions
    'get_capabilities_logic',
    'get_models_overview',
    'update_model_settings_logic',
    'validate_models_logic',
    'auto_fix_models_logic',
    'route_input_logic',
    'generate_plan_logic',
    'build_context_bundle',
    'apply_plan_logic',
]
