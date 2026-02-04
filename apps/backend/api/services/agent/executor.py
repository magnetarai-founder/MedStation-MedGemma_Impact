#!/usr/bin/env python3
"""
Agent Executor for MagnetarCode

Orchestrates autonomous agent execution:
- Plans tasks using TaskPlanner
- Executes steps using ToolRegistry
- Monitors progress and adapts plan
- Reports results in real-time
"""

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from typing import Any

from .planner import TaskPlan, TaskPlanner, TaskStep
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status"""

    IDLE = "idle"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecutor:
    """
    Autonomous agent that executes multi-step tasks

    Features:
    - Plans tasks using LLM
    - Executes steps with tools
    - Adapts plan based on results
    - Streams progress updates
    """

    def __init__(self, workspace_root: str, llm_client=None, max_iterations: int = 20):
        """
        Initialize agent executor

        Args:
            workspace_root: Path to workspace
            llm_client: LLM client for planning and decision-making
            max_iterations: Max steps to prevent infinite loops
        """
        self.workspace_root = workspace_root
        self.llm_client = llm_client
        self.max_iterations = max_iterations

        self.planner = TaskPlanner(llm_client=llm_client)
        self.tool_registry = ToolRegistry(workspace_root=workspace_root)

        self.status = AgentStatus.IDLE
        self.current_plan: TaskPlan | None = None
        self.execution_log: list[dict[str, Any]] = []

    async def execute_task(
        self,
        task_request: str,
        workspace_context: dict[str, Any] | None = None,
        auto_approve: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a task autonomously

        Args:
            task_request: User's task description
            workspace_context: Context about the workspace
            auto_approve: Auto-approve destructive operations (dangerous!)

        Yields:
            Progress updates as Server-Sent Events
        """
        self.status = AgentStatus.PLANNING
        self.execution_log = []

        try:
            # Planning phase
            async for event in self._planning_phase(task_request, workspace_context):
                yield event

            # Check if approval required
            if self.current_plan.requires_approval and not auto_approve:
                async for event in self._approval_phase():
                    yield event
                return

            # Execution phase
            async for event in self._execution_phase():
                yield event

            # Completion phase
            async for event in self._completion_phase():
                yield event

        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            yield self._create_event("error", {"message": f"Execution failed: {e!s}"})

    async def _planning_phase(
        self, task_request: str, workspace_context: dict[str, Any] | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute planning phase and create task plan"""
        yield self._create_event("planning", {"message": "Analyzing task and creating plan..."})

        plan = await self.planner.plan_task(task_request, workspace_context)
        self.current_plan = plan

        yield self._create_event(
            "plan_created", {"plan": plan.to_dict(), "total_steps": plan.total_steps}
        )

    async def _approval_phase(self) -> AsyncIterator[dict[str, Any]]:
        """Handle approval requirement for destructive operations"""
        self.status = AgentStatus.AWAITING_APPROVAL
        yield self._create_event(
            "approval_required",
            {
                "message": "This task requires approval before execution",
                "plan": self.current_plan.to_dict(),
            },
        )

    async def _execution_phase(self) -> AsyncIterator[dict[str, Any]]:
        """Execute all steps in the plan"""
        self.status = AgentStatus.EXECUTING
        plan = self.current_plan

        for step in plan.steps:
            # Check iteration limit
            if step.step_number > self.max_iterations:
                yield self._create_event(
                    "error", {"message": f"Max iterations ({self.max_iterations}) exceeded"}
                )
                break

            # Execute single step
            async for event in self._execute_single_step(step, plan):
                yield event

                # Check if execution failed
                if event.get("type") == "execution_failed":
                    return

    async def _execute_single_step(
        self, step: TaskStep, plan: TaskPlan
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute a single step and handle result"""
        yield self._create_event(
            "step_start", {"step": step.to_dict(), "progress": plan.progress_percentage}
        )

        result = await self._execute_step(step)

        # Update step
        step.completed = result.get("success", False)
        step.result = result

        # Log result
        self.execution_log.append(
            {"step": step.step_number, "timestamp": datetime.utcnow().isoformat(), "result": result}
        )

        yield self._create_event(
            "step_complete",
            {"step": step.to_dict(), "result": result, "progress": plan.progress_percentage},
        )

        # Handle failure
        if not result.get("success", False):
            should_continue = await self._handle_step_failure(step, result)
            if not should_continue:
                self.status = AgentStatus.FAILED
                yield self._create_event(
                    "execution_failed",
                    {"message": f"Step {step.step_number} failed", "error": result.get("error")},
                )

    async def _completion_phase(self) -> AsyncIterator[dict[str, Any]]:
        """Handle successful task completion"""
        self.status = AgentStatus.COMPLETED
        yield self._create_event(
            "execution_complete",
            {
                "message": "Task completed successfully",
                "plan": self.current_plan.to_dict(),
                "execution_log": self.execution_log,
            },
        )

    async def _execute_step(self, step: TaskStep) -> dict[str, Any]:
        """Execute a single step"""
        if not step.tool_name:
            # No tool specified - just mark as complete
            return {"success": True, "message": "Step completed"}

        try:
            # Execute tool
            result = self.tool_registry.execute(step.tool_name, **(step.tool_params or {}))

            return result

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_step_failure(self, step: TaskStep, result: dict[str, Any]) -> bool:
        """
        Handle step failure - decide whether to continue or stop

        Returns:
            True if execution should continue, False otherwise
        """
        error = result.get("error", "Unknown error")

        # Check if error is recoverable
        recoverable_errors = [
            "File not found",
            "No matches found",
        ]

        for recoverable in recoverable_errors:
            if recoverable.lower() in error.lower():
                logger.info(f"Recoverable error in step {step.step_number}: {error}")
                return True  # Continue to next step

        # Non-recoverable error
        logger.error(f"Non-recoverable error in step {step.step_number}: {error}")
        return False

    def _create_event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a progress event"""
        return {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": self.status.value,
            "data": data,
        }

    def get_status(self) -> dict[str, Any]:
        """Get current agent status"""
        return {
            "status": self.status.value,
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "execution_log": self.execution_log,
        }

    async def cancel(self):
        """Cancel current execution"""
        self.status = AgentStatus.CANCELLED
        logger.info("Agent execution cancelled")
