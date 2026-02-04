#!/usr/bin/env python3
"""
Smart Context Window Optimizer

Optimizes context window usage by:
- Tracking token counts
- Prioritizing relevant content
- Intelligent truncation and summarization
- Dynamic context allocation
- Caching and reuse of context
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


# Token estimation (approximate - tiktoken would be more accurate but requires dependency)
def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token for English.
    For code, tends to be ~3 characters per token.
    """
    if not text:
        return 0

    # Code tends to tokenize shorter
    code_patterns = [
        r"def\s+\w+",
        r"class\s+\w+",
        r"function\s+\w+",
        r"import\s+",
        r"from\s+\w+\s+import",
    ]
    is_code = any(re.search(pattern, text) for pattern in code_patterns)

    chars_per_token = 3.0 if is_code else 4.0
    return int(len(text) / chars_per_token)


class ContextPriority(Enum):
    """Priority levels for context items."""

    CRITICAL = 5  # System prompts, essential instructions
    HIGH = 4  # Current file, direct references
    MEDIUM = 3  # Related files, recent history
    LOW = 2  # Background context
    OPTIONAL = 1  # Nice to have


class ContentType(Enum):
    """Types of content that can go in context."""

    SYSTEM_PROMPT = "system_prompt"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    FILE_CONTENT = "file_content"
    SEARCH_RESULT = "search_result"
    TOOL_OUTPUT = "tool_output"
    SUMMARY = "summary"
    KNOWLEDGE = "knowledge"


@dataclass
class ContextItem:
    """An item that can be included in the context window."""

    content: str
    content_type: ContentType
    priority: ContextPriority
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str | None = None  # File path, message ID, etc.
    timestamp: datetime | None = None

    def __post_init__(self):
        """Estimate tokens if not provided."""
        if self.tokens == 0:
            self.tokens = estimate_tokens(self.content)

    def truncate(self, max_tokens: int) -> "ContextItem":
        """Create truncated version of this item."""
        if self.tokens <= max_tokens:
            return self

        # Estimate characters to keep
        chars_to_keep = int(max_tokens * 3.5)  # Conservative estimate

        truncated_content = self.content[:chars_to_keep] + "\n...[truncated]..."

        return ContextItem(
            content=truncated_content,
            content_type=self.content_type,
            priority=self.priority,
            tokens=estimate_tokens(truncated_content),
            metadata={**self.metadata, "truncated": True, "original_tokens": self.tokens},
            source=self.source,
            timestamp=self.timestamp,
        )


@dataclass
class ContextBudget:
    """Token budget for different context sections."""

    total: int
    system: int  # System prompts and instructions
    history: int  # Conversation history
    files: int  # File contents
    search: int  # Search results and references
    tools: int  # Tool outputs
    reserve: int  # Buffer for response

    @classmethod
    def for_model(cls, model: str) -> "ContextBudget":
        """Get recommended budget for a model."""
        # Default context sizes (conservative)
        model_contexts = {
            "qwen2.5-coder": 32000,
            "deepseek-coder": 16000,
            "codellama": 16000,
            "llama3": 8000,
            "mistral": 8000,
            "default": 8000,
        }

        # Find matching model
        total = model_contexts["default"]
        for key, value in model_contexts.items():
            if key in model.lower():
                total = value
                break

        # Allocate budget (percentages)
        return cls(
            total=total,
            system=int(total * 0.10),  # 10%
            history=int(total * 0.25),  # 25%
            files=int(total * 0.30),  # 30%
            search=int(total * 0.15),  # 15%
            tools=int(total * 0.10),  # 10%
            reserve=int(total * 0.10),  # 10% buffer
        )


