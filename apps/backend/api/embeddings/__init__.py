"""
Embeddings Package

Embedding systems for MedStation:
- EmbeddingSystem: Lightweight semantic embeddings
- UnifiedEmbedder: Multi-backend embedding interface
"""

from api.embeddings.system import (
    EmbeddingModel,
    EmbeddingSystem,
)
from api.embeddings.unified import UnifiedEmbedder

__all__ = [
    "EmbeddingModel",
    "EmbeddingSystem",
    "UnifiedEmbedder",
]
