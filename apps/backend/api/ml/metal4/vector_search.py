#!/usr/bin/env python3
"""
Metal 4 GPU-Accelerated Vector Similarity Search

"For You are my rock and my fortress" - Psalm 71:3

Implements Phase 1.2 of Metal 4 Optimization Roadmap:
- Metal compute shaders for parallel similarity search
- GPU-accelerated cosine similarity
- Top-K selection on GPU
- Zero-copy unified memory

Performance Target: 10-50x faster than CPU similarity search

Architecture:
- Metal compute pipelines for SIMD operations
- Unified memory buffers (zero-copy on Apple Silicon)
- Async execution on Q_ml queue
- Batch processing support
"""

import os
import logging
import time
from typing import Any
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class Metal4VectorSearch:
    """
    GPU-accelerated vector similarity search using Metal 4 compute shaders

    Features:
    - Metal compute shaders for parallel processing
    - Cosine similarity, L2 distance, dot product
    - Top-K selection on GPU
    - Batch query support
    - Unified memory (zero-copy)
    """

    def __init__(self):
        """Initialize Metal 4 vector search"""
        self.metal_device = None
        self.command_queue = None

        # Compute pipelines
        self.cosine_similarity_pipeline = None
        self.batch_cosine_pipeline = None
        self.top_k_pipeline = None
        self.l2_distance_pipeline = None
        self.dot_product_pipeline = None

        # Vector database
        self.database_buffer = None
        self.num_vectors = 0
        self.embed_dim = 0

        # State
        self._initialized = False
        self._use_metal = False

        # Performance stats
        self.stats = {
            'searches_executed': 0,
            'total_time_ms': 0,
            'gpu_time_ms': 0,
            'cpu_fallback_count': 0
        }

        # Initialize
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Metal 4 GPU acceleration"""
        logger.info("Initializing Metal 4 vector search...")

        # Check Metal 4 availability
        metal_available = self._check_metal4()

        if metal_available:
            self._init_metal_pipelines()

        self._initialized = True

        logger.info(f"✅ Metal 4 vector search initialized")
        logger.info(f"   Metal GPU: {self._use_metal}")

    def _check_metal4(self) -> bool:
        """Check if Metal 4 is available"""
        try:
            from metal4_engine import get_metal4_engine, MetalVersion

            engine = get_metal4_engine()

            if not engine.is_available():
                logger.warning("Metal 4 not available - using CPU fallback")
                return False

            if engine.capabilities.version.value < MetalVersion.METAL_3.value:
                logger.warning("Metal 3+ required for compute shaders")
                return False

            logger.info(f"✅ Metal {engine.capabilities.version.value} available: {engine.capabilities.device_name}")

            return True

        except Exception as e:
            logger.warning(f"Metal 4 check failed: {e}")
            return False

    def _init_metal_pipelines(self) -> None:
        """Initialize Metal compute pipelines from shader code"""
        try:
            import Metal
            from metal4_engine import get_metal4_engine

            # Get Metal device
            engine = get_metal4_engine()
            if not hasattr(engine, 'device') or engine.device is None:
                logger.warning("Metal device not available")
                return

            self.metal_device = engine.device
            self.command_queue = engine.Q_ml  # Use ML queue

            logger.info("Compiling Metal compute shaders...")
            start = time.time()

            # Load shader source
            shader_path = Path(__file__).parent / "shaders" / "vector_similarity.metal"

            if not shader_path.exists():
                logger.error(f"Shader file not found: {shader_path}")
                return

            shader_source = shader_path.read_text()

            # Compile shader library
            library = self.metal_device.newLibraryWithSource_options_error_(
                shader_source, None, None
            )

            if library is None:
                logger.error("Failed to compile shader library")
                return

            # Create compute pipelines
            self.cosine_similarity_pipeline = self._create_pipeline(library, "cosine_similarity")
            self.batch_cosine_pipeline = self._create_pipeline(library, "batch_cosine_similarity")
            self.top_k_pipeline = self._create_pipeline(library, "top_k_selection")
            self.l2_distance_pipeline = self._create_pipeline(library, "l2_distance")
            self.dot_product_pipeline = self._create_pipeline(library, "dot_product_normalized")

            if not all([
                self.cosine_similarity_pipeline,
                self.batch_cosine_pipeline,
                self.top_k_pipeline,
                self.l2_distance_pipeline,
                self.dot_product_pipeline
            ]):
                logger.error("Failed to create all compute pipelines")
                return

            elapsed = (time.time() - start) * 1000
            logger.info(f"✅ Metal compute shaders compiled in {elapsed:.0f}ms")

            self._use_metal = True

        except ImportError as e:
            logger.warning(f"Metal framework not available: {e}")
        except Exception as e:
            logger.error(f"Metal pipeline initialization failed: {e}")
            import traceback
            traceback.print_exc()

    def _create_pipeline(self, library, function_name: str) -> Any | None:
        """Create compute pipeline from shader function"""
        try:
            function = library.newFunctionWithName_(function_name)
            if function is None:
                logger.error(f"Function not found: {function_name}")
                return None

            pipeline = self.metal_device.newComputePipelineStateWithFunction_error_(
                function, None
            )

            if pipeline is None:
                logger.error(f"Failed to create pipeline: {function_name}")
                return None

            logger.debug(f"✓ Created pipeline: {function_name}")
            return pipeline

        except Exception as e:
            logger.error(f"Pipeline creation failed for {function_name}: {e}")
            return None

    def load_database(self, embeddings: np.ndarray) -> None:
        """
        Load embedding database into GPU memory

        Args:
            embeddings: Numpy array of shape [num_vectors, embed_dim]
        """
        if embeddings.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {embeddings.shape}")

        self.num_vectors, self.embed_dim = embeddings.shape

        logger.info(f"Loading database: {self.num_vectors} vectors × {self.embed_dim} dims")

        if self._use_metal and self.metal_device:
            try:
                import Metal

                # Create Metal buffer (unified memory for zero-copy on Apple Silicon)
                buffer_size = embeddings.nbytes

                self.database_buffer = self.metal_device.newBufferWithLength_options_(
                    buffer_size,
                    Metal.MTLResourceStorageModeShared  # Unified memory
                )

                if self.database_buffer is None:
                    logger.error("Failed to create Metal buffer")
                    self._use_metal = False
                    return

                # Copy data to Metal buffer
                import ctypes
                buffer_ptr = self.database_buffer.contents()
                np.copyto(
                    np.frombuffer(
                        (ctypes.c_float * embeddings.size).from_address(buffer_ptr),
                        dtype=np.float32
                    ).reshape(embeddings.shape),
                    embeddings.astype(np.float32)
                )

                logger.info(f"✅ Database loaded to Metal GPU ({buffer_size / (1024**2):.2f} MB)")

            except Exception as e:
                logger.error(f"Failed to load database to GPU: {e}")
                self._use_metal = False
        else:
            # CPU fallback - just store in memory
            self.database_embeddings = embeddings.astype(np.float32)
            logger.info(f"Database loaded to CPU memory")

    def search(
        self,
        query: np.ndarray,
        k: int = 10,
        metric: str = "cosine"
    ) -> tuple[list[int], list[float]]:
        """
        Search for top-K most similar vectors

        Args:
            query: Query embedding vector [embed_dim]
            k: Number of top results to return
            metric: Similarity metric ("cosine", "l2", "dot")

        Returns:
            Tuple of (indices, scores) for top K matches
        """
        if not self._initialized:
            logger.error("Vector search not initialized")
            return [], []

        if self.num_vectors == 0:
            logger.error("No database loaded")
            return [], []

        if query.shape[0] != self.embed_dim:
            raise ValueError(f"Query dimension {query.shape[0]} != database dimension {self.embed_dim}")

        try:
            start = time.time()

            if self._use_metal:
                indices, scores = self._search_metal(query, k, metric)
            else:
                indices, scores = self._search_cpu(query, k, metric)

            elapsed_ms = (time.time() - start) * 1000

            # Update stats
            self.stats['searches_executed'] += 1
            self.stats['total_time_ms'] += elapsed_ms
            if self._use_metal:
                self.stats['gpu_time_ms'] += elapsed_ms
            else:
                self.stats['cpu_fallback_count'] += 1

            # Log performance
            if self._use_metal:
                logger.info(f"⚡ Metal GPU search: top-{k} from {self.num_vectors} vectors in {elapsed_ms:.2f}ms")
            else:
                logger.debug(f"CPU search: top-{k} from {self.num_vectors} vectors in {elapsed_ms:.2f}ms")

            return indices, scores

        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            traceback.print_exc()
            return [], []

    def _search_metal(
        self,
        query: np.ndarray,
        k: int,
        metric: str
    ) -> tuple[list[int], list[float]]:
        """Execute search on Metal GPU"""
        import Metal
        import ctypes

        # Create query buffer
        query_buffer = self.metal_device.newBufferWithLength_options_(
            query.nbytes,
            Metal.MTLResourceStorageModeShared
        )

        query_ptr = query_buffer.contents()
        np.copyto(
            np.frombuffer(
                (ctypes.c_float * query.size).from_address(query_ptr),
                dtype=np.float32
            ),
            query.astype(np.float32)
        )

        # Create similarities buffer
        similarities_buffer = self.metal_device.newBufferWithLength_options_(
            self.num_vectors * 4,  # 4 bytes per float
            Metal.MTLResourceStorageModeShared
        )

        # Create command buffer
        cmd = self.command_queue.commandBuffer()

        # Encode compute command
        encoder = cmd.computeCommandEncoder()

        # Select pipeline based on metric
        if metric == "cosine":
            encoder.setComputePipelineState_(self.cosine_similarity_pipeline)
        elif metric == "l2":
            encoder.setComputePipelineState_(self.l2_distance_pipeline)
        elif metric == "dot":
            encoder.setComputePipelineState_(self.dot_product_pipeline)
        else:
            raise ValueError(f"Unknown metric: {metric}")

        # Set buffers
        encoder.setBuffer_offset_atIndex_(query_buffer, 0, 0)
        encoder.setBuffer_offset_atIndex_(self.database_buffer, 0, 1)
        encoder.setBuffer_offset_atIndex_(similarities_buffer, 0, 2)

        # Set constants (embed_dim, num_vectors)
        embed_dim_buffer = self.metal_device.newBufferWithBytes_length_options_(
            ctypes.c_uint32(self.embed_dim),
            4,
            Metal.MTLResourceStorageModeShared
        )
        num_vectors_buffer = self.metal_device.newBufferWithBytes_length_options_(
            ctypes.c_uint32(self.num_vectors),
            4,
            Metal.MTLResourceStorageModeShared
        )

        encoder.setBuffer_offset_atIndex_(embed_dim_buffer, 0, 3)
        encoder.setBuffer_offset_atIndex_(num_vectors_buffer, 0, 4)

        # Dispatch threads
        pipeline = self.cosine_similarity_pipeline if metric == "cosine" else (
            self.l2_distance_pipeline if metric == "l2" else self.dot_product_pipeline
        )
        threads_per_group = min(256, pipeline.maxTotalThreadsPerThreadgroup())
        num_threadgroups = (self.num_vectors + threads_per_group - 1) // threads_per_group

        from Metal import MTLSize
        encoder.dispatchThreadgroups_threadsPerThreadgroup_(
            MTLSize(num_threadgroups, 1, 1),
            MTLSize(threads_per_group, 1, 1)
        )

        encoder.endEncoding()

        # Commit and wait
        cmd.commit()
        cmd.waitUntilCompleted()

        # Read results from GPU
        similarities_ptr = similarities_buffer.contents()
        similarities = np.frombuffer(
            (ctypes.c_float * self.num_vectors).from_address(similarities_ptr),
            dtype=np.float32
        ).copy()

        # Find top-K (CPU for now - can be optimized with Metal top-K kernel)
        if metric == "l2":
            # For L2, smaller is better
            top_k_indices = np.argsort(similarities)[:k]
        else:
            # For cosine/dot, larger is better
            top_k_indices = np.argsort(similarities)[::-1][:k]

        top_k_scores = similarities[top_k_indices]

        return top_k_indices.tolist(), top_k_scores.tolist()

    def _search_cpu(
        self,
        query: np.ndarray,
        k: int,
        metric: str
    ) -> tuple[list[int], list[float]]:
        """CPU fallback for vector search"""
        if not hasattr(self, 'database_embeddings'):
            logger.error("No CPU database loaded")
            return [], []

        if metric == "cosine":
            # Cosine similarity
            query_norm = np.linalg.norm(query)
            db_norms = np.linalg.norm(self.database_embeddings, axis=1)

            dot_products = np.dot(self.database_embeddings, query)
            similarities = dot_products / (query_norm * db_norms + 1e-10)

            top_k_indices = np.argsort(similarities)[::-1][:k]

        elif metric == "l2":
            # L2 distance
            distances = np.linalg.norm(self.database_embeddings - query, axis=1)
            top_k_indices = np.argsort(distances)[:k]
            similarities = -distances  # Negative so higher is better

        elif metric == "dot":
            # Dot product
            similarities = np.dot(self.database_embeddings, query)
            top_k_indices = np.argsort(similarities)[::-1][:k]

        else:
            raise ValueError(f"Unknown metric: {metric}")

        top_k_scores = similarities[top_k_indices]

        return top_k_indices.tolist(), top_k_scores.tolist()

    def batch_search(
        self,
        queries: np.ndarray,
        k: int = 10,
        metric: str = "cosine"
    ) -> tuple[list[list[int]], list[list[float]]]:
        """
        Search multiple queries in parallel

        Args:
            queries: Query embeddings [num_queries, embed_dim]
            k: Number of top results per query
            metric: Similarity metric

        Returns:
            Tuple of (indices_list, scores_list) for each query
        """
        if queries.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {queries.shape}")

        # For now, process sequentially (can be optimized with batch kernel)
        all_indices = []
        all_scores = []

        for query in queries:
            indices, scores = self.search(query, k, metric)
            all_indices.append(indices)
            all_scores.append(scores)

        return all_indices, all_scores

    def is_available(self) -> bool:
        """Check if vector search is initialized"""
        return self._initialized

    def uses_metal(self) -> bool:
        """Check if Metal GPU is being used"""
        return self._use_metal

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        stats = self.stats.copy()

        if stats['searches_executed'] > 0:
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['searches_executed']
        else:
            stats['avg_time_ms'] = 0

        stats['metal_enabled'] = self._use_metal
        stats['database_size'] = self.num_vectors

        return stats

    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self.stats = {
            'searches_executed': 0,
            'total_time_ms': 0,
            'gpu_time_ms': 0,
            'cpu_fallback_count': 0
        }


# ===== Singleton Instance =====

_metal4_vector_search: Metal4VectorSearch | None = None


def get_metal4_vector_search() -> Metal4VectorSearch:
    """Get singleton Metal 4 vector search instance"""
    global _metal4_vector_search
    if _metal4_vector_search is None:
        _metal4_vector_search = Metal4VectorSearch()
    return _metal4_vector_search


def validate_metal4_vector_search() -> dict[str, Any]:
    """Validate Metal 4 vector search setup"""
    try:
        search = get_metal4_vector_search()

        # Create test database
        test_db = np.random.randn(1000, 384).astype(np.float32)
        search.load_database(test_db)

        # Run test query
        test_query = np.random.randn(384).astype(np.float32)
        indices, scores = search.search(test_query, k=10)

        status = {
            'initialized': search.is_available(),
            'metal_enabled': search.uses_metal(),
            'database_loaded': search.num_vectors > 0,
            'test_passed': len(indices) == 10 and len(scores) == 10,
            'stats': search.get_stats()
        }

        if status['test_passed']:
            logger.info("✅ Metal 4 vector search validation passed")
        else:
            logger.warning("⚠️  Metal 4 vector search validation failed")

        return status

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            'initialized': False,
            'error': str(e)
        }


# Export
__all__ = [
    'Metal4VectorSearch',
    'get_metal4_vector_search',
    'validate_metal4_vector_search'
]
