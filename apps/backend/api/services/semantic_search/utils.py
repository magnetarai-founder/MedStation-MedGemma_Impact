"""
Helper utilities for semantic search
"""
import numpy as np


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def _create_snippet(content: str, query: str, max_length: int) -> str:
    """
    Create a snippet highlighting query relevance

    Args:
        content: Full message content
        query: Search query
        max_length: Maximum snippet length

    Returns:
        Snippet with query context
    """
    content = content.strip()

    # If content is short, return as-is
    if len(content) <= max_length:
        return content

    # Try to find query term in content
    query_lower = query.lower()
    content_lower = content.lower()

    # Find first occurrence of any query term
    best_pos = -1
    for term in query_lower.split():
        pos = content_lower.find(term)
        if pos != -1:
            best_pos = pos
            break

    # If query term found, center snippet around it
    if best_pos != -1:
        start = max(0, best_pos - max_length // 2)
        end = min(len(content), start + max_length)
        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet.strip()

    # Otherwise, return beginning
    return content[:max_length] + "..."
