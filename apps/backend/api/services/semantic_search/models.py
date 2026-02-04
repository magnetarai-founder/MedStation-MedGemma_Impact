"""
Data models for semantic search
"""
from dataclasses import dataclass


@dataclass
class SemanticSearchResult:
    """A single semantic search result"""

    session_id: str
    session_title: str | None
    message_id: int
    role: str
    content: str
    timestamp: str
    model: str | None
    similarity: float
    snippet: str  # Highlighted excerpt


@dataclass
class SearchConfig:
    """Configuration for semantic search"""

    top_k: int = 10
    similarity_threshold: float = 0.3
    max_snippet_length: int = 200
    use_hybrid: bool = True  # Combine semantic + keyword
    rerank: bool = True  # Re-rank by relevance
