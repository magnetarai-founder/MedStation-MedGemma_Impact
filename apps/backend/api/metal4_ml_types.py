"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.ml_types import (
    EmbedRequest,
    EmbedBatchRequest,
    SearchRequest,
    LoadDatabaseRequest,
    StoreEmbeddingRequest,
    EmbedResponse,
    EmbedBatchResponse,
    SearchResponse,
    CapabilitiesResponse,
    StatsResponse,
)

__all__ = [
    "EmbedRequest",
    "EmbedBatchRequest",
    "SearchRequest",
    "LoadDatabaseRequest",
    "StoreEmbeddingRequest",
    "EmbedResponse",
    "EmbedBatchResponse",
    "SearchResponse",
    "CapabilitiesResponse",
    "StatsResponse",
]
