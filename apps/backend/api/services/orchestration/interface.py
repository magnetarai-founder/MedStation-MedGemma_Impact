"""
Orchestration Interfaces

Abstract interfaces for agent orchestration.
Defines the contracts for routing, coordination, and execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator


class AgentType(Enum):
    """Types of agents available"""

    CHAT = "chat"  # General chat/Q&A
    EDIT = "edit"  # Code editing (Aider)
    ANALYZE = "analyze"  # Code analysis
    PLAN = "plan"  # Task planning
    EXECUTE = "execute"  # Task execution
    DEBUG = "debug"  # Debugging
    TEST = "test"  # Test generation
    REFACTOR = "refactor"  # Code refactoring


class TaskPriority(Enum):
    """Task execution priority"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ExecutionStatus(Enum):
    """Status of task execution"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentCapabilities:
    """Capabilities of an agent"""

    agent_type: AgentType
    name: str
    description: str

    # What the agent can do
    can_read_files: bool = True
    can_write_files: bool = False
    can_execute_commands: bool = False
    can_search_codebase: bool = True
    can_use_tools: bool = False

    # Model requirements
    preferred_model: str = ""
    min_context_window: int = 4000

    # Performance hints
    typical_latency_ms: int = 1000
    supports_streaming: bool = True


@dataclass
class OrchestrationRequest:
    """
    Request for orchestration.

    Represents a user's intent that needs to be routed
    and executed by the appropriate agents.
    """

    # Request identification
    request_id: str
    session_id: str

    # User input
    user_input: str
    context: dict[str, Any] = field(default_factory=dict)

    # Workspace
    workspace_root: str = ""
    active_file: str | None = None
    selected_code: str | None = None

    # Execution preferences
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: int = 300
    stream_response: bool = True

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_input": self.user_input[:100],
            "workspace_root": self.workspace_root,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
        }


@dataclass
class OrchestrationResult:
    """
    Result of orchestration.

    Contains the final output and execution metadata.
    """

    request_id: str
    status: ExecutionStatus

    # Output
    response: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    # Execution info
    agents_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    # Performance
    total_duration_ms: int = 0
    tokens_used: int = 0

    # Errors
    error: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "response_length": len(self.response),
            "agents_used": self.agents_used,
            "files_modified": self.files_modified,
            "duration_ms": self.total_duration_ms,
            "error": self.error,
        }


@dataclass
class RoutingDecision:
    """
    Decision about which agent(s) to use.

    Contains the routing logic's output.
    """

    primary_agent: AgentType
    secondary_agents: list[AgentType] = field(default_factory=list)

    # Routing rationale
    confidence: float = 0.8
    rationale: str = ""

    # Execution hints
    requires_planning: bool = False
    requires_context: bool = True
    estimated_steps: int = 1


class Router(ABC):
    """
    Abstract router for agent selection.

    Determines which agent(s) should handle a request.
    """

    @abstractmethod
    async def route(
        self,
        request: OrchestrationRequest,
    ) -> RoutingDecision:
        """
        Route a request to appropriate agent(s).

        Args:
            request: The orchestration request

        Returns:
            Routing decision with agent selection
        """
        pass

    @abstractmethod
    def get_available_agents(self) -> list[AgentCapabilities]:
        """Get list of available agents"""
        pass


class Coordinator(ABC):
    """
    Abstract coordinator for multi-agent execution.

    Manages the execution of complex tasks across agents.
    """

    @abstractmethod
    async def coordinate(
        self,
        request: OrchestrationRequest,
        routing: RoutingDecision,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Coordinate execution across agents.

        Args:
            request: The orchestration request
            routing: The routing decision

        Yields:
            Execution events
        """
        pass

    @abstractmethod
    async def cancel(self, request_id: str) -> bool:
        """Cancel an in-progress execution"""
        pass

    @abstractmethod
    def get_status(self, request_id: str) -> ExecutionStatus | None:
        """Get execution status"""
        pass


class Orchestrator(ABC):
    """
    Abstract orchestrator interface.

    Top-level interface that combines routing and coordination.
    """

    @abstractmethod
    async def process(
        self,
        request: OrchestrationRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Process an orchestration request.

        Args:
            request: The request to process

        Yields:
            Execution events (progress, responses, errors)
        """
        pass

    @abstractmethod
    async def get_result(
        self,
        request_id: str,
    ) -> OrchestrationResult | None:
        """Get the final result of a request"""
        pass

    @abstractmethod
    async def cancel(self, request_id: str) -> bool:
        """Cancel a request"""
        pass

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """Get orchestrator capabilities"""
        pass
