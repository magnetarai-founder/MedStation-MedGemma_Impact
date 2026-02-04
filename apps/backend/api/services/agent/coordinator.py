#!/usr/bin/env python3
"""
Multi-Agent Coordinator

Manages collaboration between multiple agents:
- Task decomposition and assignment
- Inter-agent communication
- Workflow orchestration
- Result aggregation
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .agent_types import AgentProfile, AgentRole, get_collaborative_agents
from .executor import AgentExecutor
from .feedback import TaskExecution, TaskOutcome, get_feedback_store
from .planner import TaskPlanner, TaskStep


class CoordinationStrategy(Enum):
    """Strategies for multi-agent coordination"""

    SEQUENTIAL = "sequential"  # Agents work one after another
    PARALLEL = "parallel"  # Agents work simultaneously
    PIPELINE = "pipeline"  # Output of one feeds into next
    COLLABORATIVE = "collaborative"  # Agents work together on same task


@dataclass
class AgentMessage:
    """Message passed between agents"""

    from_agent: str
    to_agent: str
    message_type: str  # "request", "response", "data", "error"
    content: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AgentTask:
    """Task assigned to a specific agent"""

    task_id: str
    agent_role: AgentRole
    description: str
    steps: list[TaskStep]
    dependencies: list[str] = field(default_factory=list)  # Task IDs this depends on
    status: str = "pending"  # pending, in_progress, completed, failed
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class WorkflowExecution:
    """Tracks execution of a multi-agent workflow"""

    workflow_id: str
    description: str
    strategy: CoordinationStrategy
    agent_tasks: list[AgentTask]
    start_time: str
    end_time: str | None = None
    status: str = "running"  # running, completed, failed
    messages: list[AgentMessage] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if all tasks are complete"""
        return all(task.status in ["completed", "failed"] for task in self.agent_tasks)

    def get_results(self) -> dict[str, Any]:
        """Aggregate results from all agents"""
        results = {}
        for task in self.agent_tasks:
            if task.result:
                results[task.agent_role.value] = task.result
        return results


