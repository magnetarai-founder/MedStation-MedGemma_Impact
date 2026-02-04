"""
Agentic Loop Data Models

Defines the core data structures for the Execute → Observe → Reflect → Decide loop.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class LoopPhase(Enum):
    """Current phase in the agentic loop"""

    PLANNING = "planning"  # Initial planning
    EXECUTE = "execute"  # Executing an action
    OBSERVE = "observe"  # Observing results
    REFLECT = "reflect"  # Analyzing what happened
    DECIDE = "decide"  # Deciding next action
    COMPLETE = "complete"  # Successfully finished
    ERROR = "error"  # Unrecoverable error
    ABORTED = "aborted"  # Aborted by user or system


class ReflectionAssessment(Enum):
    """Agent's assessment of progress"""

    ON_TRACK = "on_track"  # Making good progress
    NEEDS_ADJUSTMENT = "needs_adjustment"  # Minor course correction needed
    STUCK = "stuck"  # Not making progress
    ERROR = "error"  # Something went wrong
    COMPLETE = "complete"  # Goal achieved


class DecisionType(Enum):
    """Types of decisions the agent can make"""

    CONTINUE = "continue"  # Proceed with next planned action
    RETRY = "retry"  # Retry the failed action
    MODIFY = "modify"  # Modify the plan and continue
    SKIP = "skip"  # Skip current action, move to next
    ABORT = "abort"  # Stop execution entirely
    COMPLETE = "complete"  # Mark as successfully complete
    ASK_USER = "ask_user"  # Need user input to continue


@dataclass
class Observation:
    """
    Result observation from an action execution.

    Captures what happened when an action was executed,
    including success/failure, output, and side effects.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_id: str = ""  # The action/task that was executed
    action_description: str = ""

    # Result
    success: bool = True
    output: Any = None
    error: str | None = None

    # Side effects detected
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)

    # Metrics
    duration_ms: int = 0
    tokens_used: int = 0

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "action_description": self.action_description,
            "success": self.success,
            "output": self._truncate_output(self.output),
            "error": self.error,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "files_deleted": self.files_deleted,
            "commands_run": self.commands_run,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }

    def _truncate_output(self, output: Any, max_len: int = 1000) -> Any:
        """Truncate output for serialization"""
        if isinstance(output, str) and len(output) > max_len:
            return output[:max_len] + "... [truncated]"
        return output

    @property
    def summary(self) -> str:
        """Brief summary for logging"""
        status = "✓" if self.success else "✗"
        files = len(self.files_modified) + len(self.files_created)
        return f"{status} {self.action_description[:50]} ({files} files, {self.duration_ms}ms)"


@dataclass
class Reflection:
    """
    Agent's analysis of an observation.

    The agent reflects on what happened to understand:
    - Are we making progress toward the goal?
    - What went well or poorly?
    - What should we do next?
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    observation_id: str = ""

    # Assessment
    assessment: ReflectionAssessment = ReflectionAssessment.ON_TRACK
    confidence: float = 0.8  # 0.0 - 1.0

    # Analysis
    reasoning: str = ""  # Why this assessment
    what_went_well: list[str] = field(default_factory=list)
    what_went_wrong: list[str] = field(default_factory=list)

    # Recommendations
    suggested_actions: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)

    # Progress tracking
    progress_toward_goal: float = 0.0  # 0.0 - 1.0
    estimated_remaining_steps: int = 0

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observation_id": self.observation_id,
            "assessment": self.assessment.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "what_went_well": self.what_went_well,
            "what_went_wrong": self.what_went_wrong,
            "suggested_actions": self.suggested_actions,
            "lessons_learned": self.lessons_learned,
            "progress_toward_goal": self.progress_toward_goal,
            "estimated_remaining_steps": self.estimated_remaining_steps,
            "timestamp": self.timestamp,
        }

    @property
    def is_positive(self) -> bool:
        """Check if reflection indicates positive progress"""
        return self.assessment in (
            ReflectionAssessment.ON_TRACK,
            ReflectionAssessment.COMPLETE,
        )

    @property
    def needs_intervention(self) -> bool:
        """Check if human intervention might be needed"""
        return self.assessment == ReflectionAssessment.STUCK or (
            self.assessment == ReflectionAssessment.ERROR and self.confidence > 0.8
        )


