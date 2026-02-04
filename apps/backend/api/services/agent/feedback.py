#!/usr/bin/env python3
"""
Agent Feedback and Learning System

Tracks agent performance, learns from user feedback, and improves over time:
- Performance metrics tracking
- User feedback collection
- Success/failure pattern learning
- Capability confidence adjustment

Uses the BaseRepository pattern for consistent database operations.
"""
# ruff: noqa: S608

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.services.db import BaseRepository, DatabaseConnection


class FeedbackType(Enum):
    """Types of feedback"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TaskOutcome(Enum):
    """Task execution outcomes"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    CANCELLED = "cancelled"


@dataclass
class TaskFeedback:
    """User feedback on a completed task"""

    task_id: str
    agent_role: str
    feedback_type: FeedbackType
    rating: int  # 1-5 stars
    comment: str | None = None
    task_type: str | None = None
    timestamp: str | None = None
    id: int | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class TaskExecution:
    """Record of a task execution"""

    task_id: str
    agent_role: str
    task_type: str
    task_description: str
    outcome: TaskOutcome
    duration_seconds: float
    steps_completed: int
    steps_total: int
    tools_used: list[str]
    error_message: str | None = None
    timestamp: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this execution"""
        if self.steps_total == 0:
            return 0.0
        return self.steps_completed / self.steps_total


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""

    agent_role: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    partial_tasks: int
    average_rating: float
    average_duration: float
    total_steps_completed: int
    most_used_tools: list[str]
    success_rate: float

    @classmethod
    def calculate(
        cls, executions: list[TaskExecution], feedbacks: list[TaskFeedback]
    ) -> "AgentMetrics":
        """Calculate metrics from execution history"""
        if not executions:
            return cls(
                agent_role="unknown",
                total_tasks=0,
                successful_tasks=0,
                failed_tasks=0,
                partial_tasks=0,
                average_rating=0.0,
                average_duration=0.0,
                total_steps_completed=0,
                most_used_tools=[],
                success_rate=0.0,
            )

        agent_role = executions[0].agent_role
        total = len(executions)
        successful = sum(1 for e in executions if e.outcome == TaskOutcome.SUCCESS)
        failed = sum(1 for e in executions if e.outcome == TaskOutcome.FAILURE)
        partial = sum(1 for e in executions if e.outcome == TaskOutcome.PARTIAL)

        # Calculate average rating from feedback
        ratings = [f.rating for f in feedbacks if f.agent_role == agent_role]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # Calculate average duration
        avg_duration = sum(e.duration_seconds for e in executions) / total

        # Total steps
        total_steps = sum(e.steps_completed for e in executions)

        # Most used tools
        tool_counts: dict[str, int] = {}
        for exec in executions:
            for tool in exec.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
        most_used = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_used_tools = [tool for tool, _ in most_used]

        return cls(
            agent_role=agent_role,
            total_tasks=total,
            successful_tasks=successful,
            failed_tasks=failed,
            partial_tasks=partial,
            average_rating=avg_rating,
            average_duration=avg_duration,
            total_steps_completed=total_steps,
            most_used_tools=most_used_tools,
            success_rate=successful / total if total > 0 else 0.0,
        )


class TaskExecutionRepository(BaseRepository[TaskExecution]):
    """Repository for task execution records."""

    @property
    def table_name(self) -> str:
        return "task_executions"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS task_executions (
                task_id TEXT PRIMARY KEY,
                agent_role TEXT NOT NULL,
                task_type TEXT NOT NULL,
                task_description TEXT,
                outcome TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                steps_completed INTEGER NOT NULL,
                steps_total INTEGER NOT NULL,
                tools_used TEXT NOT NULL,
                error_message TEXT,
                timestamp TEXT NOT NULL
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TaskExecution:
        return TaskExecution(
            task_id=row["task_id"],
            agent_role=row["agent_role"],
            task_type=row["task_type"],
            task_description=row["task_description"],
            outcome=TaskOutcome(row["outcome"]),
            duration_seconds=row["duration_seconds"],
            steps_completed=row["steps_completed"],
            steps_total=row["steps_total"],
            tools_used=json.loads(row["tools_used"]),
            error_message=row["error_message"],
            timestamp=row["timestamp"],
        )

    def _run_migrations(self):
        """Create indexes for performance."""
        self._create_index(["agent_role"], name="idx_executions_agent")
        self._create_index(["timestamp"], name="idx_executions_timestamp")

    def record(self, execution: TaskExecution):
        """Record a task execution (insert or replace)."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO task_executions
            (task_id, agent_role, task_type, task_description, outcome,
             duration_seconds, steps_completed, steps_total, tools_used,
             error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.task_id,
                execution.agent_role,
                execution.task_type,
                execution.task_description,
                execution.outcome.value,
                execution.duration_seconds,
                execution.steps_completed,
                execution.steps_total,
                json.dumps(execution.tools_used),
                execution.error_message,
                execution.timestamp,
            ),
        )
        self.db.get().commit()


