"""
Context Sources

Provides context from different sources:
- WorkspaceSource: Files from workspace
- TerminalSource: Terminal output
"""

import pathlib
from collections.abc import Iterator
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class WorkspaceSource:
    """
    Extract context from workspace files.

    Reads code files and prepares them for indexing.
    """

    def __init__(self, workspace_path: str):
        """
        Initialize workspace source.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = pathlib.Path(workspace_path)

        # File extensions to index
        self.code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".swift",
            ".rs",
            ".go",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".rb",
            ".php",
            ".sh",
            ".zsh",
        }

        self.doc_extensions = {
            ".md",
            ".txt",
            ".rst",
        }

        # Patterns to ignore
        self.ignore_patterns = {
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            "venv",
            ".venv",
            "env",
            ".build",
            "build",
            "dist",
            "target",
            "__pycache__",
            ".pytest_cache",
            ".DS_Store",
            ".swiftpm",
        }

    def should_index(self, file_path: pathlib.Path) -> bool:
        """Check if file should be indexed"""
        # Check extension
        if file_path.suffix not in (self.code_extensions | self.doc_extensions):
            return False

        # Check ignore patterns
        for part in file_path.parts:
            if part in self.ignore_patterns or part.startswith("."):
                return False

        return True

    def iter_files(self) -> Iterator[tuple[str, str, dict[str, Any]]]:
        """
        Iterate over workspace files.

        Yields:
            (source_id, content, metadata) tuples
        """
        for file_path in self.workspace_path.rglob("*"):
            if not file_path.is_file():
                continue

            if not self.should_index(file_path):
                continue

            # Skip files larger than 100KB
            if file_path.stat().st_size > 100_000:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            # Generate source ID
            rel_path = file_path.relative_to(self.workspace_path)
            source_id = f"file:{rel_path}"

            # Metadata
            metadata = {
                "path": str(rel_path),
                "type": "code" if file_path.suffix in self.code_extensions else "doc",
                "language": self._detect_language(file_path),
                "size": file_path.stat().st_size,
            }

            yield (source_id, content, metadata)

    def _detect_language(self, file_path: pathlib.Path) -> str:
        """Detect programming language from extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascriptreact",
            ".tsx": "typescriptreact",
            ".swift": "swift",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".sh": "bash",
            ".zsh": "zsh",
        }
        return ext_map.get(file_path.suffix, "plaintext")


class TerminalSource:
    """
    Extract context from terminal output.

    Integrates with terminal context API.
    """

    def __init__(self):
        """Initialize terminal source"""
        pass

    def get_context(
        self, session_id: str = "main", lines: int = 100
    ) -> tuple[str, str, dict] | None:
        """
        Get terminal context for indexing.

        Args:
            session_id: Terminal session ID
            lines: Number of lines to retrieve

        Returns:
            (source_id, content, metadata) tuple or None
        """
        # Import here to avoid circular dependency
        try:
            from ...terminal_context_api import _session_metadata, _terminal_buffers

            if session_id not in _terminal_buffers:
                return None

            buffer = _terminal_buffers[session_id]
            if not buffer:
                return None

            # Get recent lines
            recent_items = list(buffer)[-lines:]

            # Format output
            output_lines = []
            for item in recent_items:
                line = item["line"]
                if item.get("command"):
                    output_lines.append(f"$ {item['command']}")
                output_lines.append(line)

            if not output_lines:
                return None

            content = "\n".join(output_lines)
            source_id = f"terminal:{session_id}"

            metadata = _session_metadata.get(session_id, {})
            metadata["type"] = "terminal"
            metadata["session_id"] = session_id

            return (source_id, content, metadata)

        except Exception as e:
            logger.error(f"Error fetching terminal context: {e}")
            return None
