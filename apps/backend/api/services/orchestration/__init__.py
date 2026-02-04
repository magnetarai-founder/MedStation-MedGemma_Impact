"""
Orchestration Engine

Unified orchestration for MagnetarCode's agent system.
Routes requests, coordinates agents, and manages execution.

Usage:
    from api.services.orchestration import (
        MagnetarOrchestrator,
        OrchestrationRequest,
        create_orchestrator,
        orchestrate,
    )

    # Full orchestrator setup
    orchestrator = create_orchestrator(
        workspace_root="/path/to/project",
        enable_aider=True,
        enable_continue=True,
    )

    request = OrchestrationRequest(
        request_id="req-123",
        session_id="session-456",
        user_input="Add error handling to the login function",
        workspace_root="/path/to/project",
    )

    async for event in orchestrator.process(request):
        if event["type"] == "chunk":
            print(event["content"], end="")

    # Quick orchestration
    async for event in orchestrate(
        "Explain this code",
        workspace_root="/path/to/project",
    ):
        print(event)

Architecture:
    Request → Router → Coordinator → Agent Executors → Response

    1. Router: Uses NLP intent classification to select agent(s)
    2. Coordinator: Manages multi-agent execution flow
    3. Executors: Agent-specific execution logic
    4. All integrated with Aider (edits) and Continue (IDE)
"""

from .coordinator import (
    AgentExecutor,
    ExecutionCoordinator,
    ExecutionState,
)
from .interface import (
    AgentCapabilities,
    AgentType,
    Coordinator,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
    Orchestrator,
    Router,
    RoutingDecision,
    TaskPriority,
)
from .orchestrator import (
    MagnetarOrchestrator,
    create_orchestrator,
    orchestrate,
)
from .router import (
    AGENT_CAPABILITIES,
    IntentBasedRouter,
    RuleBasedRouter,
    create_router,
)

__all__ = [
    # Core interfaces
    "Orchestrator",
    "Router",
    "Coordinator",
    # Types
    "AgentType",
    "AgentCapabilities",
    "TaskPriority",
    "ExecutionStatus",
    "OrchestrationRequest",
    "OrchestrationResult",
    "RoutingDecision",
    # Implementations
    "MagnetarOrchestrator",
    "IntentBasedRouter",
    "RuleBasedRouter",
    "ExecutionCoordinator",
    "AgentExecutor",
    "ExecutionState",
    # Factory functions
    "create_orchestrator",
    "create_router",
    "orchestrate",
    # Constants
    "AGENT_CAPABILITIES",
]
