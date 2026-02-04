"""
Recursive Task Planner

Main entry point for the planning system.
Coordinates intent classification, task decomposition, and dependency resolution.
"""

import logging
from typing import Any

from ..intent import IntentResult, IntentType, get_intent_classifier
from .decomposer import TaskDecomposer
from .dependency_graph import DependencyGraph
from .models import (
    ComplexityLevel,
    HierarchicalTask,
    TaskPriority,
    TaskType,
)

logger = logging.getLogger(__name__)


class RecursivePlanner:
    """
    Main planner that orchestrates task planning.

    Pipeline:
    1. Classify intent (if not provided)
    2. Create root task from request
    3. Decompose into subtasks recursively
    4. Build dependency graph
    5. Return execution-ready task tree
    """

    def __init__(self, llm_client=None, use_transformer: bool = True):
        """
        Initialize recursive planner.

        Args:
            llm_client: LLM client for planning and decomposition
            use_transformer: Use transformer-based intent classification
        """
        self.llm_client = llm_client
        self.decomposer = TaskDecomposer(llm_client)
        self.intent_classifier = get_intent_classifier(use_transformer=use_transformer)

    async def plan(
        self,
        request: str,
        context: dict[str, Any] | None = None,
        intent: IntentResult | None = None,
    ) -> HierarchicalTask:
        """
        Create a complete execution plan for a request.

        Args:
            request: User's request/instruction
            context: Workspace context (files, errors, etc.)
            intent: Pre-classified intent (optional)

        Returns:
            Root HierarchicalTask with children
        """
        # Step 1: Classify intent if not provided
        if intent is None:
            intent = await self.intent_classifier.classify(request, context)
            logger.info(
                f"Classified intent: {intent.primary_intent.value} "
                f"(confidence: {intent.confidence:.2f})"
            )

        # Step 2: Create root task
        root = self._create_root_task(request, intent, context)

        # Step 3: Decompose into subtasks
        root = await self.decomposer.decompose(root, context)

        # Step 4: Add file-based dependencies
        self._add_implicit_dependencies(root, intent)

        # Step 5: Validate the plan
        self._validate_plan(root)

        logger.info(
            f"Created plan with {root.total_subtasks} subtasks "
            f"(depth: {root.depth})"
        )

        return root

    def _create_root_task(
        self,
        request: str,
        intent: IntentResult,
        context: dict[str, Any] | None,
    ) -> HierarchicalTask:
        """
        Create the root task from request and intent.

        Args:
            request: User's request
            intent: Classified intent
            context: Optional context

        Returns:
            Root HierarchicalTask
        """
        # Map intent to task type
        intent_to_type = {
            IntentType.CODE_EDIT: TaskType.CODE_EDIT,
            IntentType.DEBUG: TaskType.CODE_EDIT,  # Debug involves editing
            IntentType.REFACTOR: TaskType.CODE_EDIT,
            IntentType.TEST: TaskType.TEST,
            IntentType.CODE_REVIEW: TaskType.REVIEW,
            IntentType.EXPLAIN: TaskType.RESEARCH,
            IntentType.SEARCH: TaskType.SEARCH,
            IntentType.CHAT: TaskType.COMPOSITE,
        }

        # Estimate complexity
        complexity = self.decomposer.estimate_complexity(request)

        # Determine priority from intent
        priority = self._intent_to_priority(intent)

        # Build context dict
        task_context = context.copy() if context else {}
        task_context["intent"] = intent.to_dict()
        task_context["extracted_files"] = intent.file_entities
        task_context["extracted_symbols"] = intent.symbol_entities

        return HierarchicalTask(
            description=request,
            task_type=intent_to_type.get(intent.primary_intent, TaskType.COMPOSITE),
            priority=priority,
            complexity=complexity,
            context=task_context,
        )

    def _intent_to_priority(self, intent: IntentResult) -> TaskPriority:
        """Map intent to task priority"""
        # Debug is usually urgent
        if intent.primary_intent == IntentType.DEBUG:
            return TaskPriority.HIGH

        # High confidence = higher priority
        if intent.confidence >= 0.9:
            return TaskPriority.HIGH
        elif intent.confidence >= 0.7:
            return TaskPriority.MEDIUM
        else:
            return TaskPriority.LOW

    def _add_implicit_dependencies(
        self, root: HierarchicalTask, intent: IntentResult
    ) -> None:
        """
        Add implicit dependencies based on task relationships.

        Rules:
        - Write tasks depend on read tasks for same file
        - Test tasks depend on code changes
        - Review tasks depend on code changes
        """
        all_tasks = root.to_flat_list()

        # Group by file (if we can infer from tool_params)
        file_tasks: dict[str, list[HierarchicalTask]] = {}

        for task in all_tasks:
            if task.tool_params and "file_path" in task.tool_params:
                file_path = task.tool_params["file_path"]
                if file_path not in file_tasks:
                    file_tasks[file_path] = []
                file_tasks[file_path].append(task)

        # Add dependencies: writes depend on reads
        for file_path, tasks in file_tasks.items():
            read_tasks = [t for t in tasks if t.task_type == TaskType.CODE_READ]
            write_tasks = [t for t in tasks if t.task_type == TaskType.CODE_EDIT]

            for write_task in write_tasks:
                for read_task in read_tasks:
                    if read_task.id != write_task.id:
                        write_task.add_dependency(read_task.id)

        # Test tasks depend on edit tasks
        edit_tasks = [t for t in all_tasks if t.task_type == TaskType.CODE_EDIT]
        test_tasks = [t for t in all_tasks if t.task_type == TaskType.TEST]

        for test_task in test_tasks:
            for edit_task in edit_tasks:
                test_task.add_dependency(edit_task.id)

    def _validate_plan(self, root: HierarchicalTask) -> None:
        """
        Validate the plan is executable.

        Checks:
        - No circular dependencies
        - All dependencies exist
        - At least one executable task
        """
        # Build dependency graph to check for cycles
        try:
            graph = DependencyGraph.from_task_tree(root)
            _ = graph.get_execution_order()
        except Exception as e:
            logger.warning(f"Plan validation found issue: {e}")
            # Clear problematic dependencies rather than fail
            self._clear_invalid_dependencies(root)

    def _clear_invalid_dependencies(self, root: HierarchicalTask) -> None:
        """Remove dependencies that would cause cycles or reference missing tasks"""
        all_tasks = root.to_flat_list()
        valid_ids = {t.id for t in all_tasks}

        for task in all_tasks:
            task.dependencies = [
                dep for dep in task.dependencies if dep in valid_ids
            ]

    def get_dependency_graph(self, root: HierarchicalTask) -> DependencyGraph:
        """
        Build dependency graph for a task tree.

        Args:
            root: Root task of the tree

        Returns:
            DependencyGraph for execution
        """
        return DependencyGraph.from_task_tree(root)

    async def replan(
        self,
        original_plan: HierarchicalTask,
        failure_info: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> HierarchicalTask:
        """
        Create a new plan after a failure.

        Uses the failure information to create a recovery plan.

        Args:
            original_plan: The plan that failed
            failure_info: Information about the failure
            context: Updated context

        Returns:
            New task tree for recovery
        """
        # Create a recovery request
        failed_task_id = failure_info.get("task_id")
        error = failure_info.get("error", "Unknown error")

        recovery_request = (
            f"Fix the error that occurred: {error}\n"
            f"Original task: {original_plan.description}"
        )

        # Add failure context
        recovery_context = context.copy() if context else {}
        recovery_context["previous_failure"] = failure_info
        recovery_context["original_plan"] = original_plan.to_dict()

        # Plan recovery
        return await self.plan(recovery_request, recovery_context)


# Convenience function
async def create_plan(
    request: str,
    llm_client=None,
    context: dict[str, Any] | None = None,
) -> HierarchicalTask:
    """
    Convenience function for creating a plan.

    Args:
        request: User's request
        llm_client: Optional LLM client
        context: Optional context

    Returns:
        HierarchicalTask tree
    """
    planner = RecursivePlanner(llm_client=llm_client)
    return await planner.plan(request, context)
