"""
Shared Utilities Package

Common utility functions used across the API.
"""

from api.shared.semantic_utils import (
    embed_query,
    compute_cosine_similarity,
)

__all__ = [
    "embed_query",
    "compute_cosine_similarity",
]