@dataclass
class OptimizedContext:
    """Result of context optimization."""

    items: list[ContextItem]
    total_tokens: int
    budget: ContextBudget
    dropped_items: list[tuple[ContextItem, str]]  # (item, reason)

    def to_messages(self) -> list[dict[str, str]]:
        """Convert to message list for LLM."""
        messages = []

        for item in self.items:
            if item.content_type == ContentType.SYSTEM_PROMPT:
                messages.append({"role": "system", "content": item.content})
            elif item.content_type == ContentType.USER_MESSAGE:
                messages.append({"role": "user", "content": item.content})
            elif item.content_type == ContentType.ASSISTANT_MESSAGE:
                messages.append({"role": "assistant", "content": item.content})
            else:
                # Inject as system context
                messages.append({"role": "system", "content": item.content})

        return messages

    def get_stats(self) -> dict[str, Any]:
        """Get optimization statistics."""
        by_type = {}
        for item in self.items:
            type_name = item.content_type.value
            if type_name not in by_type:
                by_type[type_name] = {"count": 0, "tokens": 0}
            by_type[type_name]["count"] += 1
            by_type[type_name]["tokens"] += item.tokens

        return {
            "total_tokens": self.total_tokens,
            "budget_total": self.budget.total,
            "utilization": round(self.total_tokens / self.budget.total * 100, 1),
            "items_included": len(self.items),
            "items_dropped": len(self.dropped_items),
            "by_type": by_type,
        }


