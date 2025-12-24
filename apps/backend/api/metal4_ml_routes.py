#!/usr/bin/env python3
"""
Metal 4 ML API Routes

"I will praise you, Lord, with all my heart" - Psalm 9:1

REST API endpoints for Metal 4 GPU-accelerated ML operations:
- Text embeddings (Metal 4 MPS)
- Vector similarity search (Metal compute shaders)
- Sparse embedding storage (Metal 4 sparse resources)
- Performance benchmarks and validation
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metal4", tags=["metal4-ml"])


# ===== Request/Response Models =====

class EmbedRequest(BaseModel):
    """Request for text embedding"""
    text: str = Field(..., description="Text to embed")


class EmbedBatchRequest(BaseModel):
    """Request for batch text embedding"""
    texts: List[str] = Field(..., description="List of texts to embed")
    batch_size: Optional[int] = Field(None, description="Batch size for processing")


class SearchRequest(BaseModel):
    """Request for vector similarity search"""
    query: str = Field(..., description="Query text")
    k: int = Field(10, description="Number of results to return", ge=1, le=100)
    metric: str = Field("cosine", description="Similarity metric (cosine, l2, dot)")


class LoadDatabaseRequest(BaseModel):
    """Request to load vector database"""
    embeddings: List[List[float]] = Field(..., description="Embedding vectors [num_vectors, embed_dim]")


class StoreEmbeddingRequest(BaseModel):
    """Request to store embedding in sparse storage"""
    vector_id: int = Field(..., description="Unique vector ID", ge=0)
    text: str = Field(..., description="Text to embed and store")


class EmbedResponse(BaseModel):
    """Response with embedding vector"""
    embedding: List[float]
    dimension: int
    backend: str
    time_ms: float


class EmbedBatchResponse(BaseModel):
    """Response with batch embeddings"""
    embeddings: List[List[float]]
    count: int
    dimension: int
    backend: str
    total_time_ms: float
    avg_time_ms: float


class SearchResponse(BaseModel):
    """Response with search results"""
    indices: List[int]
    scores: List[float]
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
    capabilities: Dict[str, Any]
    embedder: Dict[str, Any]
    vector_search: Dict[str, Any]
    sparse_storage: Dict[str, Any]


# ===== API Endpoints =====

@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(user: dict = Depends(get_current_user)):
    """
    Get Metal 4 GPU capabilities

    Returns system capabilities including Metal version, available backends,
    and hardware features like sparse resources and unified memory.
    """
    try:
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()
        caps = pipeline.get_capabilities()

        return CapabilitiesResponse(**caps)

    except Exception as e:
        logger.exception("Failed to get capabilities")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user: dict = Depends(get_current_user)):
    """
    Get performance statistics

    Returns detailed statistics from all Metal 4 ML components including
    embedder, vector search, and sparse storage performance metrics.
    """
    try:
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()
        stats = pipeline.get_stats()

        return StatsResponse(**stats)

    except Exception as e:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed", response_model=EmbedResponse)
async def embed_text(
    request: EmbedRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create embedding for text using Metal 4 GPU acceleration

    Uses Metal Performance Shaders (MPS) for GPU-accelerated embeddings
    when available. Falls back to CPU automatically if Metal unavailable.

    Expected performance:
    - Metal GPU: 5-10x faster than CPU
    - Apple Silicon: Zero-copy unified memory
    """
    try:
        import time
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()

        start = time.time()
        embedding = pipeline.embed(request.text)
        elapsed_ms = (time.time() - start) * 1000

        return EmbedResponse(
            embedding=embedding,
            dimension=len(embedding),
            backend=pipeline.capabilities['embedder_backend'],
            time_ms=elapsed_ms
        )

    except Exception as e:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed_batch", response_model=EmbedBatchResponse)
