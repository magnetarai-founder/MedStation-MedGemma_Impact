"""Backward Compatibility Shim - use api.ml.mlx instead."""

from api.ml.mlx.sentence_transformer import (
    MLXSentenceTransformer,
    create_mlx_embedder,
    test_mlx_sentence_transformer,
)

__all__ = ["MLXSentenceTransformer", "create_mlx_embedder", "test_mlx_sentence_transformer"]