class ContextOptimizer:
    """
    Optimizes context window usage for LLM calls.

    Features:
    - Priority-based item selection
    - Token budget management
    - Intelligent truncation
    - Relevance scoring
    - Context caching
    """

    def __init__(
        self,
        model: str = "default",
        custom_budget: ContextBudget | None = None,
    ):
        """
        Initialize optimizer.

        Args:
            model: Model name for budget estimation
            custom_budget: Custom budget override
        """
        self.model = model
        self.budget = custom_budget or ContextBudget.for_model(model)

        # Simple cache for optimized contexts
        self._cache: dict[str, tuple[OptimizedContext, datetime]] = {}
        self._cache_ttl_seconds = 60  # 1 minute cache

    def _cache_key(self, items: list[ContextItem]) -> str:
        """Generate cache key for items."""
        content = "|".join(f"{item.source}:{item.tokens}" for item in items)
        return hashlib.md5(content.encode()).hexdigest()

    def optimize(
        self,
        items: list[ContextItem],
        query: str | None = None,
    ) -> OptimizedContext:
        """
        Optimize context items to fit within budget.

        Args:
            items: List of context items to optimize
            query: Optional query for relevance scoring

        Returns:
            OptimizedContext with selected items
        """
        # Check cache
        cache_key = self._cache_key(items)
        if cache_key in self._cache:
            cached, cached_at = self._cache[cache_key]
            age = (datetime.utcnow() - cached_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return cached

        # Score and sort items
        scored_items = self._score_items(items, query)

        # Select items within budget
        selected, dropped = self._select_items(scored_items)

        # Build result
        result = OptimizedContext(
            items=selected,
            total_tokens=sum(item.tokens for item in selected),
            budget=self.budget,
            dropped_items=dropped,
        )

        # Cache result
        self._cache[cache_key] = (result, datetime.utcnow())

        return result

    def _score_items(
        self,
        items: list[ContextItem],
        query: str | None = None,
    ) -> list[tuple[ContextItem, float]]:
        """
        Score items by relevance and priority.

        Returns list of (item, score) tuples, sorted by score descending.
        """
        scored = []

        query_terms = set(query.lower().split()) if query else set()

        for item in items:
            # Base score from priority
            score = item.priority.value * 10

            # Recency bonus (if timestamp available)
            if item.timestamp:
                age_minutes = (datetime.utcnow() - item.timestamp).total_seconds() / 60
                recency_bonus = max(0, 5 - (age_minutes / 10))  # Decays over time
                score += recency_bonus

            # Query relevance bonus
            if query_terms and item.content:
                content_terms = set(item.content.lower().split())
                overlap = len(query_terms & content_terms)
                relevance_bonus = min(overlap * 2, 10)  # Cap at 10
                score += relevance_bonus

            # Content type bonuses
            if item.content_type == ContentType.SYSTEM_PROMPT:
                score += 20  # System prompts always important
            elif item.content_type == ContentType.USER_MESSAGE:
                score += 5  # User messages are important

            scored.append((item, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _select_items(
        self,
        scored_items: list[tuple[ContextItem, float]],
    ) -> tuple[list[ContextItem], list[tuple[ContextItem, str]]]:
        """
        Select items that fit within budget.

        Returns:
            Tuple of (selected_items, dropped_items_with_reasons)
        """
        selected = []
        dropped = []

        # Track budget usage by category
        usage = {
            "system": 0,
            "history": 0,
            "files": 0,
            "search": 0,
            "tools": 0,
        }

        # Map content types to budget categories
        type_to_category = {
            ContentType.SYSTEM_PROMPT: "system",
            ContentType.USER_MESSAGE: "history",
            ContentType.ASSISTANT_MESSAGE: "history",
            ContentType.FILE_CONTENT: "files",
            ContentType.SEARCH_RESULT: "search",
            ContentType.TOOL_OUTPUT: "tools",
            ContentType.SUMMARY: "system",
            ContentType.KNOWLEDGE: "search",
        }

        # Category budgets
        category_budgets = {
            "system": self.budget.system,
            "history": self.budget.history,
            "files": self.budget.files,
            "search": self.budget.search,
            "tools": self.budget.tools,
        }

        available = self.budget.total - self.budget.reserve
        total_used = 0

        for item, score in scored_items:
            category = type_to_category.get(item.content_type, "files")
            category_budget = category_budgets[category]

            # Check if fits in category budget
            if usage[category] + item.tokens > category_budget:
                # Try truncating
                available_in_category = category_budget - usage[category]
                if available_in_category > 100:  # Minimum useful size
                    truncated = item.truncate(available_in_category)
                    if truncated.tokens > 0:
                        selected.append(truncated)
                        usage[category] += truncated.tokens
                        total_used += truncated.tokens
                        continue

                dropped.append((item, f"Category budget exceeded ({category})"))
                continue

            # Check total budget
            if total_used + item.tokens > available:
                dropped.append((item, "Total budget exceeded"))
                continue

            # Add item
            selected.append(item)
            usage[category] += item.tokens
            total_used += item.tokens

        return selected, dropped

    def add_file_context(
        self,
        file_path: str,
        content: str,
        priority: ContextPriority = ContextPriority.MEDIUM,
    ) -> ContextItem:
        """
        Create a file content context item.

        Args:
            file_path: Path to file
            content: File content
            priority: Priority level

        Returns:
            ContextItem for the file
        """
        return ContextItem(
            content=f"File: {file_path}\n```\n{content}\n```",
            content_type=ContentType.FILE_CONTENT,
            priority=priority,
            source=file_path,
            timestamp=datetime.utcnow(),
        )

    def add_search_context(
        self,
        query: str,
        results: list[dict[str, Any]],
        priority: ContextPriority = ContextPriority.MEDIUM,
    ) -> ContextItem:
        """
        Create a search results context item.

        Args:
            query: Search query
            results: Search results
            priority: Priority level

        Returns:
            ContextItem for search results
        """
        content_parts = [f"Search results for '{query}':"]

        for result in results[:10]:  # Limit to top 10
            snippet = result.get("snippet", result.get("content", ""))[:200]
            source = result.get("source", result.get("file", "unknown"))
            content_parts.append(f"\n- {source}: {snippet}")

        return ContextItem(
            content="\n".join(content_parts),
            content_type=ContentType.SEARCH_RESULT,
            priority=priority,
            source=f"search:{query}",
            timestamp=datetime.utcnow(),
        )

    def summarize_history(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 500,
    ) -> ContextItem:
        """
        Summarize conversation history for context.

        Args:
            messages: Message history
            max_tokens: Maximum tokens for summary

        Returns:
            ContextItem with summary
        """
        # Simple summarization - take key points
        summary_parts = ["Conversation summary:"]

        tokens_used = estimate_tokens("Conversation summary:\n")

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Truncate long messages
            if len(content) > 200:
                content = content[:197] + "..."

            line = f"- {role}: {content}"
            line_tokens = estimate_tokens(line)

            if tokens_used + line_tokens > max_tokens:
                break

            summary_parts.append(line)
            tokens_used += line_tokens

        return ContextItem(
            content="\n".join(summary_parts),
            content_type=ContentType.SUMMARY,
            priority=ContextPriority.MEDIUM,
            timestamp=datetime.utcnow(),
        )

    def clear_cache(self) -> None:
        """Clear the optimization cache."""
        self._cache.clear()


# Global instance
_optimizer: ContextOptimizer | None = None


def get_context_optimizer(
    model: str = "default",
    budget: ContextBudget | None = None,
) -> ContextOptimizer:
    """Get or create global context optimizer."""
    global _optimizer

    if _optimizer is None or _optimizer.model != model:
        _optimizer = ContextOptimizer(model, budget)

    return _optimizer