async def embed_batch(
    request: EmbedBatchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create embeddings for multiple texts in batch

    Batch processing provides significant performance improvements on GPU:
    - Metal GPU: Up to 10x faster than sequential CPU embedding
    - Automatic batching and optimization based on available VRAM
    """
    try:
        import time
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()

        start = time.time()
        embeddings = pipeline.embed_batch(request.texts)
        elapsed_ms = (time.time() - start) * 1000

        return EmbedBatchResponse(
            embeddings=embeddings,
            count=len(embeddings),
            dimension=len(embeddings[0]) if embeddings else 0,
            backend=pipeline.capabilities['embedder_backend'],
            total_time_ms=elapsed_ms,
            avg_time_ms=elapsed_ms / len(embeddings) if embeddings else 0
        )

    except Exception as e:
        logger.exception("Batch embedding failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def vector_search(
    request: SearchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Search for similar vectors using Metal 4 GPU compute shaders

    Uses Metal compute kernels for parallel similarity computation:
    - Metal GPU: 10-50x faster than CPU for large databases
    - SIMD float4 operations for maximum throughput
    - Supports cosine similarity, L2 distance, and dot product

    Database must be loaded first using /load_database endpoint.
    """
    try:
        import time
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()

        start = time.time()
        indices, scores = pipeline.search(request.query, request.k, request.metric)
        elapsed_ms = (time.time() - start) * 1000

        return SearchResponse(
            indices=indices,
            scores=scores,
            count=len(indices),
            backend=pipeline.capabilities['vector_search_backend'],
            time_ms=elapsed_ms
        )

    except Exception as e:
        logger.exception("Vector search failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load_database")
async def load_database(
    request: LoadDatabaseRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Load vector database for searching

    Loads embedding vectors into GPU memory for fast similarity search.
    On Metal 4 with unified memory, this is a zero-copy operation.

    Note: Large databases benefit from sparse resources (Metal 4 / macOS Tahoe 26+)
    """
    try:
        import numpy as np
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()

        # Convert to numpy array
        embeddings = np.array(request.embeddings, dtype=np.float32)

        pipeline.load_database(embeddings)

        return {
            "message": "Database loaded successfully",
            "num_vectors": embeddings.shape[0],
            "embed_dim": embeddings.shape[1],
            "backend": pipeline.capabilities['vector_search_backend']
        }

    except Exception as e:
        logger.exception("Failed to load database")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store_embedding")
async def store_embedding(
    request: StoreEmbeddingRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Store embedding in sparse storage

    Uses Metal 4 Sparse Resources for memory-efficient storage of large
    embedding collections (100M+ vectors).

    Features:
    - Memory-mapped backing store
    - On-demand GPU paging (Metal 4)
    - LRU cache for frequently accessed vectors
    """
    try:
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()
        pipeline.store_embedding(request.vector_id, request.text)

        return {
            "message": "Embedding stored successfully",
            "vector_id": request.vector_id
        }

    except Exception as e:
        logger.exception("Failed to store embedding")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve_embedding/{vector_id}")
async def retrieve_embedding(
    vector_id: int,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieve embedding from sparse storage

    Retrieves stored embedding vector by ID. Uses GPU cache when available
    for frequently accessed vectors.
    """
    try:
        from metal4_ml_integration import get_ml_pipeline

        pipeline = get_ml_pipeline()
        embedding = pipeline.retrieve_embedding(vector_id)

        if embedding is None:
            raise HTTPException(status_code=404, detail="Vector not found")

        return {
            "vector_id": vector_id,
            "embedding": embedding.tolist(),
            "dimension": len(embedding)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve embedding")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_setup(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Validate Metal 4 ML pipeline setup

    Runs comprehensive validation tests on all components:
    - Embedder functionality
    - Vector search accuracy
    - Sparse storage integrity

    Returns detailed status and test results.
    """
    try:
        from metal4_ml_integration import validate_ml_pipeline

        results = validate_ml_pipeline()

        return {
            "validation_results": results,
            "all_tests_passed": all([
                results.get('embedding_test', False),
                results.get('batch_embedding_test', False),
                results.get('search_test', False)
            ])
        }

    except Exception as e:
        logger.exception("Validation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark")
async def run_benchmark(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Run performance benchmarks

    Executes comprehensive benchmarks comparing Metal GPU vs CPU performance:
    - Single embedding performance
    - Batch embedding performance
    - Vector search performance
    - Sparse storage performance
    - End-to-end RAG pipeline

    Returns detailed results including speedup measurements and success criteria.

    WARNING: This may take several minutes to complete.
    """
    try:
        from metal4_benchmarks import run_benchmarks

        logger.info("Starting Metal 4 benchmarks...")
        results = run_benchmarks()

        return {
            "benchmark_results": results,
            "message": "Benchmarks completed successfully"
        }

    except Exception as e:
        logger.exception("Benchmark failed")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['router']
