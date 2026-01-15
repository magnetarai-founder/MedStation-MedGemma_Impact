"""
Metal 4 GPU acceleration for NeutronStar.

Note: The core Metal4Engine is in api.metal4_engine (separate package).

Provides:
- Metal4Benchmarks: GPU benchmark suite
- Metal4Diagnostics: Performance monitoring
- Metal4DuckDBBridge: DuckDB GPU acceleration
- Metal4MetalFXRenderer: MetalFX upscaling
- Metal4MLPipeline: ML pipeline acceleration
- Metal4MPSEmbedder: MPS-accelerated embeddings
- Metal4ResourceManager: GPU resource management
- Metal4SparseEmbeddings: Sparse embedding operations
- Metal4SQLEngine: GPU-accelerated SQL
- Metal4TensorOps: Tensor operations
- Metal4VectorSearch: Vector similarity search
"""

from api.ml.metal4.benchmarks import Metal4Benchmarks, BenchmarkResult, run_benchmarks
from api.ml.metal4.diagnostics import Metal4Diagnostics, get_diagnostics, QueueStats, PerformanceMetrics
from api.ml.metal4.duckdb_bridge import Metal4DuckDBBridge, get_duckdb_bridge, validate_duckdb_bridge
from api.ml.metal4.metalfx_renderer import Metal4MetalFXRenderer, get_metalfx_renderer, validate_metalfx_renderer, FrameMetrics
from api.ml.metal4.ml_integration import Metal4MLPipeline, get_ml_pipeline, validate_ml_pipeline
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
from api.ml.metal4.mps_embedder import Metal4MPSEmbedder, get_metal4_mps_embedder, validate_metal4_mps_setup
from api.ml.metal4.resources import Metal4ResourceManager, get_resource_manager, BufferType
from api.ml.metal4.sparse_embeddings import Metal4SparseEmbeddings, get_sparse_embeddings, validate_sparse_embeddings
from api.ml.metal4.sql_engine import Metal4SQLEngine, get_sql_engine, validate_sql_engine
from api.ml.metal4.tensor_ops import Metal4TensorOps, get_tensor_ops, validate_tensor_ops
from api.ml.metal4.vector_search import Metal4VectorSearch, get_metal4_vector_search, validate_metal4_vector_search

__all__ = [
    # benchmarks
    "Metal4Benchmarks",
    "BenchmarkResult",
    "run_benchmarks",
    # diagnostics
    "Metal4Diagnostics",
    "get_diagnostics",
    "QueueStats",
    "PerformanceMetrics",
    # duckdb_bridge
    "Metal4DuckDBBridge",
    "get_duckdb_bridge",
    "validate_duckdb_bridge",
    # metalfx_renderer
    "Metal4MetalFXRenderer",
    "get_metalfx_renderer",
    "validate_metalfx_renderer",
    "FrameMetrics",
    # ml_integration
    "Metal4MLPipeline",
    "get_ml_pipeline",
    "validate_ml_pipeline",
    # ml_types
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
    # mps_embedder
    "Metal4MPSEmbedder",
    "get_metal4_mps_embedder",
    "validate_metal4_mps_setup",
    # resources
    "Metal4ResourceManager",
    "get_resource_manager",
    "BufferType",
    # sparse_embeddings
    "Metal4SparseEmbeddings",
    "get_sparse_embeddings",
    "validate_sparse_embeddings",
    # sql_engine
    "Metal4SQLEngine",
    "get_sql_engine",
    "validate_sql_engine",
    # tensor_ops
    "Metal4TensorOps",
    "get_tensor_ops",
    "validate_tensor_ops",
    # vector_search
    "Metal4VectorSearch",
    "get_metal4_vector_search",
    "validate_metal4_vector_search",
]
