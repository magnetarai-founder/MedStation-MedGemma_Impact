"""
Typed Result Models for Agent Execution

Provides structured result types for task step execution.
Replaces untyped `result: Any` with specific result categories.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepResultType(Enum):
    """
    Types of step execution results.

    SUCCESS: Step completed as expected
    FAILURE: Step failed with an error
    PARTIAL: Step partially completed (some actions succeeded)
    SKIPPED: Step was skipped (precondition not met)
    BLOCKED: Step blocked by another failure
    TIMEOUT: Step exceeded time limit
    """

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class ErrorCategory(Enum):
    """
    Categories of execution errors.

    Helps with automated error handling and recovery strategies.
    """

    TOOL_NOT_FOUND = "tool_not_found"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    LLM_ERROR = "llm_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """Structured error information"""

    category: ErrorCategory
    message: str
    details: str | None = None
    recoverable: bool = True
    suggested_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action,
        }


@dataclass
class FileChange:
    """Record of a file modification"""

    path: str
    change_type: str  # "created", "modified", "deleted"
    lines_added: int = 0
    lines_removed: int = 0
    diff_preview: str | None = None


@dataclass
class CommandOutput:
    """Output from a shell command execution"""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


@dataclass
class StepResult:
    """
    Result of executing a single task step.

    Replaces the untyped `result: Any` in TaskStep with structured data.
    """

    type: StepResultType
    output: Any  # Primary output (file content, command output, etc.)
    error: ErrorInfo | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Tracking for side effects
    files_changed: list[FileChange] = field(default_factory=list)
    commands_run: list[CommandOutput] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if step completed successfully (SUCCESS or PARTIAL)"""
        return self.type in (StepResultType.SUCCESS, StepResultType.PARTIAL)

    @property
    def failed(self) -> bool:
        """Check if step failed"""
        return self.type in (StepResultType.FAILURE, StepResultType.TIMEOUT)

    @property
    def is_recoverable(self) -> bool:
        """Check if this failure can potentially be recovered from"""
        if self.error is None:
            return True
        return self.error.recoverable

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "output": self._serialize_output(),
            "error": self.error.to_dict() if self.error else None,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "files_changed": [
                {
                    "path": f.path,
                    "change_type": f.change_type,
                    "lines_added": f.lines_added,
                    "lines_removed": f.lines_removed,
                }
                for f in self.files_changed
            ],
            "commands_run": [
                {
                    "command": c.command,
                    "exit_code": c.exit_code,
                    "duration_ms": c.duration_ms,
                }
                for c in self.commands_run
            ],
        }

    def _serialize_output(self) -> Any:
        """Serialize output for JSON (truncate large outputs)"""
        if isinstance(self.output, str) and len(self.output) > 5000:
            return self.output[:5000] + "... [truncated]"
        return self.output


# Factory functions for common result types


def success_result(
    output: Any,
    metadata: dict[str, Any] | None = None,
    duration_ms: int = 0,
    files_changed: list[FileChange] | None = None,
) -> StepResult:
    """Create a successful result"""
    return StepResult(
        type=StepResultType.SUCCESS,
        output=output,
        metadata=metadata or {},
        duration_ms=duration_ms,
        files_changed=files_changed or [],
    )


def failure_result(
    error_message: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    details: str | None = None,
    recoverable: bool = True,
    suggested_action: str | None = None,
) -> StepResult:
    """Create a failure result"""
    return StepResult(
        type=StepResultType.FAILURE,
        output=None,
        error=ErrorInfo(
            category=category,
            message=error_message,
            details=details,
            recoverable=recoverable,
            suggested_action=suggested_action,
        ),
    )


def partial_result(
    output: Any,
    error_message: str,
    files_changed: list[FileChange] | None = None,
) -> StepResult:
    """Create a partial success result (some actions completed)"""
    return StepResult(
        type=StepResultType.PARTIAL,
        output=output,
        error=ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message=error_message,
            recoverable=True,
        ),
        files_changed=files_changed or [],
    )


def skipped_result(reason: str) -> StepResult:
    """Create a skipped step result"""
    return StepResult(
        type=StepResultType.SKIPPED,
        output=None,
        metadata={"skip_reason": reason},
    )


def timeout_result(timeout_seconds: int, partial_output: Any = None) -> StepResult:
    """Create a timeout result"""
    return StepResult(
        type=StepResultType.TIMEOUT,
        output=partial_output,
        error=ErrorInfo(
            category=ErrorCategory.TIMEOUT_ERROR,
            message=f"Step timed out after {timeout_seconds} seconds",
            recoverable=True,
            suggested_action="Consider breaking this step into smaller parts",
        ),
    )


@dataclass
class TaskResult:
    """
    Aggregate result of executing an entire task (multiple steps).
    """

    task_id: str
    task_description: str
    step_results: list[StepResult]
    total_duration_ms: int = 0
    final_output: Any = None

    @property
    def success(self) -> bool:
        """Task succeeded if all steps succeeded"""
        return all(r.success for r in self.step_results)

    @property
    def failed(self) -> bool:
        """Task failed if any step failed (not skipped)"""
        return any(r.failed for r in self.step_results)

    @property
    def partial_success(self) -> bool:
        """Some steps succeeded, some failed"""
        successes = [r for r in self.step_results if r.success]
        failures = [r for r in self.step_results if r.failed]
        return len(successes) > 0 and len(failures) > 0

    @property
    def all_files_changed(self) -> list[FileChange]:
        """Aggregate all file changes across steps"""
        changes = []
        for result in self.step_results:
            changes.extend(result.files_changed)
        return changes

    @property
    def all_errors(self) -> list[ErrorInfo]:
        """Collect all errors from failed steps"""
        return [r.error for r in self.step_results if r.error is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "success": self.success,
            "step_results": [r.to_dict() for r in self.step_results],
            "total_duration_ms": self.total_duration_ms,
            "files_changed": [
                {"path": f.path, "change_type": f.change_type}
                for f in self.all_files_changed
            ],
            "errors": [e.to_dict() for e in self.all_errors],
        }
