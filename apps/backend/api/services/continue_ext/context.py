"""
Continue Context Providers

Concrete implementations of context providers for Continue.
Integrates MagnetarCode's context engine with Continue's context system.

SECURITY: Git commands use create_subprocess_exec with list arguments,
which is the safe subprocess pattern preventing shell injection.
"""

import logging
from pathlib import Path
from typing import Any

from .bridge import ContextItem, ContextItemType, ContextProvider

logger = logging.getLogger(__name__)


class CodebaseContextProvider(ContextProvider):
    """
    Provides codebase context using semantic search.

    Uses MagnetarCode's FAISS-based search to find relevant code.
    """

    def __init__(
        self,
        workspace_root: str | None = None,
        max_results: int = 5,
        max_tokens: int = 2000,
    ):
        """
        Initialize codebase context provider.

        Args:
            workspace_root: Default workspace directory
            max_results: Maximum context items to return
            max_tokens: Maximum total tokens across all items
        """
        self._workspace_root = workspace_root
        self._max_results = max_results
        self._max_tokens = max_tokens
        self._search_service = None

    @property
    def name(self) -> str:
        return "magnetar-codebase"

    @property
    def description(self) -> str:
        return "Search codebase for relevant code using semantic search"

    async def get_context(
        self,
        query: str,
        full_input: str,
        workspace_root: str | None = None,
        selected_code: str | None = None,
    ) -> list[ContextItem]:
        """
        Get relevant code context for query.

        Uses FAISS search to find semantically similar code.
        """
        workspace = workspace_root or self._workspace_root
        if not workspace:
            return []

        items: list[ContextItem] = []

        try:
            # Try to use FAISS search if available
            search_results = await self._search_codebase(query, workspace)

            for result in search_results[:self._max_results]:
                items.append(ContextItem(
                    name=result.get("file", "unknown"),
                    content=result.get("content", ""),
                    item_type=ContextItemType.CODE,
                    description=f"Relevant code from {result.get('file', 'codebase')}",
                    uri=f"file://{result.get('path', '')}",
                    line_start=result.get("line_start"),
                    line_end=result.get("line_end"),
                    language=self._detect_language(result.get("file", "")),
                    relevance_score=result.get("score", 0.5),
                ))

            # Trim to token budget
            items = self._trim_to_token_budget(items)

        except Exception as e:
            logger.warning(f"Codebase search failed: {e}")

        return items

    async def _search_codebase(
        self, query: str, workspace: str
    ) -> list[dict[str, Any]]:
        """
        Search codebase using available search service.

        Falls back to simple file search if FAISS unavailable.
        """
        # Try FAISS search
        try:
            from ..faiss_search import FAISSSearch

            search = FAISSSearch(workspace)
            if search.is_indexed():
                results = await search.search(query, top_k=self._max_results)
                return [
                    {
                        "file": r.file_path,
                        "path": str(Path(workspace) / r.file_path),
                        "content": r.content,
                        "line_start": r.line_start,
                        "line_end": r.line_end,
                        "score": r.score,
                    }
                    for r in results
                ]
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"FAISS search unavailable: {e}")

        # Fallback: simple grep-style search
        return await self._simple_search(query, workspace)

    async def _simple_search(
        self, query: str, workspace: str
    ) -> list[dict[str, Any]]:
        """Simple file content search fallback"""
        import re

        results: list[dict[str, Any]] = []
        workspace_path = Path(workspace)

        # Search patterns
        patterns = [
            re.compile(re.escape(word), re.IGNORECASE)
            for word in query.split()[:5]  # Limit to 5 words
        ]

        # File extensions to search
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}

        try:
            for file_path in workspace_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in extensions:
                    continue
                if any(p in str(file_path) for p in ["node_modules", ".git", "__pycache__", "venv"]):
                    continue

                try:
                    content = file_path.read_text(errors="ignore")
                    matches = sum(1 for p in patterns if p.search(content))

                    if matches > 0:
                        # Find relevant lines
                        lines = content.split("\n")
                        relevant_lines: list[tuple[int, str]] = []

                        for i, line in enumerate(lines):
                            if any(p.search(line) for p in patterns):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                snippet = "\n".join(lines[start:end])
                                relevant_lines.append((start + 1, snippet))
                                if len(relevant_lines) >= 2:
                                    break

                        if relevant_lines:
                            results.append({
                                "file": str(file_path.relative_to(workspace_path)),
                                "path": str(file_path),
                                "content": relevant_lines[0][1],
                                "line_start": relevant_lines[0][0],
                                "score": matches / len(patterns),
                            })

                except (OSError, UnicodeDecodeError):
                    continue

                if len(results) >= self._max_results * 2:
                    break

        except OSError as e:
            logger.warning(f"Simple search error: {e}")

        # Sort by score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:self._max_results]

    def _detect_language(self, file_path: str) -> str | None:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascriptreact",
            ".tsx": "typescriptreact",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
        }
        suffix = Path(file_path).suffix.lower()
        return ext_map.get(suffix)

    def _trim_to_token_budget(
        self, items: list[ContextItem]
    ) -> list[ContextItem]:
        """Trim items to fit within token budget"""
        total_tokens = 0
        result: list[ContextItem] = []

        for item in items:
            tokens = item.token_estimate
            if total_tokens + tokens <= self._max_tokens:
                result.append(item)
                total_tokens += tokens
            else:
                # Try to include partial content
                remaining = self._max_tokens - total_tokens
                if remaining > 100:
                    truncated_content = item.content[:remaining * 4]
                    item.content = truncated_content + "\n... [truncated]"
                    result.append(item)
                break

        return result


