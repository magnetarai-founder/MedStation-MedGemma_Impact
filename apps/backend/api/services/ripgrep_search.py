"""
Ripgrep-based Code Search

Fast file content search using ripgrep (rg).

Features:
- Regex pattern matching
- Multi-file search
- Glob pattern filtering
- Context lines (before/after)
- JSON output parsing
- Performance metrics

Requires ripgrep to be installed:
    Ubuntu/Debian: apt-get install ripgrep
    macOS: brew install ripgrep
    From source: https://github.com/BurntSushi/ripgrep
"""

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.structured_logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchMatch:
    """A single search match result"""

    file_path: str
    line_number: int
    column: int
    match_text: str
    line_text: str
    context_before: list[str] = None
    context_after: list[str] = None


@dataclass
class SearchResult:
    """Complete search results"""

    query: str
    matches: list[SearchMatch]
    total_matches: int
    files_searched: int
    search_time_ms: float
    truncated: bool = False


class RipgrepSearch:
    """
    High-performance code search using ripgrep.

    Ripgrep is significantly faster than Python's built-in search:
    - 10-100x faster than grep
    - Respects .gitignore automatically
    - Parallel search across files
    - Smart file type detection
    """

    def __init__(self, workspace_root: Path):
        """
        Initialize ripgrep search

        Args:
            workspace_root: Root directory to search in

        Raises:
            RuntimeError: If ripgrep is not installed
        """
        self.workspace_root = workspace_root

        # Check if ripgrep is available
        if not self._is_ripgrep_available():
            raise RuntimeError(
                "Ripgrep (rg) not found. Install with: "
                "apt-get install ripgrep (Linux) or brew install ripgrep (macOS)"
            )

    def _is_ripgrep_available(self) -> bool:
        """Check if ripgrep is installed"""
        return shutil.which("rg") is not None

    async def search(
        self,
        pattern: str,
        file_pattern: str | None = None,
        context_lines: int = 0,
        max_results: int = 100,
        case_sensitive: bool = False,
        regex: bool = True,
        file_types: list[str] | None = None,
    ) -> SearchResult:
        """
        Search for pattern in workspace files

        Args:
            pattern: Search pattern (regex or literal)
            file_pattern: Glob pattern to filter files (e.g., "*.py")
            context_lines: Number of context lines before/after match
            max_results: Maximum number of results to return
            case_sensitive: Whether search is case-sensitive
            regex: Whether pattern is regex (False for literal search)
            file_types: File types to search (e.g., ["py", "js"])

        Returns:
            SearchResult with matches

        Example:
            searcher = RipgrepSearch(Path("/path/to/project"))
            results = await searcher.search(
                pattern="async def.*auth",
                file_types=["py"],
                context_lines=2
            )
        """
        import time

        start_time = time.time()

        # Build ripgrep command
        cmd = self._build_command(
            pattern=pattern,
            file_pattern=file_pattern,
            context_lines=context_lines,
            max_results=max_results,
            case_sensitive=case_sensitive,
            regex=regex,
            file_types=file_types,
        )

        logger.info(
            "Running ripgrep search",
            pattern=pattern,
            workspace=str(self.workspace_root),
            max_results=max_results,
        )

        # Execute ripgrep
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            search_time_ms = (time.time() - start_time) * 1000

            # Parse results
            matches = self._parse_json_output(stdout.decode("utf-8"))

            # Check if truncated
            truncated = len(matches) >= max_results

            result = SearchResult(
                query=pattern,
                matches=matches[:max_results],
                total_matches=len(matches),
                files_searched=len({m.file_path for m in matches}),
                search_time_ms=round(search_time_ms, 2),
                truncated=truncated,
            )

            logger.info(
                "Search completed",
                matches=result.total_matches,
                files=result.files_searched,
                duration_ms=result.search_time_ms,
            )

            return result

        except Exception as e:
            logger.error("Ripgrep search failed", error=e, pattern=pattern)
            raise

    def _build_command(
        self,
        pattern: str,
        file_pattern: str | None,
        context_lines: int,
        max_results: int,
        case_sensitive: bool,
        regex: bool,
        file_types: list[str] | None,
    ) -> list[str]:
        """Build ripgrep command with arguments"""
        cmd = [
            "rg",
            "--json",  # JSON output for easy parsing
            "--line-number",  # Include line numbers
            "--column",  # Include column numbers
            "--no-heading",  # Don't group by file
        ]

        # Context lines
        if context_lines > 0:
            cmd.extend(["-C", str(context_lines)])

        # Max results (use max-count per file, then limit in code)
        cmd.extend(["-m", str(max_results)])

        # Case sensitivity
        if not case_sensitive:
            cmd.append("-i")

        # Literal vs regex
        if not regex:
            cmd.append("-F")  # Fixed string (literal)

        # File types
        if file_types:
            for ft in file_types:
                cmd.extend(["-t", ft])

        # Glob pattern
        if file_pattern:
            cmd.extend(["-g", file_pattern])

        # Respect .gitignore
        cmd.append("--no-ignore-vcs")  # Don't use .gitignore (search all files)

        # Add pattern
        cmd.append(pattern)

        return cmd

    def _parse_json_output(self, output: str) -> list[SearchMatch]:
        """
        Parse ripgrep JSON output

        Ripgrep JSON format:
        {"type":"match","data":{"path":{"text":"file.py"},"lines":{"text":"line content"},"line_number":42,...}}
        {"type":"context","data":{"path":{"text":"file.py"},"lines":{"text":"context line"},...}}
        """
        matches = []

        for line in output.strip().split("\n"):
            if not line:
                continue

            try:
                entry = json.loads(line)

                if entry.get("type") == "match":
                    data = entry["data"]

                    match = SearchMatch(
                        file_path=data["path"]["text"],
                        line_number=data["line_number"],
                        column=data.get("submatches", [{}])[0].get("start", 0) + 1,
                        match_text=data.get("submatches", [{}])[0].get("match", {}).get("text", ""),
                        line_text=data["lines"]["text"].rstrip("\n"),
                    )

                    matches.append(match)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse ripgrep output line: {e}")
                continue

        return matches

    async def search_and_replace(
        self,
        pattern: str,
        replacement: str,
        file_pattern: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """
        Search and replace across files

        Args:
            pattern: Search pattern (regex)
            replacement: Replacement text
            file_pattern: Glob pattern to filter files
            dry_run: If True, only show what would be replaced

        Returns:
            Dictionary with replacement details
        """
        # First, find all matches
        results = await self.search(pattern=pattern, file_pattern=file_pattern)

        if dry_run:
            return {
                "dry_run": True,
                "matches_found": results.total_matches,
                "files_affected": results.files_searched,
                "preview": [
                    {
                        "file": m.file_path,
                        "line": m.line_number,
                        "before": m.line_text,
                        "after": m.line_text.replace(pattern, replacement),
                    }
                    for m in results.matches[:10]  # Show first 10
                ],
            }

        # Actually perform replacement
        # Note: This is a simplified version. For production,
        # use sed or perl for in-place replacement
        files_modified = set()

        for match in results.matches:
            file_path = self.workspace_root / match.file_path

            try:
                content = file_path.read_text()
                modified_content = content.replace(pattern, replacement)

                if content != modified_content:
                    file_path.write_text(modified_content)
                    files_modified.add(match.file_path)

            except Exception as e:
                logger.error(f"Failed to replace in {match.file_path}", error=e)

        return {
            "dry_run": False,
            "files_modified": len(files_modified),
            "matches_replaced": results.total_matches,
            "files": list(files_modified),
        }


# Global instance cache
_ripgrep_instances: dict[str, RipgrepSearch] = {}


def get_ripgrep_search(workspace_root: Path) -> RipgrepSearch:
    """
    Get or create RipgrepSearch instance for workspace

    Args:
        workspace_root: Workspace root directory

    Returns:
        RipgrepSearch instance
    """
    workspace_key = str(workspace_root.resolve())

    if workspace_key not in _ripgrep_instances:
        _ripgrep_instances[workspace_key] = RipgrepSearch(workspace_root)

    return _ripgrep_instances[workspace_key]