@dataclass
class Decision:
    """
    Agent's decision about what to do next.

    Based on reflection, the agent decides:
    - Continue with the plan
    - Modify the plan
    - Retry a failed action
    - Abort and ask for help
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    reflection_id: str = ""

    # Decision
    decision_type: DecisionType = DecisionType.CONTINUE
    rationale: str = ""  # Why this decision

    # Next action (if CONTINUE or RETRY)
    next_action_id: str | None = None
    next_action_description: str | None = None

    # Plan modification (if MODIFY)
    modified_plan: dict[str, Any] | None = None
    removed_tasks: list[str] = field(default_factory=list)
    added_tasks: list[str] = field(default_factory=list)

    # User question (if ASK_USER)
    user_question: str | None = None

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "reflection_id": self.reflection_id,
            "decision_type": self.decision_type.value,
            "rationale": self.rationale,
            "next_action_id": self.next_action_id,
            "next_action_description": self.next_action_description,
            "modified_plan": self.modified_plan,
            "removed_tasks": self.removed_tasks,
            "added_tasks": self.added_tasks,
            "user_question": self.user_question,
            "timestamp": self.timestamp,
        }

    @property
    def should_continue(self) -> bool:
        """Check if execution should continue"""
        return self.decision_type in (
            DecisionType.CONTINUE,
            DecisionType.RETRY,
            DecisionType.MODIFY,
            DecisionType.SKIP,
        )


@dataclass
class LoopState:
    """
    Complete state of the agentic loop.

    Tracks the entire execution history for:
    - Debugging and analysis
    - Context for LLM decisions
    - Progress reporting
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Goal
    goal: str = ""
    original_plan_id: str = ""

    # Current state
    phase: LoopPhase = LoopPhase.PLANNING
    iteration: int = 0
    max_iterations: int = 20

    # History
    observations: list[Observation] = field(default_factory=list)
    reflections: list[Reflection] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)

    # Execution tracking
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    skipped_tasks: list[str] = field(default_factory=list)

    # Timing
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None
    total_duration_ms: int = 0

    # Final result
    success: bool = False
    final_output: Any = None
    final_error: str | None = None

    def add_observation(self, obs: Observation) -> None:
        """Add an observation to history"""
        self.observations.append(obs)

    def add_reflection(self, ref: Reflection) -> None:
        """Add a reflection to history"""
        self.reflections.append(ref)

    def add_decision(self, dec: Decision) -> None:
        """Add a decision to history"""
        self.decisions.append(dec)
        self.iteration += 1

    def get_recent_observations(self, n: int = 5) -> list[Observation]:
        """Get the N most recent observations"""
        return self.observations[-n:]

    def get_recent_reflections(self, n: int = 5) -> list[Reflection]:
        """Get the N most recent reflections"""
        return self.reflections[-n:]

    def get_last_decision(self) -> Decision | None:
        """Get the most recent decision"""
        return self.decisions[-1] if self.decisions else None

    @property
    def is_complete(self) -> bool:
        """Check if loop has terminated"""
        return self.phase in (LoopPhase.COMPLETE, LoopPhase.ERROR, LoopPhase.ABORTED)

    @property
    def should_continue(self) -> bool:
        """Check if loop should continue executing"""
        if self.is_complete:
            return False
        if self.iteration >= self.max_iterations:
            return False
        return True

    @property
    def progress(self) -> float:
        """Estimate overall progress (0.0 - 1.0)"""
        if not self.reflections:
            return 0.0
        last_reflection = self.reflections[-1]
        return last_reflection.progress_toward_goal

    def mark_complete(self, output: Any = None) -> None:
        """Mark the loop as successfully complete"""
        self.phase = LoopPhase.COMPLETE
        self.success = True
        self.final_output = output
        self.completed_at = datetime.utcnow().isoformat()

    def mark_error(self, error: str) -> None:
        """Mark the loop as failed with error"""
        self.phase = LoopPhase.ERROR
        self.success = False
        self.final_error = error
        self.completed_at = datetime.utcnow().isoformat()

    def mark_aborted(self, reason: str = "") -> None:
        """Mark the loop as aborted"""
        self.phase = LoopPhase.ABORTED
        self.success = False
        self.final_error = f"Aborted: {reason}" if reason else "Aborted by user"
        self.completed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "phase": self.phase.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "observations_count": len(self.observations),
            "reflections_count": len(self.reflections),
            "decisions_count": len(self.decisions),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "progress": self.progress,
        }

    def to_context_string(self, max_history: int = 5) -> str:
        """
        Format state as context string for LLM prompts.

        Args:
            max_history: Maximum history items to include

        Returns:
            Formatted context string
        """
        lines = [
            f"Goal: {self.goal}",
            f"Progress: {self.progress:.0%}",
            f"Iteration: {self.iteration}/{self.max_iterations}",
            "",
            "Recent History:",
        ]

        # Add recent observations
        for obs in self.get_recent_observations(max_history):
            lines.append(f"  - {obs.summary}")

        # Add recent reflections
        if self.reflections:
            last_ref = self.reflections[-1]
            lines.append(f"\nLast Assessment: {last_ref.assessment.value}")
            lines.append(f"Reasoning: {last_ref.reasoning[:200]}")

        return "\n".join(lines)
