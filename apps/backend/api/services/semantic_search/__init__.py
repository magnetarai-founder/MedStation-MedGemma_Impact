"""
Semantic Search Package for MagnetarCode

Provides vector-based semantic search across conversation history.
"""
from .engine import SemanticSearchEngine, get_semantic_search
from .models import SearchConfig, SemanticSearchResult

__all__ = [
    "SemanticSearchEngine",
    "get_semantic_search",
    "SemanticSearchResult",
    "SearchConfig",
]
