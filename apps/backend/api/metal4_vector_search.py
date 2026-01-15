"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.vector_search import (
    Metal4VectorSearch,
    get_metal4_vector_search,
    validate_metal4_vector_search,
    logger,
)

__all__ = ["Metal4VectorSearch", "get_metal4_vector_search", "validate_metal4_vector_search", "logger"]