class ActiveFileContextProvider(ContextProvider):
    """
    Provides context from the currently active file.

    Includes the full file or relevant sections.
    """

    def __init__(self, max_lines: int = 200):
        self._max_lines = max_lines

    @property
    def name(self) -> str:
        return "magnetar-active-file"

    @property
    def description(self) -> str:
        return "Include context from the currently active file"

    async def get_context(
        self,
        query: str,
        full_input: str,
        workspace_root: str | None = None,
        selected_code: str | None = None,
    ) -> list[ContextItem]:
        """Get context from active file"""
        items: list[ContextItem] = []

        # If there's selected code, use that
        if selected_code:
            items.append(ContextItem(
                name="Selected Code",
                content=selected_code,
                item_type=ContextItemType.CODE,
                description="Currently selected code",
                relevance_score=1.0,
            ))

        return items


class GitHistoryContextProvider(ContextProvider):
    """
    Provides context from git history.

    Useful for understanding recent changes and context.

    SECURITY: Uses create_subprocess_exec with hardcoded git commands
    and list arguments - no user input in command construction.
    """

    def __init__(self, max_commits: int = 5):
        self._max_commits = max_commits

    @property
    def name(self) -> str:
        return "magnetar-git-history"

    @property
    def description(self) -> str:
        return "Include recent git commits for context"

    async def get_context(
        self,
        query: str,
        full_input: str,
        workspace_root: str | None = None,
        selected_code: str | None = None,
    ) -> list[ContextItem]:
        """Get context from git history"""
        if not workspace_root:
            return []

        items: list[ContextItem] = []

        try:
            import asyncio

            # SAFE: Using create_subprocess_exec with list args
            # All arguments are hardcoded strings, no user input
            process = await asyncio.create_subprocess_exec(
                "git", "log",
                f"-{self._max_commits}",
                "--oneline",
                "--no-decorate",
                cwd=workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await process.communicate()

            if process.returncode == 0:
                commits = stdout.decode("utf-8", errors="replace").strip()
                if commits:
                    items.append(ContextItem(
                        name="Recent Commits",
                        content=commits,
                        item_type=ContextItemType.CUSTOM,
                        description=f"Last {self._max_commits} git commits",
                        relevance_score=0.6,
                    ))

        except (OSError, FileNotFoundError):
            # Git not available
            pass

        return items


class ProblemsContextProvider(ContextProvider):
    """
    Provides context from linter/compiler problems.

    Helps the model understand current errors and warnings.
    """

    def __init__(self):
        self._problems: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "magnetar-problems"

    @property
    def description(self) -> str:
        return "Include current linter/compiler problems"

    def set_problems(self, problems: list[dict[str, Any]]) -> None:
        """Update the current problems list"""
        self._problems = problems

    async def get_context(
        self,
        query: str,
        full_input: str,
        workspace_root: str | None = None,
        selected_code: str | None = None,
    ) -> list[ContextItem]:
        """Get context from current problems"""
        if not self._problems:
            return []

        items: list[ContextItem] = []

        # Group problems by file
        by_file: dict[str, list[dict[str, Any]]] = {}
        for problem in self._problems:
            file_path = problem.get("file", "unknown")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(problem)

        for file_path, file_problems in by_file.items():
            problem_text = "\n".join(
                f"Line {p.get('line', '?')}: [{p.get('severity', 'error')}] {p.get('message', '')}"
                for p in file_problems[:5]
            )

            items.append(ContextItem(
                name=f"Problems: {file_path}",
                content=problem_text,
                item_type=ContextItemType.PROBLEM,
                description=f"{len(file_problems)} problem(s) in {file_path}",
                uri=f"file://{file_path}",
                relevance_score=0.9,
            ))

        return items


class ContextProviderRegistry:
    """
    Registry for context providers.

    Manages multiple providers and aggregates results.
    """

    def __init__(self):
        self._providers: dict[str, ContextProvider] = {}

    def register(self, provider: ContextProvider) -> None:
        """Register a context provider"""
        self._providers[provider.name] = provider
        logger.info(f"Registered context provider: {provider.name}")

    def unregister(self, name: str) -> None:
        """Unregister a context provider"""
        if name in self._providers:
            del self._providers[name]

    def get(self, name: str) -> ContextProvider | None:
        """Get a specific provider"""
        return self._providers.get(name)

    def list_providers(self) -> list[dict[str, str]]:
        """List all registered providers"""
        return [
            {"name": p.name, "description": p.description}
            for p in self._providers.values()
        ]

    async def get_context(
        self,
        query: str,
        full_input: str = "",
        workspace_root: str | None = None,
        selected_code: str | None = None,
        provider_names: list[str] | None = None,
    ) -> list[ContextItem]:
        """
        Get context from multiple providers.

        Args:
            query: The query to get context for
            full_input: Full conversation input
            workspace_root: Workspace directory
            selected_code: Currently selected code
            provider_names: Specific providers to use (all if None)

        Returns:
            Aggregated context items sorted by relevance
        """
        items: list[ContextItem] = []

        providers_to_use = (
            [self._providers[n] for n in provider_names if n in self._providers]
            if provider_names
            else list(self._providers.values())
        )

        for provider in providers_to_use:
            try:
                provider_items = await provider.get_context(
                    query=query,
                    full_input=full_input,
                    workspace_root=workspace_root,
                    selected_code=selected_code,
                )
                items.extend(provider_items)
            except Exception as e:
                logger.warning(f"Context provider {provider.name} failed: {e}")

        # Sort by relevance
        items.sort(key=lambda x: x.relevance_score, reverse=True)

        return items


def create_default_providers(
    workspace_root: str | None = None,
) -> ContextProviderRegistry:
    """
    Create registry with default providers.

    Args:
        workspace_root: Default workspace directory

    Returns:
        Configured registry with standard providers
    """
    registry = ContextProviderRegistry()

    registry.register(CodebaseContextProvider(workspace_root))
    registry.register(ActiveFileContextProvider())
    registry.register(GitHistoryContextProvider())
    registry.register(ProblemsContextProvider())

    return registry
