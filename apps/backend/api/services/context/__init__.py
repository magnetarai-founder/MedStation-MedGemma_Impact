"""
Context Management Package

Provides smart context window optimization for LLM calls:
- Token budget management
- Priority-based content selection
- Intelligent truncation
- Relevance scoring
- Context caching
"""

from .optimizer import (
    ContentType,
    ContextBudget,
    ContextItem,
    ContextOptimizer,
    ContextPriority,
    OptimizedContext,
    estimate_tokens,
    get_context_optimizer,
)

__all__ = [
    # Token estimation
    "estimate_tokens",
    # Enums
    "ContextPriority",
    "ContentType",
    # Data classes
    "ContextItem",
    "ContextBudget",
    "OptimizedContext",
    # Optimizer
    "ContextOptimizer",
    "get_context_optimizer",
]
