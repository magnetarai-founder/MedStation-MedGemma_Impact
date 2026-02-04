"""
Context Synchronizer

Ensures Aider sessions have the correct file context.
Synchronizes between agent's working memory and Aider's context.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    """Tracked state of a file"""

    path: str
    content_hash: str
    size: int
    modified_at: datetime
    in_aider_context: bool = False

    @classmethod
    def from_path(cls, file_path: str) -> "FileState | None":
        """Create FileState from file path"""
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                return None

            stat = path.stat()
            content = path.read_bytes()
            content_hash = hashlib.sha256(content).hexdigest()[:16]

            return cls(
                path=str(path.resolve()),
                content_hash=content_hash,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        except OSError as e:
            logger.warning(f"Cannot read file state for {file_path}: {e}")
            return None


@dataclass
class SyncState:
    """State of the synchronization"""

    workspace_root: str
    files: dict[str, FileState] = field(default_factory=dict)
    last_sync: datetime | None = None

    # Files that need attention
    modified_files: set[str] = field(default_factory=set)
    new_files: set[str] = field(default_factory=set)
    deleted_files: set[str] = field(default_factory=set)

    def has_changes(self) -> bool:
        """Check if there are any changes to sync"""
        return bool(self.modified_files or self.new_files or self.deleted_files)


class ContextSynchronizer:
    """
    Synchronizes file context between agent and Aider.

    Responsibilities:
    - Track which files are in Aider's context
    - Detect file modifications since last sync
    - Recommend files to add/remove from context
    - Handle context size limits
    """

    # Maximum files in context
    MAX_CONTEXT_FILES = 20

    # Maximum total context size (bytes)
    MAX_CONTEXT_SIZE = 500_000  # 500KB

    # File patterns to ignore
    IGNORE_PATTERNS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "*.pyc",
        "*.pyo",
        ".DS_Store",
    }

    def __init__(self, workspace_root: str):
        """
        Initialize synchronizer.

        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.state = SyncState(workspace_root=str(self.workspace_root))

    def scan_files(self, paths: list[str] | None = None) -> dict[str, FileState]:
        """
        Scan files and get their current state.

        Args:
            paths: Specific paths to scan, or None for all tracked files

        Returns:
            Dict of path -> FileState
        """
        result: dict[str, FileState] = {}

        if paths:
            for path in paths:
                state = FileState.from_path(path)
                if state:
                    result[state.path] = state
        else:
            # Scan all tracked files
            for path in self.state.files:
                state = FileState.from_path(path)
                if state:
                    result[state.path] = state

        return result

    def detect_changes(self) -> SyncState:
        """
        Detect changes since last sync.

        Returns:
            Updated SyncState with changes detected
        """
        # Scan current state
        current = self.scan_files()

        # Find modifications
        self.state.modified_files.clear()
        self.state.new_files.clear()
        self.state.deleted_files.clear()

        # Check for modified and deleted files
        for path, old_state in self.state.files.items():
            if path in current:
                new_state = current[path]
                if new_state.content_hash != old_state.content_hash:
                    self.state.modified_files.add(path)
            else:
                self.state.deleted_files.add(path)

        # Check for new files (if any were added to tracking)
        for path in current:
            if path not in self.state.files:
                self.state.new_files.add(path)

        return self.state

    def add_to_tracking(self, paths: list[str]) -> list[str]:
        """
        Add files to tracking.

        Args:
            paths: File paths to track

        Returns:
            List of paths successfully added
        """
        added = []

        for path in paths:
            if self._should_ignore(path):
                continue

            state = FileState.from_path(path)
            if state:
                self.state.files[state.path] = state
                added.append(state.path)

        return added

    def remove_from_tracking(self, paths: list[str]) -> None:
        """Remove files from tracking"""
        for path in paths:
            resolved = str(Path(path).resolve())
            self.state.files.pop(resolved, None)

    def mark_in_aider_context(self, paths: list[str], in_context: bool) -> None:
        """
        Mark files as in/out of Aider context.

        Args:
            paths: File paths
            in_context: Whether they're in context
        """
        for path in paths:
            resolved = str(Path(path).resolve())
            if resolved in self.state.files:
                self.state.files[resolved].in_aider_context = in_context

    def get_context_recommendations(
        self,
        task_description: str = "",
        related_files: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """
        Get recommendations for context management.

        Args:
            task_description: Description of current task
            related_files: Files related to the task

        Returns:
            Dict with 'add', 'remove', and 'keep' file lists
        """
        # Detect any changes first
        self.detect_changes()

        recommendations: dict[str, list[str]] = {
            "add": [],
            "remove": [],
            "keep": [],
        }

        # Files currently in Aider context
        in_context = [
            path for path, state in self.state.files.items()
            if state.in_aider_context
        ]

        # Add related files if specified
        if related_files:
            for path in related_files:
                resolved = str(Path(path).resolve())
                if resolved not in in_context:
                    # Check if it exists
                    if Path(resolved).exists():
                        recommendations["add"].append(resolved)

        # Add modified files that are in context (need refresh)
        for path in self.state.modified_files:
            if path in in_context:
                recommendations["keep"].append(path)

        # Remove deleted files
        for path in self.state.deleted_files:
            if path in in_context:
                recommendations["remove"].append(path)

        # Keep existing context files not deleted
        for path in in_context:
            if path not in self.state.deleted_files:
                if path not in recommendations["keep"]:
                    recommendations["keep"].append(path)

        # Check context limits
        total_add = len(recommendations["add"]) + len(recommendations["keep"])
        if total_add > self.MAX_CONTEXT_FILES:
            # Prioritize related files, then by recency
            excess = total_add - self.MAX_CONTEXT_FILES
            # Remove oldest files from keep list
            if len(recommendations["keep"]) > excess:
                to_remove = self._prioritize_removal(
                    recommendations["keep"], excess
                )
                for path in to_remove:
                    recommendations["keep"].remove(path)
                    recommendations["remove"].append(path)

        return recommendations

    def get_files_for_task(
        self,
        task_type: str,
        target_files: list[str] | None = None,
    ) -> list[str]:
        """
        Get relevant files for a task type.

        Args:
            task_type: Type of task (edit, analyze, fix, etc.)
            target_files: Explicit target files

        Returns:
            List of file paths to include in context
        """
        files: list[str] = []

        # Always include explicit targets
        if target_files:
            for path in target_files:
                resolved = str(Path(path).resolve())
                if Path(resolved).exists():
                    files.append(resolved)

        # For edit tasks, include related files
        if task_type in ("edit", "refactor", "fix"):
            for path in files[:]:
                related = self._find_related_files(path)
                files.extend(related)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_files: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        return unique_files[:self.MAX_CONTEXT_FILES]

    def sync_complete(self) -> None:
        """Mark sync as complete, update state"""
        self.state.last_sync = datetime.utcnow()
        self.state.modified_files.clear()
        self.state.new_files.clear()
        self.state.deleted_files.clear()

        # Update file states
        self.state.files = self.scan_files(list(self.state.files.keys()))

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        path_obj = Path(path)

        for pattern in self.IGNORE_PATTERNS:
            if pattern.startswith("*"):
                # Glob pattern
                if path_obj.match(pattern):
                    return True
            else:
                # Directory/file name
                if pattern in path_obj.parts:
                    return True

        return False

    def _find_related_files(self, file_path: str) -> list[str]:
        """
        Find files related to the given file.

        Uses heuristics like:
        - Same directory
        - Import relationships
        - Test files
        """
        related: list[str] = []
        path = Path(file_path)

        if not path.exists():
            return related

        # Same directory files with same extension
        if path.parent.exists():
            for sibling in path.parent.iterdir():
                if sibling.is_file() and sibling.suffix == path.suffix:
                    if sibling != path:
                        related.append(str(sibling.resolve()))

        # Test file relationship
        if path.stem.startswith("test_"):
            # Find the source file
            source_name = path.stem[5:] + path.suffix
            source_path = path.parent / source_name
            if source_path.exists():
                related.append(str(source_path.resolve()))
        else:
            # Find the test file
            test_name = f"test_{path.stem}{path.suffix}"
            test_path = path.parent / test_name
            if test_path.exists():
                related.append(str(test_path.resolve()))

        return related[:5]  # Limit related files

    def _prioritize_removal(
        self, paths: list[str], count: int
    ) -> list[str]:
        """
        Prioritize which files to remove from context.

        Removes files with oldest modification times first.
        """
        # Sort by modification time
        with_times: list[tuple[str, float]] = []
        for path in paths:
            try:
                mtime = os.path.getmtime(path)
                with_times.append((path, mtime))
            except OSError:
                with_times.append((path, 0))

        with_times.sort(key=lambda x: x[1])

        return [path for path, _ in with_times[:count]]

    def get_stats(self) -> dict[str, Any]:
        """Get synchronization statistics"""
        in_context = sum(
            1 for s in self.state.files.values() if s.in_aider_context
        )
        total_size = sum(s.size for s in self.state.files.values())

        return {
            "workspace": self.workspace_root,
            "tracked_files": len(self.state.files),
            "in_context": in_context,
            "total_size_bytes": total_size,
            "has_changes": self.state.has_changes(),
            "modified_count": len(self.state.modified_files),
            "new_count": len(self.state.new_files),
            "deleted_count": len(self.state.deleted_files),
            "last_sync": self.state.last_sync.isoformat() if self.state.last_sync else None,
        }
