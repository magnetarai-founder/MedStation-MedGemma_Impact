"""
Semantic Search Utilities

Shared functions for embedding generation and vector similarity calculations.
Used by both data/ and vault/ semantic search routes.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


async def embed_query(text: str) -> Optional[List[float]]:
    """
    Generate embedding for query text using ANE Context Engine.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding, or None if embedding fails
    """
    try:
        from api.ane_context_engine import _embed_with_ane
        embedding = _embed_with_ane(text)
        return embedding
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score between 0 and 1, or 0 if vectors are incompatible
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)
