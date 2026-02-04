#!/usr/bin/env python3
"""
Smart Context Selection for MagnetarCode

Automatically selects the most relevant context for user queries:
- Analyzes query intent and entities
- Uses RAG for semantic file retrieval
- Manages token budgets
- Prioritizes recent and active files
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    """A single context item (file, terminal output, etc.)"""

    source_type: str  # "file", "terminal", "memory"
    source_id: str  # file path or identifier
    content: str
    relevance_score: float  # 0.0 to 1.0
    token_estimate: int
    metadata: dict[str, Any] | None = None


@dataclass
class ContextBudget:
    """Token budget for context inclusion"""

    total_tokens: int = 8000  # Default budget
    system_tokens: int = 500  # Reserved for system messages
    user_message_tokens: int = 0  # User's message tokens

    @property
    def available_tokens(self) -> int:
        """Tokens available for context"""
        return self.total_tokens - self.system_tokens - self.user_message_tokens


class QueryAnalyzer:
    """Analyzes user queries to extract intent and entities"""

    # Common coding keywords and patterns
    FILE_PATTERNS = [
        r"(?:in |from |file |module |class |function )?([a-zA-Z0-9_/\-\.]+\.[a-zA-Z]{1,4})",
        r"([a-zA-Z0-9_/\-]+(?:\.py|\.js|\.ts|\.tsx|\.jsx|\.go|\.rs|\.java))",
    ]

    FUNCTION_PATTERNS = [
        r"function\s+([a-zA-Z0-9_]+)",
        r"def\s+([a-zA-Z0-9_]+)",
        r"class\s+([a-zA-Z0-9_]+)",
    ]

    ACTION_KEYWORDS = {
        "explain": {"type": "read", "priority": "high"},
        "show": {"type": "read", "priority": "high"},
        "what": {"type": "read", "priority": "high"},
        "how": {"type": "read", "priority": "medium"},
        "why": {"type": "read", "priority": "medium"},
        "fix": {"type": "write", "priority": "high"},
        "update": {"type": "write", "priority": "high"},
        "create": {"type": "write", "priority": "high"},
        "add": {"type": "write", "priority": "high"},
        "delete": {"type": "write", "priority": "medium"},
        "refactor": {"type": "write", "priority": "medium"},
        "debug": {"type": "debug", "priority": "high"},
        "error": {"type": "debug", "priority": "high"},
        "test": {"type": "test", "priority": "medium"},
    }

    def analyze(self, query: str) -> dict[str, Any]:
        """
        Analyze a user query to extract:
        - Intent (read, write, debug, test)
        - Mentioned files/paths
        - Mentioned functions/classes
        - Action keywords
        - Priority
        """
        query_lower = query.lower()

        # Extract file references
        files = []
        for pattern in self.FILE_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            files.extend(matches)

        # Extract function/class references
        entities = []
        for pattern in self.FUNCTION_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend(matches)

        # Detect intent from keywords
        intent = "general"
        priority = "medium"
        for keyword, info in self.ACTION_KEYWORDS.items():
            if keyword in query_lower:
                intent = info["type"]
                priority = info["priority"]
                break

        # Check for terminal/command context needs
        needs_terminal = any(
            word in query_lower
            for word in ["error", "output", "ran", "executed", "command", "terminal"]
        )

        return {
            "intent": intent,
            "priority": priority,
            "files": list(set(files)),
            "entities": list(set(entities)),
            "needs_terminal": needs_terminal,
            "original_query": query,
        }


class SmartContextSelector:
    """
    Intelligently selects context for LLM requests

    Uses a multi-stage approach:
    1. Query analysis - extract intent and entities
    2. RAG search - semantic file retrieval
    3. Priority ranking - score and rank results
    4. Budget management - fit within token limits
    """

    def __init__(self, context_engine=None):
        self.analyzer = QueryAnalyzer()
        self.context_engine = context_engine

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4

    def select_context(
        self,
        query: str,
        workspace_path: str | None = None,
        recent_files: list[str] | None = None,
        include_terminal: bool = False,
        terminal_output: str | None = None,
        budget: ContextBudget | None = None,
    ) -> list[ContextItem]:
        """
        Select the most relevant context for a query

        Args:
            query: User's question/request
            workspace_path: Path to workspace root
            recent_files: Recently active files
            include_terminal: Whether to include terminal output
            terminal_output: Recent terminal output
            budget: Token budget constraints

        Returns:
            List of ContextItem objects, ranked by relevance
        """
        if budget is None:
            budget = ContextBudget()

        # Analyze the query
        analysis = self.analyzer.analyze(query)
        logger.info(f"Query analysis: {analysis}")

        context_items = []

        # 1. Add explicitly mentioned files (highest priority)
        if analysis["files"] and workspace_path:
            for file_ref in analysis["files"]:
                file_path = Path(workspace_path) / file_ref
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        tokens = self.estimate_tokens(content)
                        context_items.append(
                            ContextItem(
                                source_type="file",
                                source_id=str(file_path),
                                content=content,
                                relevance_score=1.0,  # Explicitly mentioned = highest relevance
                                token_estimate=tokens,
                                metadata={"reason": "explicitly_mentioned"},
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")

        # 2. Use RAG to find semantically similar files
        if self.context_engine and workspace_path:
            try:
                # Search with higher top_k, we'll filter later
                rag_results = self.context_engine.search(
                    query=query, top_k=10, use_hybrid=True, filter_source=workspace_path
                )

                for result in rag_results:
                    # Skip if already included
                    if any(item.source_id == result["source_id"] for item in context_items):
                        continue

                    # Calculate relevance score
                    # RAG score is already 0-1, boost based on query analysis
                    relevance = result.get("score", 0.5)

                    # Boost if file extension matches common patterns in query
                    if any(ext in query.lower() for ext in [".py", ".js", ".ts", ".go"]):
                        if any(ext in result["source_id"] for ext in [".py", ".js", ".ts", ".go"]):
                            relevance *= 1.2

                    context_items.append(
                        ContextItem(
                            source_type="file",
                            source_id=result["source_id"],
                            content=result["content"],
                            relevance_score=min(relevance, 1.0),
                            token_estimate=self.estimate_tokens(result["content"]),
                            metadata={"reason": "rag_search", "rag_score": result.get("score")},
                        )
                    )
            except Exception as e:
                logger.error(f"RAG search failed: {e}")

        # 3. Add recent files if relevant
        if recent_files and workspace_path:
            for file_path in recent_files[:3]:  # Max 3 recent files
                full_path = Path(workspace_path) / file_path

                # Skip if already included
                if any(item.source_id == str(full_path) for item in context_items):
                    continue

                if full_path.exists() and full_path.is_file():
                    try:
                        content = full_path.read_text(encoding="utf-8")
                        tokens = self.estimate_tokens(content)

                        # Recent files get medium relevance
                        context_items.append(
                            ContextItem(
                                source_type="file",
                                source_id=str(full_path),
                                content=content,
                                relevance_score=0.6,
                                token_estimate=tokens,
                                metadata={"reason": "recent_file"},
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to read recent file {full_path}: {e}")

        # 4. Add terminal output if needed
        if include_terminal and terminal_output and analysis["needs_terminal"]:
            tokens = self.estimate_tokens(terminal_output)
            context_items.append(
                ContextItem(
                    source_type="terminal",
                    source_id="recent_terminal",
                    content=terminal_output,
                    relevance_score=0.8,  # High relevance if query mentions errors/output
                    token_estimate=tokens,
                    metadata={"reason": "error_context"},
                )
            )

        # 5. Sort by relevance score (descending)
        context_items.sort(key=lambda x: x.relevance_score, reverse=True)

        # 6. Apply budget constraints - fit as many high-relevance items as possible
        selected = []
        total_tokens = 0

        for item in context_items:
            if total_tokens + item.token_estimate <= budget.available_tokens:
                selected.append(item)
                total_tokens += item.token_estimate
            else:
                logger.debug(f"Skipping {item.source_id} - would exceed budget")

        logger.info(f"Selected {len(selected)} context items ({total_tokens} tokens)")
        return selected

    def format_context(self, items: list[ContextItem]) -> str:
        """Format context items into a readable string for the LLM"""
        sections = []

        for item in items:
            if item.source_type == "file":
                ext = Path(item.source_id).suffix.lstrip(".")
                sections.append(f"## File: {item.source_id}\n" f"```{ext}\n{item.content}\n```")
            elif item.source_type == "terminal":
                sections.append(f"## Recent Terminal Output\n" f"```\n{item.content}\n```")
            elif item.source_type == "memory":
                sections.append(f"## Relevant Memory\n" f"{item.content}")

        return "\n\n".join(sections)


# Global instance
_smart_context_selector: SmartContextSelector | None = None


def get_smart_context_selector(context_engine=None) -> SmartContextSelector:
    """Get or create global smart context selector"""
    global _smart_context_selector
    if _smart_context_selector is None:
        _smart_context_selector = SmartContextSelector(context_engine)
    return _smart_context_selector
