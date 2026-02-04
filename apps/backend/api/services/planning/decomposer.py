"""
Task Decomposer

Recursively breaks down complex tasks into smaller, executable subtasks.
Uses LLM for intelligent decomposition with heuristic fallbacks.
"""

import json
import logging
from typing import Any

from .models import (
    ComplexityLevel,
    HierarchicalTask,
    TaskPriority,
    TaskStatus,
    TaskType,
    create_task,
)

logger = logging.getLogger(__name__)


# Decomposition prompt template
DECOMPOSITION_PROMPT = """You are a task decomposition expert for a code editing agent.

Given a complex task, break it down into smaller, actionable subtasks.

Task to decompose:
{task_description}

Context:
{context}

Available tools:
- read_file: Read file contents
- write_file: Create/write a file
- edit_file: Edit existing file (search and replace)
- list_files: List files in directory
- grep_code: Search for patterns in code
- run_command: Execute shell commands

Guidelines:
1. Each subtask should be atomic (can be done with one tool)
2. Order subtasks logically (read before write, test after change)
3. Include verification steps (run tests, check output)
4. Maximum 7 subtasks (if more needed, mark for further decomposition)
5. Be specific about file paths and operations

Respond ONLY with valid JSON in this format:
{{
  "subtasks": [
    {{
      "description": "What this subtask does",
      "task_type": "code_edit|code_read|command|search|test|review",
      "tool_name": "read_file|write_file|edit_file|...",
      "tool_params": {{"param": "value"}},
      "priority": "critical|high|medium|low",
      "complexity": "trivial|simple|medium|complex",
      "depends_on": []
    }}
  ],
  "needs_further_decomposition": false
}}"""


