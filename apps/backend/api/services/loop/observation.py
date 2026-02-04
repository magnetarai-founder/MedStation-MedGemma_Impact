"""
Observation Engine

Collects and analyzes execution observations.
Detects side effects, measures outcomes, and prepares data for reflection.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any

from ..agent.results import StepResult, StepResultType
from .models import Observation

logger = logging.getLogger(__name__)


class ObservationEngine:
    """
    Collects observations from action execution.

    Responsibilities:
    - Capture action results (success/failure, output, errors)
    - Detect side effects (file changes, test results)
    - Compute metrics (duration, tokens)
    - Prepare data for reflection
    """

    def __init__(self, workspace_root: str | None = None):
        """
        Initialize observation engine.

        Args:
            workspace_root: Root directory for detecting file changes
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()

        # Track file state for change detection
        self._file_states: dict[str, float] = {}  # path -> mtime
        self._snapshot_taken = False

    def take_snapshot(self) -> None:
        """
        Take a snapshot of current file states.

        Call this before executing an action to enable change detection.
        """
        self._file_states = {}
        try:
            for path in self.workspace_root.rglob("*"):
                if path.is_file() and not self._should_ignore(path):
                    try:
                        self._file_states[str(path)] = path.stat().st_mtime
                    except OSError:
                        pass
            self._snapshot_taken = True
        except Exception as e:
            logger.warning(f"Failed to take file snapshot: {e}")

    def observe(
        self,
        action_id: str,
        action_description: str,
        result: StepResult,
        start_time: float | None = None,
    ) -> Observation:
        """
        Create an observation from an action result.

        Args:
            action_id: ID of the executed action
            action_description: Description of what was done
            result: Result from executing the action
            start_time: When the action started (for duration)

        Returns:
            Observation object
        """
        # Calculate duration
        duration_ms = 0
        if start_time:
            duration_ms = int((time.time() - start_time) * 1000)

        # Determine success
        success = result.type in (StepResultType.SUCCESS, StepResultType.PARTIAL)

        # Get error if failed
        error = None
        if result.error:
            error = result.error.message

        # Detect file changes
        files_modified, files_created, files_deleted = self._detect_file_changes()

        # Also include changes from the result itself
        for change in result.files_changed:
            path = change.path
            if change.change_type == "created" and path not in files_created:
                files_created.append(path)
            elif change.change_type == "modified" and path not in files_modified:
                files_modified.append(path)
            elif change.change_type == "deleted" and path not in files_deleted:
                files_deleted.append(path)

        # Get commands run
        commands_run = [cmd.command for cmd in result.commands_run]

        return Observation(
            action_id=action_id,
            action_description=action_description,
            success=success,
            output=result.output,
            error=error,
            files_modified=files_modified,
            files_created=files_created,
            files_deleted=files_deleted,
            commands_run=commands_run,
            duration_ms=duration_ms,
        )

    def observe_raw(
        self,
        action_id: str,
        action_description: str,
        success: bool,
        output: Any = None,
        error: str | None = None,
        duration_ms: int = 0,
    ) -> Observation:
        """
        Create an observation from raw data (without StepResult).

        Useful for observing actions that don't use the result system.
        """
        files_modified, files_created, files_deleted = self._detect_file_changes()

        return Observation(
            action_id=action_id,
            action_description=action_description,
            success=success,
            output=output,
            error=error,
            files_modified=files_modified,
            files_created=files_created,
            files_deleted=files_deleted,
            duration_ms=duration_ms,
        )

    def _detect_file_changes(self) -> tuple[list[str], list[str], list[str]]:
        """
        Detect file changes since last snapshot.

        Returns:
            Tuple of (modified, created, deleted) file paths
        """
        if not self._snapshot_taken:
            return [], [], []

        modified = []
        created = []
        deleted = set(self._file_states.keys())

        try:
            for path in self.workspace_root.rglob("*"):
                if path.is_file() and not self._should_ignore(path):
                    path_str = str(path)
                    try:
                        current_mtime = path.stat().st_mtime
                    except OSError:
                        continue

                    if path_str in deleted:
                        deleted.remove(path_str)
                        # Check if modified
                        if current_mtime > self._file_states.get(path_str, 0):
                            modified.append(self._relative_path(path_str))
                    else:
                        # New file
                        created.append(self._relative_path(path_str))
        except Exception as e:
            logger.warning(f"Error detecting file changes: {e}")

        # Convert deleted to relative paths
        deleted_relative = [self._relative_path(p) for p in deleted]

        return modified, created, deleted_relative

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored for change detection"""
        ignore_patterns = {
            "__pycache__",
            ".git",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "venv",
            ".venv",
            ".env",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
        }

        path_str = str(path)
        for pattern in ignore_patterns:
            if pattern in path_str:
                return True

        return False

    def _relative_path(self, path: str) -> str:
        """Convert to relative path from workspace root"""
        try:
            return str(Path(path).relative_to(self.workspace_root))
        except ValueError:
            return path

    def analyze_test_output(self, output: str) -> dict[str, Any]:
        """
        Analyze test command output for pass/fail stats.

        Args:
            output: Test command stdout

        Returns:
            Dict with test analysis
        """
        analysis = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "framework": "unknown",
        }

        # Detect framework and parse accordingly
        if "pytest" in output or "PASSED" in output or "FAILED" in output:
            analysis["framework"] = "pytest"
            analysis.update(self._parse_pytest_output(output))
        elif "jest" in output.lower() or "Tests:" in output:
            analysis["framework"] = "jest"
            analysis.update(self._parse_jest_output(output))

        return analysis

    def _parse_pytest_output(self, output: str) -> dict[str, Any]:
        """Parse pytest output for stats"""
        import re

        result = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}

        # Look for summary line like "5 passed, 2 failed"
        summary_match = re.search(
            r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped", output
        )

        # Count individual results
        result["passed"] = len(re.findall(r"PASSED", output))
        result["failed"] = len(re.findall(r"FAILED", output))
        result["skipped"] = len(re.findall(r"SKIPPED", output))

        # Extract error messages
        error_matches = re.findall(r"(?:AssertionError|Error|Exception):\s*(.+)", output)
        result["errors"] = error_matches[:5]  # Limit to 5 errors

        return result

    def _parse_jest_output(self, output: str) -> dict[str, Any]:
        """Parse Jest output for stats"""
        import re

        result = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}

        # Look for "Tests: X passed, Y failed"
        tests_match = re.search(r"Tests:\s+(\d+)\s+passed,\s+(\d+)\s+failed", output)
        if tests_match:
            result["passed"] = int(tests_match.group(1))
            result["failed"] = int(tests_match.group(2))

        return result

    def summarize_observations(
        self, observations: list[Observation]
    ) -> dict[str, Any]:
        """
        Summarize a list of observations for context.

        Args:
            observations: List of observations to summarize

        Returns:
            Summary dict with stats and key findings
        """
        if not observations:
            return {"count": 0, "success_rate": 0.0, "total_duration_ms": 0}

        successes = sum(1 for o in observations if o.success)
        total_duration = sum(o.duration_ms for o in observations)
        all_files_modified = set()
        all_errors = []

        for obs in observations:
            all_files_modified.update(obs.files_modified)
            all_files_modified.update(obs.files_created)
            if obs.error:
                all_errors.append(obs.error)

        return {
            "count": len(observations),
            "successes": successes,
            "failures": len(observations) - successes,
            "success_rate": successes / len(observations),
            "total_duration_ms": total_duration,
            "files_touched": list(all_files_modified),
            "recent_errors": all_errors[-3:],  # Last 3 errors
        }
