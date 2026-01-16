"""
Compatibility Shim for Unified Embedder

The implementation now lives in the `api.embeddings` package:
- api.embeddings.unified: UnifiedEmbedder class

This shim maintains backward compatibility.
"""

from api.embeddings.unified import UnifiedEmbedder

__all__ = [
    "UnifiedEmbedder",
]