class TaskDecomposer:
    """
    Decomposes complex tasks into subtasks recursively.

    Uses LLM for intelligent decomposition when available,
    falls back to heuristic decomposition otherwise.
    """

    # Maximum depth for recursive decomposition
    MAX_DEPTH = 4

    # Tasks with estimated steps > threshold get decomposed
    COMPLEXITY_THRESHOLD = 3

    # Maximum subtasks per decomposition (to avoid over-splitting)
    MAX_SUBTASKS = 7

    def __init__(self, llm_client=None):
        """
        Initialize task decomposer.

        Args:
            llm_client: LLM client for intelligent decomposition
        """
        self.llm_client = llm_client

    async def decompose(
        self,
        task: HierarchicalTask,
        context: dict[str, Any] | None = None,
        depth: int = 0,
    ) -> HierarchicalTask:
        """
        Recursively decompose a task into subtasks.

        Args:
            task: Task to decompose
            context: Workspace context (files, errors, etc.)
            depth: Current decomposition depth

        Returns:
            Task with children populated (if decomposed)
        """
        # Check depth limit
        if depth >= self.MAX_DEPTH:
            logger.debug(f"Max depth reached for task {task.id}")
            return task

        # Check if task needs decomposition
        if not self._needs_decomposition(task):
            logger.debug(f"Task {task.id} is atomic, skipping decomposition")
            return task

        # Decompose using LLM or heuristics
        if self.llm_client:
            subtasks = await self._decompose_with_llm(task, context or {})
        else:
            subtasks = self._decompose_with_heuristics(task)

        # Add subtasks as children
        for subtask in subtasks:
            task.add_child(subtask)

        # Recursively decompose children if needed
        for child in task.children:
            await self.decompose(child, context, depth + 1)

        return task

    def _needs_decomposition(self, task: HierarchicalTask) -> bool:
        """
        Determine if a task should be decomposed further.

        Args:
            task: Task to check

        Returns:
            True if task should be broken down
        """
        # Already has children
        if task.children:
            return False

        # Already atomic (has tool_name)
        if task.tool_name:
            return False

        # Check complexity
        if task.complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.SIMPLE):
            return False

        # Check description length as proxy for complexity
        if len(task.description) < 50:
            return False

        # Contains keywords suggesting multiple steps
        multi_step_keywords = [
            " and ",
            " then ",
            " after ",
            " before ",
            "first,",
            "finally",
            "multiple",
            "several",
            "all ",
        ]

        desc_lower = task.description.lower()
        if any(kw in desc_lower for kw in multi_step_keywords):
            return True

        return task.complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX)

    async def _decompose_with_llm(
        self, task: HierarchicalTask, context: dict[str, Any]
    ) -> list[HierarchicalTask]:
        """
        Use LLM to decompose task into subtasks.

        Args:
            task: Task to decompose
            context: Workspace context

        Returns:
            List of subtasks
        """
        # Format context
        context_str = self._format_context(context)

        prompt = DECOMPOSITION_PROMPT.format(
            task_description=task.description, context=context_str
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}], format="json"
            )

            content = response.get("message", {}).get("content", "{}")
            result = json.loads(content)

            subtasks = []
            for i, st in enumerate(result.get("subtasks", [])[:self.MAX_SUBTASKS]):
                subtask = self._parse_subtask(st, i)
                subtasks.append(subtask)

            logger.info(f"LLM decomposed task {task.id} into {len(subtasks)} subtasks")
            return subtasks

        except Exception as e:
            logger.warning(f"LLM decomposition failed: {e}, using heuristics")
            return self._decompose_with_heuristics(task)

    def _decompose_with_heuristics(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """
        Decompose task using pattern-based heuristics.

        Args:
            task: Task to decompose

        Returns:
            List of subtasks
        """
        subtasks = []
        desc_lower = task.description.lower()

        # Pattern: Implementation tasks
        if any(kw in desc_lower for kw in ["implement", "add", "create", "build"]):
            subtasks = self._decompose_implementation(task)

        # Pattern: Fix/debug tasks
        elif any(kw in desc_lower for kw in ["fix", "debug", "repair", "resolve"]):
            subtasks = self._decompose_fix(task)

        # Pattern: Refactoring tasks
        elif any(kw in desc_lower for kw in ["refactor", "improve", "optimize"]):
            subtasks = self._decompose_refactor(task)

        # Pattern: Testing tasks
        elif any(kw in desc_lower for kw in ["test", "verify", "validate"]):
            subtasks = self._decompose_test(task)

        # Default: generic decomposition
        else:
            subtasks = self._decompose_generic(task)

        logger.info(f"Heuristic decomposed task {task.id} into {len(subtasks)} subtasks")
        return subtasks

    def _decompose_implementation(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """Decompose an implementation task"""
        return [
            create_task(
                "Analyze existing code structure",
                TaskType.CODE_READ,
                TaskPriority.HIGH,
                tool_name="grep_code",
            ),
            create_task(
                "Read relevant files",
                TaskType.CODE_READ,
                TaskPriority.HIGH,
                tool_name="read_file",
            ),
            create_task(
                f"Implement: {task.description}",
                TaskType.CODE_EDIT,
                TaskPriority.HIGH,
            ),
            create_task(
                "Run tests to verify implementation",
                TaskType.TEST,
                TaskPriority.MEDIUM,
                tool_name="run_command",
                tool_params={"command": "pytest"},
            ),
        ]

    def _decompose_fix(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """Decompose a bug fix task"""
        return [
            create_task(
                "Search for error in codebase",
                TaskType.SEARCH,
                TaskPriority.HIGH,
                tool_name="grep_code",
            ),
            create_task(
                "Read files containing the error",
                TaskType.CODE_READ,
                TaskPriority.HIGH,
                tool_name="read_file",
            ),
            create_task(
                "Analyze root cause",
                TaskType.RESEARCH,
                TaskPriority.HIGH,
            ),
            create_task(
                f"Fix: {task.description}",
                TaskType.CODE_EDIT,
                TaskPriority.HIGH,
            ),
            create_task(
                "Run tests to verify fix",
                TaskType.TEST,
                TaskPriority.MEDIUM,
                tool_name="run_command",
            ),
        ]

    def _decompose_refactor(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """Decompose a refactoring task"""
        return [
            create_task(
                "Analyze current implementation",
                TaskType.CODE_READ,
                TaskPriority.HIGH,
                tool_name="read_file",
            ),
            create_task(
                "Identify areas for improvement",
                TaskType.REVIEW,
                TaskPriority.MEDIUM,
            ),
            create_task(
                f"Refactor: {task.description}",
                TaskType.CODE_EDIT,
                TaskPriority.HIGH,
            ),
            create_task(
                "Run tests to ensure no regression",
                TaskType.TEST,
                TaskPriority.HIGH,
                tool_name="run_command",
            ),
        ]

    def _decompose_test(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """Decompose a testing task"""
        return [
            create_task(
                "Read code to be tested",
                TaskType.CODE_READ,
                TaskPriority.HIGH,
                tool_name="read_file",
            ),
            create_task(
                "Identify test cases needed",
                TaskType.RESEARCH,
                TaskPriority.MEDIUM,
            ),
            create_task(
                f"Write tests: {task.description}",
                TaskType.CODE_EDIT,
                TaskPriority.HIGH,
            ),
            create_task(
                "Run tests and verify",
                TaskType.TEST,
                TaskPriority.HIGH,
                tool_name="run_command",
            ),
        ]

    def _decompose_generic(self, task: HierarchicalTask) -> list[HierarchicalTask]:
        """Generic decomposition for unknown task types"""
        return [
            create_task(
                "Understand the task context",
                TaskType.RESEARCH,
                TaskPriority.HIGH,
            ),
            create_task(
                f"Execute: {task.description}",
                TaskType.COMPOSITE,
                TaskPriority.MEDIUM,
            ),
            create_task(
                "Verify completion",
                TaskType.REVIEW,
                TaskPriority.LOW,
            ),
        ]

    def _parse_subtask(self, subtask_dict: dict[str, Any], index: int) -> HierarchicalTask:
        """Parse a subtask from LLM response"""
        # Map string types to enums
        task_type_map = {
            "code_edit": TaskType.CODE_EDIT,
            "code_read": TaskType.CODE_READ,
            "command": TaskType.COMMAND,
            "search": TaskType.SEARCH,
            "test": TaskType.TEST,
            "review": TaskType.REVIEW,
        }

        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }

        complexity_map = {
            "trivial": ComplexityLevel.TRIVIAL,
            "simple": ComplexityLevel.SIMPLE,
            "medium": ComplexityLevel.MEDIUM,
            "complex": ComplexityLevel.COMPLEX,
        }

        return HierarchicalTask(
            description=subtask_dict.get("description", f"Subtask {index + 1}"),
            task_type=task_type_map.get(
                subtask_dict.get("task_type", ""), TaskType.COMPOSITE
            ),
            priority=priority_map.get(
                subtask_dict.get("priority", ""), TaskPriority.MEDIUM
            ),
            complexity=complexity_map.get(
                subtask_dict.get("complexity", ""), ComplexityLevel.MEDIUM
            ),
            tool_name=subtask_dict.get("tool_name"),
            tool_params=subtask_dict.get("tool_params"),
            dependencies=subtask_dict.get("depends_on", []),
        )

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context dict for prompt"""
        parts = []

        if "recent_files" in context:
            parts.append(f"Recent files: {', '.join(context['recent_files'])}")

        if "workspace_structure" in context:
            parts.append(f"Structure:\n{context['workspace_structure']}")

        if "current_errors" in context:
            parts.append(f"Errors:\n{context['current_errors']}")

        if "relevant_code" in context:
            parts.append(f"Relevant code:\n{context['relevant_code']}")

        return "\n".join(parts) if parts else "No additional context"

    def estimate_complexity(self, description: str) -> ComplexityLevel:
        """
        Estimate task complexity from description.

        Args:
            description: Task description

        Returns:
            Estimated complexity level
        """
        desc_lower = description.lower()

        # Very complex indicators
        if any(
            kw in desc_lower
            for kw in [
                "refactor entire",
                "migrate all",
                "rewrite",
                "overhaul",
                "redesign",
            ]
        ):
            return ComplexityLevel.VERY_COMPLEX

        # Complex indicators
        if any(
            kw in desc_lower
            for kw in [
                "implement",
                "create new",
                "add feature",
                "integrate",
                "multiple files",
            ]
        ):
            return ComplexityLevel.COMPLEX

        # Medium indicators
        if any(
            kw in desc_lower
            for kw in ["fix", "update", "modify", "change", "add", "remove"]
        ):
            return ComplexityLevel.MEDIUM

        # Simple indicators
        if any(
            kw in desc_lower
            for kw in ["read", "check", "verify", "list", "show", "get"]
        ):
            return ComplexityLevel.SIMPLE

        return ComplexityLevel.MEDIUM
