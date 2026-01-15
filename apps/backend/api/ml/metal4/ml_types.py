"""
Metal 4 ML Types - Request/response models for Metal GPU ML operations

Extracted from metal4_ml_routes.py during P2 decomposition.
Contains:
- EmbedRequest, EmbedBatchRequest (input models)
- EmbedResponse, EmbedBatchResponse (output models)
- SearchRequest, SearchResponse (vector search models)
- LoadDatabaseRequest, StoreEmbeddingRequest (database models)
- CapabilitiesResponse, StatsResponse (status models)
"""

from pydantic import BaseModel, Field
from typing import Any


# ===== Request Models =====

class EmbedRequest(BaseModel):
    """Request for text embedding"""
    text: str = Field(..., description="Text to embed")


class EmbedBatchRequest(BaseModel):
    """Request for batch text embedding"""
    texts: list[str] = Field(..., description="List of texts to embed")
    batch_size: int | None = Field(None, description="Batch size for processing")


class SearchRequest(BaseModel):
    """Request for vector similarity search"""
    query: str = Field(..., description="Query text")
    k: int = Field(10, description="Number of results to return", ge=1, le=100)
    metric: str = Field("cosine", description="Similarity metric (cosine, l2, dot)")


class LoadDatabaseRequest(BaseModel):
    """Request to load vector database"""
    embeddings: list[list[float]] = Field(..., description="Embedding vectors [num_vectors, embed_dim]")


class StoreEmbeddingRequest(BaseModel):
    """Request to store embedding in sparse storage"""
    vector_id: int = Field(..., description="Unique vector ID", ge=0)
    text: str = Field(..., description="Text to embed and store")


# ===== Response Models =====

class EmbedResponse(BaseModel):
    """Response with embedding vector"""
    embedding: list[float]
    dimension: int
    backend: str
    time_ms: float


class EmbedBatchResponse(BaseModel):
    """Response with batch embeddings"""
    embeddings: list[list[float]]
    count: int
    dimension: int
    backend: str
    total_time_ms: float
    avg_time_ms: float


class SearchResponse(BaseModel):
    """Response with search results"""
    indices: list[int]
    scores: list[float]
    count: int
    backend: str
    time_ms: float


class CapabilitiesResponse(BaseModel):
    """Response with Metal 4 capabilities"""
    metal_version: int
    embedder_backend: str
    vector_search_backend: str
    sparse_resources: bool
    unified_memory: bool


class StatsResponse(BaseModel):
    """Response with performance statistics"""
    capabilities: dict[str, Any]
    embedder: dict[str, Any]
    vector_search: dict[str, Any]
    sparse_storage: dict[str, Any]


__all__ = [
    # Request models
    "EmbedRequest",
    "EmbedBatchRequest",
    "SearchRequest",
    "LoadDatabaseRequest",
    "StoreEmbeddingRequest",
    # Response models
    "EmbedResponse",
    "EmbedBatchResponse",
    "SearchResponse",
    "CapabilitiesResponse",
    "StatsResponse",
]
