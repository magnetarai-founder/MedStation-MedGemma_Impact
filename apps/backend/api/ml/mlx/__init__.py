"""
MLX Framework integration for Apple Silicon.

Provides:
- MLXEmbedder: Hardware-accelerated text embeddings
- MLXDistributed: Distributed MLX computation
- MLXSentenceTransformer: Sentence transformer models
"""

from api.ml.mlx.embedder import MLXEmbedder, get_mlx_embedder, validate_mlx_setup
from api.ml.mlx.distributed import get_mlx_distributed

__all__ = [
    "MLXEmbedder",
    "get_mlx_embedder",
    "validate_mlx_setup",
    "get_mlx_distributed",
]