class TaskFeedbackRepository(BaseRepository[TaskFeedback]):
    """Repository for task feedback records."""

    @property
    def table_name(self) -> str:
        return "task_feedback"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS task_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_role TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                task_type TEXT,
                timestamp TEXT NOT NULL
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TaskFeedback:
        return TaskFeedback(
            id=row["id"],
            task_id=row["task_id"],
            agent_role=row["agent_role"],
            feedback_type=FeedbackType(row["feedback_type"]),
            rating=row["rating"],
            comment=row["comment"],
            task_type=row["task_type"],
            timestamp=row["timestamp"],
        )

    def _run_migrations(self):
        """Create indexes for performance."""
        self._create_index(["task_id"], name="idx_feedback_task")
        self._create_index(["agent_role"], name="idx_feedback_agent")

    def record(self, feedback: TaskFeedback):
        """Record user feedback on a task."""
        self.insert(
            {
                "task_id": feedback.task_id,
                "agent_role": feedback.agent_role,
                "feedback_type": feedback.feedback_type.value,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "task_type": feedback.task_type,
                "timestamp": feedback.timestamp,
            }
        )


class FeedbackStore:
    """
    Persistent storage for agent feedback and performance data.

    Uses repositories for consistent database access with:
    - Thread-local connection pooling
    - WAL mode for concurrent reads/writes
    - Automatic migrations
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            data_dir = Path(os.path.expanduser("~/.magnetarcode/data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "agent_feedback.db"

        self._db = DatabaseConnection(db_path)
        self._executions = TaskExecutionRepository(self._db)
        self._feedback = TaskFeedbackRepository(self._db)

    def record_execution(self, execution: TaskExecution):
        """Record a task execution."""
        self._executions.record(execution)

    def record_feedback(self, feedback: TaskFeedback):
        """Record user feedback on a task."""
        self._feedback.record(feedback)

    def get_agent_executions(self, agent_role: str, limit: int = 100) -> list[TaskExecution]:
        """Get execution history for an agent."""
        return self._executions.find_where(
            "agent_role = ?",
            (agent_role,),
            order_by="timestamp DESC",
            limit=limit,
        )

    def get_agent_feedback(self, agent_role: str, limit: int = 100) -> list[TaskFeedback]:
        """Get feedback history for an agent."""
        return self._feedback.find_where(
            "agent_role = ?",
            (agent_role,),
            order_by="timestamp DESC",
            limit=limit,
        )

    def get_agent_metrics(self, agent_role: str) -> AgentMetrics:
        """Calculate performance metrics for an agent."""
        executions = self.get_agent_executions(agent_role)
        feedbacks = self.get_agent_feedback(agent_role)
        return AgentMetrics.calculate(executions, feedbacks)

    def get_task_patterns(self, agent_role: str, task_type: str | None = None) -> dict[str, Any]:
        """
        Analyze patterns in task execution.

        Returns:
            Dictionary with pattern analysis including:
            - Common failure points
            - Success patterns
            - Optimal tool combinations
        """
        executions = self.get_agent_executions(agent_role)

        if task_type:
            executions = [e for e in executions if e.task_type == task_type]

        if not executions:
            return {"success_patterns": [], "failure_patterns": [], "optimal_tools": []}

        # Success patterns
        successful = [e for e in executions if e.outcome == TaskOutcome.SUCCESS]
        success_tools: dict[str, int] = {}
        for exec in successful:
            key = ",".join(sorted(exec.tools_used))
            success_tools[key] = success_tools.get(key, 0) + 1

        # Failure patterns
        failed = [e for e in executions if e.outcome == TaskOutcome.FAILURE]
        failure_reasons: dict[str, int] = {}
        for exec in failed:
            if exec.error_message:
                # Extract error type
                error_type = (
                    exec.error_message.split(":")[0] if ":" in exec.error_message else "unknown"
                )
                failure_reasons[error_type] = failure_reasons.get(error_type, 0) + 1

        return {
            "success_patterns": sorted(
                [{"tools": k, "count": v} for k, v in success_tools.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:5],
            "failure_patterns": sorted(
                [{"error": k, "count": v} for k, v in failure_reasons.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:5],
            "optimal_tools": (
                sorted(success_tools.items(), key=lambda x: x[1], reverse=True)[0][0].split(",")
                if success_tools
                else []
            ),
        }


# Global instance
_feedback_store: FeedbackStore | None = None


def get_feedback_store() -> FeedbackStore:
    """Get or create global feedback store."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store
