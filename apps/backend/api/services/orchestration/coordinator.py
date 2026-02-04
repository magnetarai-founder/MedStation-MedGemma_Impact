"""
Execution Coordinator

Coordinates execution across multiple agents.
Manages the agentic loop for complex multi-step tasks.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator

from .interface import (
    AgentType,
    Coordinator,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionState:
    """State of an execution"""

    request_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Progress
    current_step: int = 0
    total_steps: int = 1
    current_agent: AgentType | None = None

    # Results
    response_chunks: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    # Agents used
    agents_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)

    # Errors
    error: str | None = None
    error_type: str | None = None

    # Metrics
    tokens_used: int = 0

    def get_duration_ms(self) -> int:
        """Get execution duration in milliseconds"""
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.utcnow()
        return int((end - self.started_at).total_seconds() * 1000)

    def to_result(self) -> OrchestrationResult:
        """Convert to OrchestrationResult"""
        return OrchestrationResult(
            request_id=self.request_id,
            status=self.status,
            response="".join(self.response_chunks),
            artifacts=self.artifacts,
            agents_used=self.agents_used,
            tools_used=self.tools_used,
            files_modified=self.files_modified,
            total_duration_ms=self.get_duration_ms(),
            tokens_used=self.tokens_used,
            error=self.error,
            error_type=self.error_type,
        )


class AgentExecutor:
    """
    Executes a single agent.

    Wraps agent-specific logic for the coordinator.
    """

    def __init__(
        self,
        agent_type: AgentType,
        aider_bridge=None,
        continue_bridge=None,
    ):
        self.agent_type = agent_type
        self._aider_bridge = aider_bridge
        self._continue_bridge = continue_bridge

    async def execute(
        self,
        request: OrchestrationRequest,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute the agent.

        Args:
            request: The orchestration request
            context: Additional context from previous steps

        Yields:
            Execution events
        """
        yield {
            "type": "agent_start",
            "agent": self.agent_type.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Route to appropriate handler
            if self.agent_type == AgentType.EDIT:
                async for event in self._execute_edit(request, context):
                    yield event

            elif self.agent_type == AgentType.ANALYZE:
                async for event in self._execute_analyze(request, context):
                    yield event

            elif self.agent_type == AgentType.CHAT:
                async for event in self._execute_chat(request, context):
                    yield event

            elif self.agent_type == AgentType.PLAN:
                async for event in self._execute_plan(request, context):
                    yield event

            elif self.agent_type == AgentType.DEBUG:
                async for event in self._execute_debug(request, context):
                    yield event

            elif self.agent_type == AgentType.TEST:
                async for event in self._execute_test(request, context):
                    yield event

            elif self.agent_type == AgentType.REFACTOR:
                async for event in self._execute_refactor(request, context):
                    yield event

            else:
                # Fallback to chat
                async for event in self._execute_chat(request, context):
                    yield event

        except Exception as e:
            logger.exception(f"Agent execution error: {e}")
            yield {
                "type": "error",
                "agent": self.agent_type.value,
                "error": str(e),
                "error_type": type(e).__name__,
            }

        yield {
            "type": "agent_complete",
            "agent": self.agent_type.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _execute_edit(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute edit via Aider"""
        if not self._aider_bridge:
            yield {"type": "chunk", "content": "Edit requires Aider integration.\n"}
            return

        files = []
        if request.active_file:
            files.append(request.active_file)

        async for chunk in self._aider_bridge.stream_edit(
            instruction=request.user_input,
            files=files,
            context=context,
        ):
            yield {"type": "chunk", "content": chunk}

    async def _execute_analyze(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute code analysis"""
        if self._continue_bridge:
            from ..continue_ext import ChatRequest, ChatMessage, MessageRole

            chat_request = ChatRequest(
                messages=[
                    ChatMessage(
                        role=MessageRole.USER,
                        content=request.user_input,
                    )
                ],
                workspace_root=request.workspace_root,
                active_file=request.active_file,
            )

            async for response in self._continue_bridge.handle_chat(chat_request):
                if response.content:
                    yield {"type": "chunk", "content": response.content}
        else:
            yield {
                "type": "chunk",
                "content": f"Analyzing: {request.user_input}\n"
            }

    async def _execute_chat(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute chat response"""
        if self._continue_bridge:
            from ..continue_ext import ChatRequest, ChatMessage, MessageRole

            chat_request = ChatRequest(
                messages=[
                    ChatMessage(
                        role=MessageRole.USER,
                        content=request.user_input,
                    )
                ],
                workspace_root=request.workspace_root,
            )

            async for response in self._continue_bridge.handle_chat(chat_request):
                if response.content:
                    yield {"type": "chunk", "content": response.content}
        else:
            yield {
                "type": "chunk",
                "content": f"I understand you want: {request.user_input}\n"
            }

    async def _execute_plan(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute task planning"""
        from ..planning import RecursivePlanner

        try:
            planner = RecursivePlanner()
            task_tree = await planner.plan(
                goal=request.user_input,
                context=context or {},
            )

            yield {
                "type": "plan",
                "task_tree": task_tree.to_dict() if task_tree else None,
            }

            yield {
                "type": "chunk",
                "content": f"Created plan with {task_tree.total_subtasks if task_tree else 0} tasks\n"
            }

        except Exception as e:
            yield {"type": "chunk", "content": f"Planning failed: {e}\n"}

    async def _execute_debug(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute debugging assistance"""
        yield {
            "type": "chunk",
            "content": "Analyzing the issue...\n"
        }

        if request.selected_code:
            yield {
                "type": "chunk",
                "content": f"Examining code:\n```\n{request.selected_code[:500]}\n```\n"
            }

        yield {
            "type": "chunk",
            "content": "Potential issues to investigate...\n"
        }

    async def _execute_test(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute test generation"""
        yield {
            "type": "chunk",
            "content": "Generating tests...\n"
        }

        if self._aider_bridge and request.active_file:
            instruction = f"Generate comprehensive tests for: {request.user_input}"
            async for chunk in self._aider_bridge.stream_edit(
                instruction=instruction,
                files=[request.active_file],
            ):
                yield {"type": "chunk", "content": chunk}
        else:
            yield {
                "type": "chunk",
                "content": "Test generation requires Aider and an active file.\n"
            }

    async def _execute_refactor(
        self, request: OrchestrationRequest, context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute refactoring"""
        if self._aider_bridge:
            files = []
            if request.active_file:
                files.append(request.active_file)

            instruction = f"Refactor: {request.user_input}"
            async for chunk in self._aider_bridge.stream_edit(
                instruction=instruction,
                files=files,
            ):
                yield {"type": "chunk", "content": chunk}
        else:
            yield {
                "type": "chunk",
                "content": "Refactoring requires Aider integration.\n"
            }


class ExecutionCoordinator(Coordinator):
    """
    Coordinates multi-agent execution.

    Features:
    - Sequential and parallel agent execution
    - Progress tracking
    - Cancellation support
    - Result aggregation
    """

    def __init__(
        self,
        aider_bridge=None,
        continue_bridge=None,
    ):
        """
        Initialize coordinator.

        Args:
            aider_bridge: Aider bridge for edit agents
            continue_bridge: Continue bridge for chat/analysis
        """
        self._aider_bridge = aider_bridge
        self._continue_bridge = continue_bridge

        # Execution tracking
        self._executions: dict[str, ExecutionState] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

        # Agent executors
        self._executors: dict[AgentType, AgentExecutor] = {}
        self._init_executors()

    def _init_executors(self) -> None:
        """Initialize agent executors"""
        for agent_type in AgentType:
            self._executors[agent_type] = AgentExecutor(
                agent_type=agent_type,
                aider_bridge=self._aider_bridge,
                continue_bridge=self._continue_bridge,
            )

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
        # Initialize execution state
        state = ExecutionState(
            request_id=request.request_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_steps=routing.estimated_steps,
        )
        self._executions[request.request_id] = state

        # Create cancel event
        cancel_event = asyncio.Event()
        self._cancel_events[request.request_id] = cancel_event

        yield {
            "type": "execution_start",
            "request_id": request.request_id,
            "routing": {
                "primary": routing.primary_agent.value,
                "secondary": [a.value for a in routing.secondary_agents],
                "confidence": routing.confidence,
            },
        }

        try:
            # Execute primary agent
            state.current_agent = routing.primary_agent
            state.agents_used.append(routing.primary_agent.value)

            executor = self._executors[routing.primary_agent]

            async for event in executor.execute(request):
                # Check for cancellation
                if cancel_event.is_set():
                    state.status = ExecutionStatus.CANCELLED
                    yield {"type": "cancelled", "request_id": request.request_id}
                    return

                # Update state from event
                self._update_state_from_event(state, event)

                yield event

            # Execute secondary agents sequentially
            for secondary_agent in routing.secondary_agents:
                if cancel_event.is_set():
                    break

                state.current_step += 1
                state.current_agent = secondary_agent
                state.agents_used.append(secondary_agent.value)

                executor = self._executors[secondary_agent]

                # Pass previous context to secondary agents
                context = {
                    "previous_response": "".join(state.response_chunks),
                    "files_modified": state.files_modified,
                }

                async for event in executor.execute(request, context):
                    if cancel_event.is_set():
                        break

                    self._update_state_from_event(state, event)
                    yield event

            # Mark complete
            state.status = ExecutionStatus.COMPLETED
            state.completed_at = datetime.utcnow()

            yield {
                "type": "execution_complete",
                "request_id": request.request_id,
                "duration_ms": state.get_duration_ms(),
                "agents_used": state.agents_used,
            }

        except Exception as e:
            state.status = ExecutionStatus.FAILED
            state.error = str(e)
            state.error_type = type(e).__name__
            state.completed_at = datetime.utcnow()

            yield {
                "type": "execution_error",
                "request_id": request.request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

        finally:
            # Cleanup
            self._cancel_events.pop(request.request_id, None)

    def _update_state_from_event(
        self, state: ExecutionState, event: dict[str, Any]
    ) -> None:
        """Update execution state from an event"""
        event_type = event.get("type")

        if event_type == "chunk":
            state.response_chunks.append(event.get("content", ""))

        elif event_type == "file_modified":
            state.files_modified.append(event.get("file", ""))

        elif event_type == "tool_used":
            state.tools_used.append(event.get("tool", ""))

        elif event_type == "tokens":
            state.tokens_used += event.get("count", 0)

        elif event_type == "artifact":
            state.artifacts.append(event.get("artifact", {}))

        elif event_type == "error":
            state.error = event.get("error")
            state.error_type = event.get("error_type")

    async def cancel(self, request_id: str) -> bool:
        """Cancel an in-progress execution"""
        cancel_event = self._cancel_events.get(request_id)
        if cancel_event:
            cancel_event.set()
            return True
        return False

    def get_status(self, request_id: str) -> ExecutionStatus | None:
        """Get execution status"""
        state = self._executions.get(request_id)
        return state.status if state else None

    def get_result(self, request_id: str) -> OrchestrationResult | None:
        """Get execution result"""
        state = self._executions.get(request_id)
        return state.to_result() if state else None

    def get_stats(self) -> dict[str, Any]:
        """Get coordinator statistics"""
        total = len(self._executions)
        by_status = {}
        for state in self._executions.values():
            status = state.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_executions": total,
            "by_status": by_status,
            "active_executions": len(self._cancel_events),
        }
