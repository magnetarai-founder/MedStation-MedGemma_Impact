#!/usr/bin/env python3
"""
Task Planner for Agent Execution

Breaks down complex tasks into executable steps:
- Analyzes user request
- Creates step-by-step plan
- Identifies required tools
- Estimates complexity
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """A single step in a task plan"""

    step_number: int
    description: str
    tool_name: str | None = None
    tool_params: dict[str, Any] | None = None
    expected_outcome: str | None = None
    completed: bool = False
    result: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    """A complete plan for executing a task"""

    task_description: str
    steps: list[TaskStep]
    estimated_complexity: str  # "simple", "medium", "complex"
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_description": self.task_description,
            "steps": [step.to_dict() for step in self.steps],
            "estimated_complexity": self.estimated_complexity,
            "requires_approval": self.requires_approval,
        }

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for step in self.steps if step.completed)

    @property
    def progress_percentage(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100


class TaskPlanner:
    """
    Plans multi-step tasks for agent execution

    Uses an LLM to analyze requests and create structured plans.
    """

    # Planning prompt template
    PLANNING_PROMPT = """You are a task planning assistant for a code editing agent.

Given a user request, create a detailed step-by-step plan for accomplishing the task.

Available tools:
- read_file: Read file contents
- write_file: Write/create a file
- edit_file: Edit existing file (replace text)
- list_files: List files in directory
- grep_code: Search for code patterns
- run_command: Execute shell commands (tests, linters, etc.)

User Request:
{request}

Workspace Context:
{context}

Create a JSON plan with this structure:
{{
  "task_description": "Brief summary of the task",
  "estimated_complexity": "simple|medium|complex",
  "requires_approval": true/false (true for destructive operations),
  "steps": [
    {{
      "step_number": 1,
      "description": "What this step does",
      "tool_name": "read_file",
      "tool_params": {{"file_path": "example.py"}},
      "expected_outcome": "What we expect to happen"
    }}
  ]
}}

Guidelines:
- Break down complex tasks into simple, atomic steps
- Start with reading/understanding before making changes
- Use grep_code to find relevant files if needed
- Always verify changes (e.g., run tests after code changes)
- Mark destructive operations (rm, delete) as requiring approval
- Be specific about file paths and parameters

Respond ONLY with valid JSON, no additional text."""

    def __init__(self, llm_client=None):
        """
        Initialize task planner

        Args:
            llm_client: LLM client for generating plans (Ollama, etc.)
        """
        self.llm_client = llm_client

    async def plan_task(
        self, request: str, workspace_context: dict[str, Any] | None = None
    ) -> TaskPlan:
        """
        Create a plan for executing a task

        Args:
            request: User's task request
            workspace_context: Context about the workspace (files, recent changes, etc.)

        Returns:
            TaskPlan object with steps
        """
        # Format context
        context_str = self._format_context(workspace_context or {})

        # Generate plan using LLM
        if self.llm_client:
            plan_json = await self._generate_plan_with_llm(request, context_str)
        else:
            # Fallback: create basic plan from request
            plan_json = self._create_basic_plan(request)

        # Parse and validate plan
        return self._parse_plan(plan_json, request)

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format workspace context for planning prompt"""
        parts = []

        if "recent_files" in context:
            parts.append(f"Recently modified files: {', '.join(context['recent_files'])}")

        if "workspace_structure" in context:
            parts.append(f"Workspace structure:\n{context['workspace_structure']}")

        if "current_errors" in context:
            parts.append(f"Current errors:\n{context['current_errors']}")

        return "\n".join(parts) if parts else "No additional context provided"

    async def _generate_plan_with_llm(self, request: str, context: str) -> dict[str, Any]:
        """Generate plan using LLM"""
        prompt = self.PLANNING_PROMPT.format(request=request, context=context)

        # Call LLM (assuming Ollama-style client)
        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}], format="json"
            )

            # Extract JSON from response
            content = response.get("message", {}).get("content", "{}")
            return json.loads(content)

        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            return self._create_basic_plan(request)

    def _create_basic_plan(self, request: str) -> dict[str, Any]:
        """Create a basic plan without LLM (fallback)"""
        # Simple heuristic-based planning
        request_lower = request.lower()

        steps = []
        step_num = 1

        # Common patterns
        if "fix" in request_lower or "error" in request_lower:
            steps.append(
                {
                    "step_number": step_num,
                    "description": "Search for error in codebase",
                    "tool_name": "grep_code",
                    "tool_params": {"pattern": "error", "context_lines": 5},
                    "expected_outcome": "Locate the source of the error",
                }
            )
            step_num += 1

        if "test" in request_lower:
            steps.append(
                {
                    "step_number": step_num,
                    "description": "Run tests",
                    "tool_name": "run_command",
                    "tool_params": {"command": "pytest"},
                    "expected_outcome": "Verify tests pass",
                }
            )
            step_num += 1

        # Default: just analyze the request
        if not steps:
            steps.append(
                {
                    "step_number": 1,
                    "description": f"Execute task: {request}",
                    "tool_name": None,
                    "tool_params": None,
                    "expected_outcome": "Task completed",
                }
            )

        return {
            "task_description": request,
            "estimated_complexity": "medium",
            "requires_approval": False,
            "steps": steps,
        }

    def _parse_plan(self, plan_json: dict[str, Any], original_request: str) -> TaskPlan:
        """Parse and validate plan JSON"""
        try:
            steps = [
                TaskStep(
                    step_number=s["step_number"],
                    description=s["description"],
                    tool_name=s.get("tool_name"),
                    tool_params=s.get("tool_params"),
                    expected_outcome=s.get("expected_outcome"),
                )
                for s in plan_json.get("steps", [])
            ]

            return TaskPlan(
                task_description=plan_json.get("task_description", original_request),
                steps=steps,
                estimated_complexity=plan_json.get("estimated_complexity", "medium"),
                requires_approval=plan_json.get("requires_approval", False),
            )

        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            # Return minimal plan
            return TaskPlan(
                task_description=original_request,
                steps=[
                    TaskStep(
                        step_number=1,
                        description=f"Execute: {original_request}",
                        expected_outcome="Task completed",
                    )
                ],
                estimated_complexity="unknown",
                requires_approval=True,  # Be safe
            )
