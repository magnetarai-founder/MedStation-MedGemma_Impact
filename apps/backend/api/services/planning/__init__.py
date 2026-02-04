"""
Recursive Task Planning System

Provides hierarchical task decomposition and dependency management.
Replaces flat task lists with nested subtask trees.

Usage:
    from api.services.planning import RecursivePlanner, HierarchicalTask

    planner = RecursivePlanner(llm_client)
    task_tree = await planner.plan("Implement user authentication with OAuth")

    # task_tree.children contains decomposed subtasks
    # Each subtask may have its own children (recursive)

    # Get execution order
    graph = planner.get_dependency_graph(task_tree)
    waves = graph.get_execution_waves()
    for wave in waves:
        # Tasks in same wave can run in parallel
        for task in wave.tasks:
            print(f"  {task}")
"""

from .decomposer import TaskDecomposer
from .dependency_graph import DependencyGraph, ExecutionWave
from .models import (
    ComplexityLevel,
    HierarchicalTask,
    TaskMetadata,
    TaskPriority,
    TaskStatus,
    TaskType,
    create_task,
)
from .recursive_planner import RecursivePlanner, create_plan

__all__ = [
    # Core models
    "HierarchicalTask",
    "TaskPriority",
    "TaskStatus",
    "TaskType",
    "TaskMetadata",
    "ComplexityLevel",
    "create_task",
    # Decomposition
    "TaskDecomposer",
    # Graph
    "DependencyGraph",
    "ExecutionWave",
    # Planner
    "RecursivePlanner",
    "create_plan",
]
