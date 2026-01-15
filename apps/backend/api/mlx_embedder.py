"""Backward Compatibility Shim - use api.ml.mlx instead."""

from api.ml.mlx.embedder import (
    MLXEmbedder,
    get_mlx_embedder,
    validate_mlx_setup,
)

__all__ = ["MLXEmbedder", "get_mlx_embedder", "validate_mlx_setup"]
