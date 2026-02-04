"""
Agentic Executor

Main executor implementing the Execute → Observe → Reflect → Decide loop.
Orchestrates all components for autonomous task execution.
"""

import logging
import time
from typing import Any, AsyncIterator

from ..agent.results import StepResult, failure_result, success_result
from ..planning import DependencyGraph, HierarchicalTask, TaskStatus
from .decision import DecisionEngine
from .memory import WorkingMemory
from .models import (
    Decision,
    DecisionType,
    LoopPhase,
    LoopState,
    Observation,
    Reflection,
)
from .observation import ObservationEngine
from .reflection import ReflectionEngine

logger = logging.getLogger(__name__)


class AgenticExecutor:
    """
    Autonomous executor with self-reflection and correction.

    Implements the core agentic loop:
    1. EXECUTE: Run a task using tools
    2. OBSERVE: Collect results and side effects
    3. REFLECT: Analyze what happened
    4. DECIDE: Choose next action

    Features:
    - Self-correction on failures
    - Learning from outcomes
    - Progress tracking
    - Graceful degradation
    """

    def __init__(
        self,
        tool_registry=None,
        llm_client=None,
        workspace_root: str | None = None,
        max_iterations: int = 20,
    ):
        """
        Initialize agentic executor.

        Args:
            tool_registry: Registry of available tools
            llm_client: LLM client for reflection/planning
            workspace_root: Root directory for file operations
            max_iterations: Maximum loop iterations
        """
        self.tool_registry = tool_registry
        self.llm_client = llm_client
        self.max_iterations = max_iterations

        # Initialize components
        self.observation_engine = ObservationEngine(workspace_root)
        self.reflection_engine = ReflectionEngine(llm_client)
        self.decision_engine = DecisionEngine(llm_client)
        self.memory = WorkingMemory()

        # Current state
        self.loop_state: LoopState | None = None
        self.dependency_graph: DependencyGraph | None = None

    async def execute(
        self,
        task_tree: HierarchicalTask,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a task tree with the agentic loop.

        Yields events as execution progresses.

        Args:
            task_tree: Root task to execute
            context: Optional execution context

        Yields:
            Event dicts with type and data
        """
        # Initialize state
        self.loop_state = LoopState(
            goal=task_tree.description,
            original_plan_id=task_tree.id,
            max_iterations=self.max_iterations,
        )

        # Build dependency graph
        self.dependency_graph = DependencyGraph.from_task_tree(task_tree)

        yield {
            "type": "loop_start",
            "data": {
                "goal": task_tree.description,
                "total_tasks": task_tree.total_subtasks,
            },
        }

        # Main execution loop
        while self.loop_state.should_continue:
            try:
                # Get ready tasks
                ready_tasks = self.dependency_graph.get_ready_tasks()

                if not ready_tasks:
                    # Check if we're done
                    pending = [
                        t for t in self.dependency_graph.nodes.values()
                        if t.status == TaskStatus.PENDING
                    ]
                    if not pending:
                        self.loop_state.mark_complete()
                        yield {"type": "loop_complete", "data": {"success": True}}
                        break

                    # Might be blocked
                    blocked = [
                        t for t in self.dependency_graph.nodes.values()
                        if t.status == TaskStatus.BLOCKED
                    ]
                    if blocked:
                        self.loop_state.mark_error("All remaining tasks are blocked")
                        yield {"type": "loop_error", "data": {"error": "Tasks blocked"}}
                        break

                    # Shouldn't happen
                    break

                # Execute one task
                current_task = ready_tasks[0]

                async for event in self._execute_iteration(current_task):
                    yield event

                    # Check for user interaction needed
                    if event.get("type") == "ask_user":
                        # Pause execution, wait for user
                        return

            except Exception as e:
                logger.exception(f"Loop iteration error: {e}")
                self.loop_state.mark_error(str(e))
                yield {"type": "loop_error", "data": {"error": str(e)}}
                break

        # Final state
        yield {
            "type": "loop_end",
            "data": self.loop_state.to_dict(),
        }

    async def _execute_iteration(
        self, task: HierarchicalTask
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute one iteration of the loop.

        Args:
            task: Task to execute

        Yields:
            Event dicts
        """
        self.loop_state.phase = LoopPhase.EXECUTE

        yield {
            "type": "task_start",
            "data": {
                "task_id": task.id,
                "description": task.description,
                "iteration": self.loop_state.iteration,
            },
        }

        # Take snapshot for change detection
        self.observation_engine.take_snapshot()
        start_time = time.time()

        # EXECUTE
        task.mark_started()
        result = await self._execute_task(task)

        # OBSERVE
        self.loop_state.phase = LoopPhase.OBSERVE
        observation = self.observation_engine.observe(
            action_id=task.id,
            action_description=task.description,
            result=result,
            start_time=start_time,
        )

        self.loop_state.add_observation(observation)
        self.memory.add_observation(observation)

        yield {
            "type": "observation",
            "data": observation.to_dict(),
        }

        # Update task state
        if observation.success:
            task.mark_completed(result.output)
            self.loop_state.completed_tasks.append(task.id)
        else:
            task.mark_failed(observation.error or "Unknown error")
            self.loop_state.failed_tasks.append(task.id)

        # REFLECT
        self.loop_state.phase = LoopPhase.REFLECT
        reflection = await self.reflection_engine.reflect(
            observation=observation,
            goal=self.loop_state.goal,
            history=self.memory.get_recent_observations(5),
            loop_state=self.loop_state,
        )

        self.loop_state.add_reflection(reflection)
        self.memory.add_reflection(reflection)

        yield {
            "type": "reflection",
            "data": reflection.to_dict(),
        }

        # DECIDE
        self.loop_state.phase = LoopPhase.DECIDE
        next_ready = self.dependency_graph.get_ready_tasks()
        # Remove current task from ready list
        next_ready = [t for t in next_ready if t.id != task.id]

        decision = await self.decision_engine.decide(
            reflection=reflection,
            current_task=task,
            loop_state=self.loop_state,
            next_tasks=next_ready,
        )

        self.loop_state.add_decision(decision)
        self.memory.add_decision(decision)

        yield {
            "type": "decision",
            "data": decision.to_dict(),
        }

        # Apply decision
        await self._apply_decision(decision, task)

        # Check for special decision types
        if decision.decision_type == DecisionType.COMPLETE:
            self.loop_state.mark_complete()

        elif decision.decision_type == DecisionType.ABORT:
            self.loop_state.mark_error(decision.rationale)

        elif decision.decision_type == DecisionType.ASK_USER:
            yield {
                "type": "ask_user",
                "data": {
                    "question": decision.user_question,
                    "context": self.memory.to_context_string(500),
                },
            }

    async def _execute_task(self, task: HierarchicalTask) -> StepResult:
        """
        Execute a single task.

        Args:
            task: Task to execute

        Returns:
            StepResult from execution
        """
        # If task is composite (has children), it's already broken down
        if task.children:
            return success_result(
                output="Composite task - children will be executed",
                metadata={"child_count": len(task.children)},
            )

        # If no tool specified, can't execute
        if not task.tool_name:
            return failure_result(
                error_message="No tool specified for task",
                recoverable=False,
            )

        # Check if tool exists
        if self.tool_registry and task.tool_name not in self.tool_registry:
            return failure_result(
                error_message=f"Tool not found: {task.tool_name}",
                recoverable=False,
            )

        # Execute the tool
        try:
            if self.tool_registry:
                tool = self.tool_registry.get(task.tool_name)
                if tool:
                    output = await tool.execute(task.tool_params or {})
                    return success_result(output=output)

            # Fallback: simulate execution
            return success_result(
                output=f"Simulated: {task.description}",
                metadata={"simulated": True},
            )

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            return failure_result(
                error_message=str(e),
                recoverable=True,
            )

    async def _apply_decision(
        self, decision: Decision, current_task: HierarchicalTask
    ) -> None:
        """
        Apply a decision to update state.

        Args:
            decision: Decision to apply
            current_task: The current task
        """
        if decision.decision_type == DecisionType.SKIP:
            current_task.status = TaskStatus.SKIPPED
            self.loop_state.skipped_tasks.append(current_task.id)

        elif decision.decision_type == DecisionType.RETRY:
            # Reset task for retry
            current_task.status = TaskStatus.PENDING
            current_task.error = None

        elif decision.decision_type == DecisionType.MODIFY:
            # Plan modification would be handled here
            # For now, just log it
            logger.info(f"Plan modification requested: {decision.modified_plan}")

    def get_state(self) -> LoopState | None:
        """Get current loop state"""
        return self.loop_state

    def get_memory(self) -> WorkingMemory:
        """Get working memory"""
        return self.memory

    def get_progress(self) -> dict[str, Any]:
        """Get execution progress summary"""
        if not self.loop_state:
            return {"status": "not_started"}

        return {
            "status": self.loop_state.phase.value,
            "iteration": self.loop_state.iteration,
            "max_iterations": self.loop_state.max_iterations,
            "completed_tasks": len(self.loop_state.completed_tasks),
            "failed_tasks": len(self.loop_state.failed_tasks),
            "skipped_tasks": len(self.loop_state.skipped_tasks),
            "progress": self.loop_state.progress,
            "success": self.loop_state.success,
        }

    async def resume(
        self, user_response: str
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Resume execution after user input.

        Args:
            user_response: User's response to the question

        Yields:
            Event dicts
        """
        if not self.loop_state:
            yield {"type": "error", "data": {"error": "No loop state to resume"}}
            return

        # Add user response to memory
        self.memory.add_fact("user_response", user_response, importance=0.9)

        yield {
            "type": "user_response_received",
            "data": {"response": user_response},
        }

        # Continue execution
        # (Would need to restore task context and continue loop)

    def abort(self, reason: str = "") -> None:
        """
        Abort execution.

        Args:
            reason: Reason for aborting
        """
        if self.loop_state:
            self.loop_state.mark_aborted(reason)