class MultiAgentCoordinator:
    """
    Coordinates multiple agents working together

    Handles:
    - Task decomposition across agents
    - Execution ordering and dependencies
    - Inter-agent communication
    - Result aggregation
    """

    def __init__(self):
        self.planner = TaskPlanner()
        self.feedback_store = get_feedback_store()
        self.active_workflows: dict[str, WorkflowExecution] = {}

    async def execute_collaborative_task(
        self,
        task_description: str,
        workspace_path: str,
        strategy: CoordinationStrategy = CoordinationStrategy.SEQUENTIAL,
        auto_approve: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Execute a task using multiple collaborating agents

        Args:
            task_description: Description of the task
            workspace_path: Path to workspace
            strategy: Coordination strategy
            auto_approve: Skip approval steps

        Yields:
            Progress updates and results
        """
        workflow_id = str(uuid.uuid4())

        yield {
            "type": "workflow_started",
            "workflow_id": workflow_id,
            "description": task_description,
            "strategy": strategy.value,
        }

        # 1. Determine which agents should collaborate
        agents = get_collaborative_agents(task_description)

        yield {"type": "agents_selected", "agents": [agent.name for agent in agents]}

        # 2. Create workflow execution
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            description=task_description,
            strategy=strategy,
            agent_tasks=[],
            start_time=datetime.utcnow().isoformat(),
        )

        # 3. Decompose task for each agent
        agent_tasks = await self._decompose_for_agents(task_description, agents, workspace_path)
        workflow.agent_tasks = agent_tasks

        self.active_workflows[workflow_id] = workflow

        # 4. Execute based on strategy
        if strategy == CoordinationStrategy.SEQUENTIAL:
            async for update in self._execute_sequential(workflow, workspace_path, auto_approve):
                yield update

        elif strategy == CoordinationStrategy.PARALLEL:
            async for update in self._execute_parallel(workflow, workspace_path, auto_approve):
                yield update

        elif strategy == CoordinationStrategy.PIPELINE:
            async for update in self._execute_pipeline(workflow, workspace_path, auto_approve):
                yield update

        elif strategy == CoordinationStrategy.COLLABORATIVE:
            async for update in self._execute_collaborative(workflow, workspace_path, auto_approve):
                yield update

        # 5. Aggregate results
        workflow.end_time = datetime.utcnow().isoformat()
        workflow.status = (
            "completed" if all(t.status == "completed" for t in workflow.agent_tasks) else "failed"
        )

        yield {
            "type": "workflow_completed",
            "workflow_id": workflow_id,
            "status": workflow.status,
            "results": workflow.get_results(),
        }

    async def _decompose_for_agents(
        self, task_description: str, agents: list[AgentProfile], workspace_path: str
    ) -> list[AgentTask]:
        """Decompose task into subtasks for each agent"""
        agent_tasks = []

        for i, agent in enumerate(agents):
            # Create agent-specific task description
            if agent.role == AgentRole.CODE:
                subtask = f"Implement the following: {task_description}"
            elif agent.role == AgentRole.TEST:
                subtask = f"Write tests for: {task_description}"
            elif agent.role == AgentRole.DEBUG:
                subtask = f"Debug and fix issues in: {task_description}"
            elif agent.role == AgentRole.REVIEW:
                subtask = f"Review code quality for: {task_description}"
            elif agent.role == AgentRole.RESEARCH:
                subtask = f"Research and document: {task_description}"
            else:
                subtask = task_description

            # Plan the subtask
            plan = await self.planner.plan_task(
                {"description": subtask, "workspace_path": workspace_path},
                {"workspace_path": workspace_path},
            )

            # Create agent task
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                agent_role=agent.role,
                description=subtask,
                steps=plan.steps if plan else [],
                dependencies=[agent_tasks[i - 1].task_id] if i > 0 else [],
            )
            agent_tasks.append(task)

        return agent_tasks

    async def _execute_sequential(
        self, workflow: WorkflowExecution, workspace_path: str, auto_approve: bool
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute agents one after another"""
        for task in workflow.agent_tasks:
            task.status = "in_progress"

            yield {
                "type": "agent_started",
                "agent": task.agent_role.value,
                "task_id": task.task_id,
                "description": task.description,
            }

            # Execute task
            executor = AgentExecutor()
            start_time = datetime.utcnow()

            try:
                async for update in executor.execute_task(
                    {"description": task.description, "workspace_path": workspace_path},
                    {"workspace_path": workspace_path},
                    auto_approve=auto_approve,
                ):
                    yield {
                        "type": "agent_progress",
                        "agent": task.agent_role.value,
                        "task_id": task.task_id,
                        "update": update,
                    }

                    # Store final result
                    if update.get("type") == "task_complete":
                        task.result = update.get("result")

                task.status = "completed"

                # Record execution
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.feedback_store.record_execution(
                    TaskExecution(
                        task_id=task.task_id,
                        agent_role=task.agent_role.value,
                        task_type="collaborative",
                        task_description=task.description,
                        outcome=TaskOutcome.SUCCESS,
                        duration_seconds=duration,
                        steps_completed=len(task.steps),
                        steps_total=len(task.steps),
                        tools_used=[],
                    )
                )

            except Exception as e:
                task.status = "failed"
                task.error = str(e)

                yield {
                    "type": "agent_failed",
                    "agent": task.agent_role.value,
                    "task_id": task.task_id,
                    "error": str(e),
                }

                # Record failure
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.feedback_store.record_execution(
                    TaskExecution(
                        task_id=task.task_id,
                        agent_role=task.agent_role.value,
                        task_type="collaborative",
                        task_description=task.description,
                        outcome=TaskOutcome.FAILURE,
                        duration_seconds=duration,
                        steps_completed=0,
                        steps_total=len(task.steps),
                        tools_used=[],
                        error_message=str(e),
                    )
                )

            yield {
                "type": "agent_completed",
                "agent": task.agent_role.value,
                "task_id": task.task_id,
                "status": task.status,
            }

    async def _execute_parallel(
        self, workflow: WorkflowExecution, workspace_path: str, auto_approve: bool
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute agents in parallel"""

        # Create tasks for all agents
        async def execute_agent_task(task: AgentTask):
            task.status = "in_progress"
            executor = AgentExecutor()
            start_time = datetime.utcnow()

            try:
                updates = []
                async for update in executor.execute_task(
                    {"description": task.description, "workspace_path": workspace_path},
                    {"workspace_path": workspace_path},
                    auto_approve=auto_approve,
                ):
                    updates.append(update)
                    if update.get("type") == "task_complete":
                        task.result = update.get("result")

                task.status = "completed"

                # Record execution
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.feedback_store.record_execution(
                    TaskExecution(
                        task_id=task.task_id,
                        agent_role=task.agent_role.value,
                        task_type="collaborative_parallel",
                        task_description=task.description,
                        outcome=TaskOutcome.SUCCESS,
                        duration_seconds=duration,
                        steps_completed=len(task.steps),
                        steps_total=len(task.steps),
                        tools_used=[],
                    )
                )

                return updates

            except Exception as e:
                task.status = "failed"
                task.error = str(e)

                duration = (datetime.utcnow() - start_time).total_seconds()
                self.feedback_store.record_execution(
                    TaskExecution(
                        task_id=task.task_id,
                        agent_role=task.agent_role.value,
                        task_type="collaborative_parallel",
                        task_description=task.description,
                        outcome=TaskOutcome.FAILURE,
                        duration_seconds=duration,
                        steps_completed=0,
                        steps_total=len(task.steps),
                        tools_used=[],
                        error_message=str(e),
                    )
                )

                return [{"type": "error", "error": str(e)}]

        # Execute all tasks in parallel
        results = await asyncio.gather(*[execute_agent_task(task) for task in workflow.agent_tasks])

        # Yield all updates
        for task_updates in results:
            for update in task_updates:
                yield update

    async def _execute_pipeline(
        self, workflow: WorkflowExecution, workspace_path: str, auto_approve: bool
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute agents in pipeline (output of one feeds into next)"""
        context = {"workspace_path": workspace_path}

        for task in workflow.agent_tasks:
            task.status = "in_progress"

            yield {"type": "agent_started", "agent": task.agent_role.value, "task_id": task.task_id}

            # Add previous agent's output to context
            executor = AgentExecutor()

            try:
                async for update in executor.execute_task(
                    {"description": task.description, "workspace_path": workspace_path},
                    context,
                    auto_approve=auto_approve,
                ):
                    yield update

                    if update.get("type") == "task_complete":
                        task.result = update.get("result")
                        # Add to context for next agent
                        context[f"{task.agent_role.value}_output"] = task.result

                task.status = "completed"

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                yield {"type": "agent_failed", "error": str(e)}

    async def _execute_collaborative(
        self, workflow: WorkflowExecution, workspace_path: str, auto_approve: bool
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute agents collaboratively (with inter-agent communication)"""
        # Similar to sequential but with message passing
        shared_context = {"workspace_path": workspace_path, "messages": []}

        for task in workflow.agent_tasks:
            task.status = "in_progress"

            executor = AgentExecutor()

            try:
                async for update in executor.execute_task(
                    {"description": task.description, "workspace_path": workspace_path},
                    shared_context,
                    auto_approve=auto_approve,
                ):
                    yield update

                    if update.get("type") == "task_complete":
                        task.result = update.get("result")
                        # Share result with other agents
                        shared_context[f"{task.agent_role.value}_result"] = task.result

                task.status = "completed"

            except Exception as e:
                task.status = "failed"
                task.error = str(e)


# Global instance
_coordinator: MultiAgentCoordinator | None = None


def get_coordinator() -> MultiAgentCoordinator:
    """Get or create global coordinator"""
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator
