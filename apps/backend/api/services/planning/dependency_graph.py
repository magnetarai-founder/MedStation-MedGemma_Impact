"""
Dependency Graph for Task Execution

Manages task dependencies as a DAG (Directed Acyclic Graph).
Provides topological ordering for parallel execution.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import HierarchicalTask, TaskStatus


class CyclicDependencyError(Exception):
    """Raised when a cycle is detected in task dependencies"""

    pass


@dataclass
class ExecutionWave:
    """
    A group of tasks that can execute in parallel.

    All tasks in a wave have their dependencies satisfied
    and can run concurrently.
    """

    wave_number: int
    tasks: list[HierarchicalTask]

    @property
    def task_ids(self) -> list[str]:
        return [t.id for t in self.tasks]

    @property
    def is_empty(self) -> bool:
        return len(self.tasks) == 0


class DependencyGraph:
    """
    DAG for managing task dependencies.

    Features:
    - Add/remove tasks and dependencies
    - Detect cycles
    - Get topological execution order
    - Find tasks ready for execution
    - Parallel wave grouping
    """

    def __init__(self):
        # Task ID -> Task object
        self.nodes: dict[str, HierarchicalTask] = {}

        # Task ID -> set of task IDs it depends on
        self.edges: dict[str, set[str]] = defaultdict(set)

        # Task ID -> set of task IDs that depend on it (reverse edges)
        self.reverse_edges: dict[str, set[str]] = defaultdict(set)

    def add_task(self, task: HierarchicalTask) -> None:
        """
        Add a task to the graph.

        Args:
            task: Task to add

        Raises:
            CyclicDependencyError: If adding this task creates a cycle
        """
        self.nodes[task.id] = task

        # Add edges for dependencies
        for dep_id in task.dependencies:
            self.add_dependency(task.id, dep_id)

        # Also add all children recursively
        for child in task.children:
            self.add_task(child)

    def add_dependency(self, task_id: str, depends_on_id: str) -> None:
        """
        Add a dependency edge: task_id depends on depends_on_id.

        Args:
            task_id: Task that has the dependency
            depends_on_id: Task that must complete first

        Raises:
            CyclicDependencyError: If this creates a cycle
        """
        # Check for self-dependency
        if task_id == depends_on_id:
            raise CyclicDependencyError(f"Task {task_id} cannot depend on itself")

        # Add edge
        self.edges[task_id].add(depends_on_id)
        self.reverse_edges[depends_on_id].add(task_id)

        # Check for cycle
        if self._has_cycle():
            # Remove the edge and raise
            self.edges[task_id].remove(depends_on_id)
            self.reverse_edges[depends_on_id].remove(task_id)
            raise CyclicDependencyError(
                f"Adding dependency {task_id} -> {depends_on_id} creates a cycle"
            )

    def remove_task(self, task_id: str) -> None:
        """Remove a task and its edges from the graph"""
        if task_id in self.nodes:
            del self.nodes[task_id]

        # Remove outgoing edges
        if task_id in self.edges:
            for dep_id in self.edges[task_id]:
                self.reverse_edges[dep_id].discard(task_id)
            del self.edges[task_id]

        # Remove incoming edges
        if task_id in self.reverse_edges:
            for dependent_id in self.reverse_edges[task_id]:
                self.edges[dependent_id].discard(task_id)
            del self.reverse_edges[task_id]

    def get_dependencies(self, task_id: str) -> set[str]:
        """Get IDs of tasks that this task depends on"""
        return self.edges.get(task_id, set())

    def get_dependents(self, task_id: str) -> set[str]:
        """Get IDs of tasks that depend on this task"""
        return self.reverse_edges.get(task_id, set())

    def are_dependencies_satisfied(self, task_id: str) -> bool:
        """
        Check if all dependencies of a task are completed.

        Args:
            task_id: Task to check

        Returns:
            True if all dependencies are completed
        """
        dependencies = self.get_dependencies(task_id)

        for dep_id in dependencies:
            if dep_id not in self.nodes:
                # Dependency doesn't exist - treat as not satisfied
                return False

            dep_task = self.nodes[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False

        return True

    def is_blocked_by_failure(self, task_id: str) -> bool:
        """
        Check if task is blocked by a failed dependency.

        Args:
            task_id: Task to check

        Returns:
            True if any dependency has failed
        """
        dependencies = self.get_dependencies(task_id)

        for dep_id in dependencies:
            if dep_id in self.nodes:
                dep_task = self.nodes[dep_id]
                if dep_task.status == TaskStatus.FAILED:
                    return True

        return False

    def get_ready_tasks(self) -> list[HierarchicalTask]:
        """
        Get all tasks that are ready to execute.

        A task is ready if:
        - Status is PENDING
        - All dependencies are COMPLETED
        - Not blocked by failed dependency

        Returns:
            List of tasks ready for execution
        """
        ready = []

        for task_id, task in self.nodes.items():
            if task.status != TaskStatus.PENDING:
                continue

            if self.is_blocked_by_failure(task_id):
                task.mark_blocked("Dependency failed")
                continue

            if self.are_dependencies_satisfied(task_id):
                ready.append(task)

        return ready

    def get_execution_order(self) -> list[list[str]]:
        """
        Get topological order grouped by parallel waves.

        Tasks in the same wave can execute in parallel.
        Each subsequent wave depends on the previous.

        Returns:
            List of waves, each wave is a list of task IDs
        """
        waves = []
        remaining = set(self.nodes.keys())
        completed = set()

        while remaining:
            # Find tasks with all dependencies in completed set
            wave = []
            for task_id in remaining:
                deps = self.get_dependencies(task_id)
                if deps.issubset(completed):
                    wave.append(task_id)

            if not wave:
                # No progress - there's a cycle or missing dependency
                raise CyclicDependencyError(
                    f"Cannot resolve execution order. Remaining: {remaining}"
                )

            waves.append(wave)
            completed.update(wave)
            remaining -= set(wave)

        return waves

    def get_execution_waves(self) -> list[ExecutionWave]:
        """
        Get execution waves with full task objects.

        Returns:
            List of ExecutionWave objects
        """
        order = self.get_execution_order()
        waves = []

        for i, task_ids in enumerate(order):
            tasks = [self.nodes[tid] for tid in task_ids if tid in self.nodes]
            waves.append(ExecutionWave(wave_number=i, tasks=tasks))

        return waves

    def get_critical_path(self) -> list[str]:
        """
        Find the critical path (longest dependency chain).

        Returns:
            List of task IDs on the critical path
        """
        # Calculate longest path to each node
        longest_path: dict[str, list[str]] = {}

        waves = self.get_execution_order()

        for wave in waves:
            for task_id in wave:
                deps = self.get_dependencies(task_id)

                if not deps:
                    longest_path[task_id] = [task_id]
                else:
                    # Find longest path among dependencies
                    max_path = []
                    for dep_id in deps:
                        if dep_id in longest_path:
                            if len(longest_path[dep_id]) > len(max_path):
                                max_path = longest_path[dep_id]

                    longest_path[task_id] = max_path + [task_id]

        # Find the overall longest path
        if not longest_path:
            return []

        return max(longest_path.values(), key=len)

    def _has_cycle(self) -> bool:
        """
        Detect if the graph has a cycle using DFS.

        Returns:
            True if a cycle exists
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.nodes}

        def dfs(node: str) -> bool:
            color[node] = GRAY

            for neighbor in self.edges.get(node, set()):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True  # Back edge = cycle
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True

            color[node] = BLACK
            return False

        for node in self.nodes:
            if color[node] == WHITE:
                if dfs(node):
                    return True

        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph for debugging"""
        return {
            "nodes": list(self.nodes.keys()),
            "edges": {k: list(v) for k, v in self.edges.items()},
            "execution_order": self.get_execution_order(),
        }

    def visualize(self) -> str:
        """
        Create a text visualization of the graph.

        Returns:
            ASCII art representation
        """
        lines = ["Dependency Graph:", "=" * 40]

        waves = self.get_execution_waves()

        for wave in waves:
            lines.append(f"\nWave {wave.wave_number}:")
            for task in wave.tasks:
                deps = self.get_dependencies(task.id)
                deps_str = f" <- [{', '.join(deps)}]" if deps else ""
                lines.append(f"  {task}{deps_str}")

        return "\n".join(lines)

    @classmethod
    def from_task_tree(cls, root: HierarchicalTask) -> "DependencyGraph":
        """
        Create a dependency graph from a task tree.

        Adds implicit dependencies: children depend on completion
        of tasks with lower indices (sequential by default).

        Args:
            root: Root task of the tree

        Returns:
            DependencyGraph with all tasks and dependencies
        """
        graph = cls()

        # Flatten tree
        all_tasks = root.to_flat_list()

        # Add all tasks
        for task in all_tasks:
            graph.nodes[task.id] = task

            # Add explicit dependencies
            for dep_id in task.dependencies:
                graph.edges[task.id].add(dep_id)
                graph.reverse_edges[dep_id].add(task.id)

        return graph
