"""
Compatibility Shim for Embedding System

The implementation now lives in the `api.embeddings` package:
- api.embeddings.system: EmbeddingSystem class

This shim maintains backward compatibility.
"""

from api.embeddings.system import (
    EmbeddingModel,
    EmbeddingSystem,
)

__all__ = [
    "EmbeddingModel",
    "EmbeddingSystem",
]
