"""
Hierarchical Task Models

Defines the core data structures for recursive task planning.
Tasks can contain subtasks, forming a tree structure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class TaskPriority(Enum):
    """Task priority levels for execution ordering"""

    CRITICAL = 1  # Blocking issue, must be done first
    HIGH = 2  # Important, should be done soon
    MEDIUM = 3  # Normal priority
    LOW = 4  # Can be deferred
    OPTIONAL = 5  # Nice to have


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"  # Not started
    IN_PROGRESS = "in_progress"  # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed with error
    BLOCKED = "blocked"  # Waiting on dependency
    SKIPPED = "skipped"  # Skipped (precondition not met)
    CANCELLED = "cancelled"  # Cancelled by user/system


class TaskType(Enum):
    """Types of tasks for routing to appropriate handlers"""

    CODE_EDIT = "code_edit"  # File modifications
    CODE_READ = "code_read"  # File reading/analysis
    COMMAND = "command"  # Shell command execution
    SEARCH = "search"  # Codebase search
    TEST = "test"  # Test execution
    REVIEW = "review"  # Code review
    RESEARCH = "research"  # Documentation/research
    PLANNING = "planning"  # Meta-task for planning
    COMPOSITE = "composite"  # Container for subtasks


class ComplexityLevel(Enum):
    """Estimated task complexity"""

    TRIVIAL = "trivial"  # Single operation, <1 min
    SIMPLE = "simple"  # Few operations, 1-5 min
    MEDIUM = "medium"  # Multiple steps, 5-15 min
    COMPLEX = "complex"  # Many steps, may need decomposition
    VERY_COMPLEX = "very_complex"  # Requires significant decomposition


@dataclass
class TaskMetadata:
    """Metadata for tracking and debugging"""

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int = 0
    retry_count: int = 0
    max_retries: int = 3
    decomposition_depth: int = 0  # How deep in the tree
    source: str = "planner"  # What created this task


@dataclass
class HierarchicalTask:
    """
    A task that can contain subtasks, forming a tree structure.

    Key Features:
    - Recursive decomposition (children can have children)
    - Dependency tracking (must wait for other tasks)
    - Priority ordering for execution
    - Rich metadata for tracking and debugging
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""

    # Hierarchy
    parent_id: str | None = None
    children: list["HierarchicalTask"] = field(default_factory=list)

    # Dependencies (task IDs that must complete first)
    dependencies: list[str] = field(default_factory=list)

    # Classification
    task_type: TaskType = TaskType.COMPOSITE
    priority: TaskPriority = TaskPriority.MEDIUM
    complexity: ComplexityLevel = ComplexityLevel.MEDIUM

    # Execution details
    tool_name: str | None = None
    tool_params: dict[str, Any] | None = None
    expected_outcome: str | None = None

    # State
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None

    # Metadata
    metadata: TaskMetadata = field(default_factory=TaskMetadata)

    # Context
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set parent_id on children"""
        for child in self.children:
            child.parent_id = self.id

    # ===== Properties =====

    @property
    def is_atomic(self) -> bool:
        """Task is atomic if it has no children (leaf node)"""
        return len(self.children) == 0

    @property
    def is_composite(self) -> bool:
        """Task is composite if it has children"""
        return len(self.children) > 0

    @property
    def depth(self) -> int:
        """Calculate depth in task tree (0 for leaf nodes)"""
        if not self.children:
            return 0
        return 1 + max(child.depth for child in self.children)

    @property
    def total_subtasks(self) -> int:
        """Count all subtasks recursively"""
        count = len(self.children)
        for child in self.children:
            count += child.total_subtasks
        return count

    @property
    def completed_subtasks(self) -> int:
        """Count completed subtasks recursively"""
        count = sum(1 for c in self.children if c.status == TaskStatus.COMPLETED)
        for child in self.children:
            count += child.completed_subtasks
        return count

    @property
    def progress(self) -> float:
        """Calculate progress percentage (0.0 - 1.0)"""
        if self.is_atomic:
            return 1.0 if self.status == TaskStatus.COMPLETED else 0.0

        total = self.total_subtasks
        if total == 0:
            return 0.0

        return self.completed_subtasks / total

    @property
    def is_ready(self) -> bool:
        """Check if task is ready to execute (all dependencies satisfied)"""
        if self.status != TaskStatus.PENDING:
            return False

        # For now, just check status. DependencyGraph will handle actual checking.
        return True

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked by failed dependencies"""
        return self.status == TaskStatus.BLOCKED

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return (
            self.status == TaskStatus.FAILED
            and self.metadata.retry_count < self.metadata.max_retries
        )

    # ===== Methods =====

    def add_child(self, child: "HierarchicalTask") -> None:
        """Add a child task"""
        child.parent_id = self.id
        child.metadata.decomposition_depth = self.metadata.decomposition_depth + 1
        self.children.append(child)

    def add_dependency(self, task_id: str) -> None:
        """Add a dependency on another task"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)

    def mark_started(self) -> None:
        """Mark task as started"""
        self.status = TaskStatus.IN_PROGRESS
        self.metadata.started_at = datetime.utcnow().isoformat()
        self.metadata.updated_at = datetime.utcnow().isoformat()

    def mark_completed(self, result: Any = None) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.metadata.completed_at = datetime.utcnow().isoformat()
        self.metadata.updated_at = datetime.utcnow().isoformat()

        if self.metadata.started_at:
            start = datetime.fromisoformat(self.metadata.started_at)
            end = datetime.fromisoformat(self.metadata.completed_at)
            self.metadata.duration_ms = int((end - start).total_seconds() * 1000)

    def mark_failed(self, error: str) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.metadata.updated_at = datetime.utcnow().isoformat()

    def mark_blocked(self, reason: str = "") -> None:
        """Mark task as blocked"""
        self.status = TaskStatus.BLOCKED
        self.error = reason
        self.metadata.updated_at = datetime.utcnow().isoformat()

    def retry(self) -> bool:
        """Attempt to retry the task"""
        if not self.can_retry:
            return False

        self.status = TaskStatus.PENDING
        self.error = None
        self.result = None
        self.metadata.retry_count += 1
        self.metadata.updated_at = datetime.utcnow().isoformat()
        return True

    def get_leaf_tasks(self) -> list["HierarchicalTask"]:
        """Get all leaf (atomic) tasks in the tree"""
        if self.is_atomic:
            return [self]

        leaves = []
        for child in self.children:
            leaves.extend(child.get_leaf_tasks())
        return leaves

    def get_tasks_by_status(self, status: TaskStatus) -> list["HierarchicalTask"]:
        """Get all tasks with a specific status"""
        tasks = []
        if self.status == status:
            tasks.append(self)

        for child in self.children:
            tasks.extend(child.get_tasks_by_status(status))

        return tasks

    def find_task(self, task_id: str) -> "HierarchicalTask | None":
        """Find a task by ID in the tree"""
        if self.id == task_id:
            return self

        for child in self.children:
            found = child.find_task(task_id)
            if found:
                return found

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "description": self.description,
            "parent_id": self.parent_id,
            "children": [c.to_dict() for c in self.children],
            "dependencies": self.dependencies,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "complexity": self.complexity.value,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "expected_outcome": self.expected_outcome,
            "status": self.status.value,
            "error": self.error,
            "metadata": {
                "created_at": self.metadata.created_at,
                "updated_at": self.metadata.updated_at,
                "duration_ms": self.metadata.duration_ms,
                "retry_count": self.metadata.retry_count,
                "decomposition_depth": self.metadata.decomposition_depth,
            },
            "progress": self.progress,
            "total_subtasks": self.total_subtasks,
        }

    def to_flat_list(self) -> list["HierarchicalTask"]:
        """Flatten the tree to a list (depth-first)"""
        tasks = [self]
        for child in self.children:
            tasks.extend(child.to_flat_list())
        return tasks

    def __repr__(self) -> str:
        status_icon = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.BLOCKED: "🚫",
            TaskStatus.SKIPPED: "⏭️",
            TaskStatus.CANCELLED: "🚷",
        }
        icon = status_icon.get(self.status, "❓")
        children_str = f" [{len(self.children)} subtasks]" if self.children else ""
        return f"{icon} Task({self.id}): {self.description[:50]}{children_str}"


def create_task(
    description: str,
    task_type: TaskType = TaskType.COMPOSITE,
    priority: TaskPriority = TaskPriority.MEDIUM,
    tool_name: str | None = None,
    tool_params: dict[str, Any] | None = None,
    dependencies: list[str] | None = None,
) -> HierarchicalTask:
    """
    Factory function for creating tasks.

    Args:
        description: What the task does
        task_type: Type of task
        priority: Priority level
        tool_name: Tool to use (for atomic tasks)
        tool_params: Parameters for the tool
        dependencies: Task IDs this depends on

    Returns:
        New HierarchicalTask instance
    """
    return HierarchicalTask(
        description=description,
        task_type=task_type,
        priority=priority,
        tool_name=tool_name,
        tool_params=tool_params,
        dependencies=dependencies or [],
    )
