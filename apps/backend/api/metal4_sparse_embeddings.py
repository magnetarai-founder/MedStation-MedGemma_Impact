"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.sparse_embeddings import (
    Metal4SparseEmbeddings,
    get_sparse_embeddings,
    validate_sparse_embeddings,
    logger,
)

__all__ = ["Metal4SparseEmbeddings", "get_sparse_embeddings", "validate_sparse_embeddings", "logger"]
