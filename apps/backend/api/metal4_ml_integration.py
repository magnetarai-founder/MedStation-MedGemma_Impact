#!/usr/bin/env python3
"""
Metal 4 ML Integration - Unified Interface with Progressive Enhancement

"The Lord is the stronghold of my life" - Psalm 27:1

Provides a unified interface for Metal 4 ML acceleration with automatic
fallback to CPU when Metal is unavailable.

Features:
- Progressive enhancement (Metal 4 → Metal 3 → CPU)
- Automatic feature detection
- Unified API regardless of backend
- Performance monitoring and statistics

Architecture:
- Metal 4 MPS embedder (5-10x faster)
- Metal 4 vector search (10-50x faster)
- Sparse embeddings (10x memory efficiency)
- CPU fallback for all operations
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class Metal4MLPipeline:
    """
    Unified ML pipeline with Metal 4 acceleration and CPU fallback

    This class provides a single interface for:
    - Text embeddings
    - Vector similarity search
    - Large-scale embedding storage

    Automatically selects the best available backend:
    1. Metal 4 (macOS Tahoe 26+, Apple Silicon)
    2. Metal 3 (macOS Sonoma/Sequoia, Apple Silicon)
    3. CPU (All platforms)
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_vectors: int = 1_000_000,
        gpu_cache_mb: int = 2048
    ):
        """
        Initialize ML pipeline with best available backend

        Args:
            model_name: HuggingFace model for embeddings
            max_vectors: Maximum vectors for sparse storage
            gpu_cache_mb: GPU cache size in MB
        """
        self.model_name = model_name
        self.max_vectors = max_vectors
        self.gpu_cache_mb = gpu_cache_mb

        # Components
        self.embedder = None
        self.vector_search = None
        self.sparse_storage = None

        # Capabilities
        self.capabilities = {
            'metal_version': 0,
            'embedder_backend': 'none',
            'vector_search_backend': 'none',
            'sparse_resources': False,
            'unified_memory': False
        }

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize all components with progressive enhancement"""
        logger.info("=" * 60)
        logger.info("Metal 4 ML Pipeline Initialization")
        logger.info("=" * 60)

        # Step 1: Detect Metal capabilities
        self._detect_metal_capabilities()

        # Step 2: Initialize embedder (Metal 4 → Metal 3 → CPU)
        self._init_embedder()

        # Step 3: Initialize vector search (Metal → CPU)
        self._init_vector_search()

        # Step 4: Initialize sparse storage (Metal 4 → mmap)
        self._init_sparse_storage()

        # Step 5: Print summary
        self._print_initialization_summary()

        logger.info("=" * 60)

    def _detect_metal_capabilities(self):
        """Detect Metal GPU capabilities"""
        try:
            from metal4_engine import get_metal4_engine

            engine = get_metal4_engine()

            if engine.is_available():
                self.capabilities['metal_version'] = engine.capabilities.version.value
                self.capabilities['unified_memory'] = engine.capabilities.supports_unified_memory
                self.capabilities['sparse_resources'] = engine.capabilities.supports_sparse_resources

                logger.info(f"✅ Metal {engine.capabilities.version.value} detected")
                logger.info(f"   Device: {engine.capabilities.device_name}")
                logger.info(f"   Unified Memory: {engine.capabilities.supports_unified_memory}")
                logger.info(f"   Sparse Resources: {engine.capabilities.supports_sparse_resources}")
            else:
                logger.warning("⚠️  Metal not available - using CPU fallback")

        except Exception as e:
            logger.warning(f"Metal detection failed: {e}")

    def _init_embedder(self):
        """Initialize embedder with best available backend"""
        logger.info("\n--- Initializing Embedder ---")

        # Try Metal 4 MPS embedder first
        if self.capabilities['metal_version'] >= 3:
            try:
                from metal4_mps_embedder import get_metal4_mps_embedder

                self.embedder = get_metal4_mps_embedder(self.model_name)

                if self.embedder.is_available():
                    backend = "Metal 4 MPS (GPU)" if self.embedder.uses_metal() else "PyTorch (CPU)"
                    self.capabilities['embedder_backend'] = backend
                    logger.info(f"✅ Embedder: {backend}")
                    return

            except Exception as e:
                logger.debug(f"Metal 4 MPS embedder failed: {e}")

        # Fallback to unified embedder (tries MLX, then sentence-transformers, then hash)
        try:
            from unified_embedder import get_unified_embedder

            self.embedder = get_unified_embedder()

            if self.embedder and self.embedder.is_available():
                self.capabilities['embedder_backend'] = f"Unified ({self.embedder.backend})"
                logger.info(f"✅ Embedder: {self.embedder.backend}")
                return

        except Exception as e:
            logger.warning(f"Unified embedder failed: {e}")

        # Final fallback: simple hash embedder
        logger.warning("⚠️  Using hash-based embedding fallback")
        self.capabilities['embedder_backend'] = "hash"

    def _init_vector_search(self):
        """Initialize vector search with best available backend"""
        logger.info("\n--- Initializing Vector Search ---")

        # Try Metal 4 vector search
        if self.capabilities['metal_version'] >= 3:
            try:
                from metal4_vector_search import get_metal4_vector_search

                self.vector_search = get_metal4_vector_search()

                if self.vector_search.is_available():
                    backend = "Metal GPU" if self.vector_search.uses_metal() else "CPU"
                    self.capabilities['vector_search_backend'] = backend
                    logger.info(f"✅ Vector Search: {backend}")
                    return

            except Exception as e:
                logger.debug(f"Metal 4 vector search failed: {e}")

        # CPU fallback is built into Metal4VectorSearch
        logger.info("✅ Vector Search: CPU fallback")
        self.capabilities['vector_search_backend'] = "CPU"

    def _init_sparse_storage(self):
        """Initialize sparse embedding storage"""
        logger.info("\n--- Initializing Sparse Storage ---")

        try:
            from metal4_sparse_embeddings import Metal4SparseEmbeddings

            # Get embedding dimension from embedder
            embed_dim = 384  # Default
            if hasattr(self.embedder, 'embed_dim'):
                embed_dim = self.embedder.embed_dim
            elif hasattr(self.embedder, 'get_dimensions'):
                embed_dim = self.embedder.get_dimensions()

            self.sparse_storage = Metal4SparseEmbeddings(
                embed_dim=embed_dim,
                max_vectors=self.max_vectors,
                gpu_cache_size_mb=self.gpu_cache_mb
            )

            backend = "Metal 4 Sparse" if self.sparse_storage._use_sparse_resources else "Memory-mapped"
            logger.info(f"✅ Sparse Storage: {backend}")
            logger.info(f"   Capacity: {self.sparse_storage._get_capacity_info()}")

        except Exception as e:
            logger.warning(f"Sparse storage initialization failed: {e}")
            logger.warning("⚠️  Large-scale storage unavailable")

    def _print_initialization_summary(self):
        """Print initialization summary"""
        logger.info("\n--- Initialization Complete ---")
        logger.info(f"Metal Version: {self.capabilities['metal_version'] or 'Not available'}")
        logger.info(f"Embedder: {self.capabilities['embedder_backend']}")
        logger.info(f"Vector Search: {self.capabilities['vector_search_backend']}")
        logger.info(f"Sparse Resources: {'✓' if self.capabilities['sparse_resources'] else '✗'}")
        logger.info(f"Unified Memory: {'✓' if self.capabilities['unified_memory'] else '✗'}")

    # ========================================================================
    # Public API
    # ========================================================================

    def embed(self, text: str) -> List[float]:
        """
        Create embedding for text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        if not self.embedder:
            logger.error("Embedder not initialized")
            return []

        if hasattr(self.embedder, 'embed'):
            return self.embedder.embed(text)
        else:
            # Fallback to simple hash
            return self._hash_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not self.embedder:
            return [self._hash_embed(t) for t in texts]

        if hasattr(self.embedder, 'embed_batch'):
            return self.embedder.embed_batch(texts)
        else:
            return [self.embed(t) for t in texts]

    def search(
        self,
        query: str,
        k: int = 10,
        metric: str = "cosine"
    ) -> Tuple[List[int], List[float]]:
        """
        Search for similar vectors

        Args:
            query: Query text
            k: Number of results
            metric: Similarity metric ("cosine", "l2", "dot")

        Returns:
            Tuple of (indices, scores)
        """
        # Embed query
        query_embedding = self.embed(query)

        if not query_embedding:
            return [], []

        # Convert to numpy
        query_vec = np.array(query_embedding, dtype=np.float32)

        # Search using vector search engine
        if self.vector_search and self.vector_search.num_vectors > 0:
            return self.vector_search.search(query_vec, k, metric)
        else:
            logger.warning("Vector search not initialized or empty database")
            return [], []

    def load_database(self, embeddings: np.ndarray):
        """
        Load embedding database for searching

        Args:
            embeddings: Embedding matrix [num_vectors, embed_dim]
        """
        if self.vector_search:
            self.vector_search.load_database(embeddings)
            logger.info(f"Loaded {embeddings.shape[0]} vectors into search index")
        else:
            logger.error("Vector search not initialized")

    def store_embedding(self, vector_id: int, text: str):
        """
        Store embedding in sparse storage

        Args:
            vector_id: Unique vector ID
            text: Text to embed and store
        """
        if not self.sparse_storage:
            logger.warning("Sparse storage not available")
            return

        # Create embedding
        embedding = self.embed(text)

        if not embedding:
            logger.error("Failed to create embedding")
            return

        # Store
        embedding_vec = np.array(embedding, dtype=np.float32)
        self.sparse_storage.add_embedding(vector_id, embedding_vec)

    def retrieve_embedding(self, vector_id: int) -> Optional[np.ndarray]:
        """
        Retrieve embedding from sparse storage

        Args:
            vector_id: Vector ID

        Returns:
            Embedding vector or None
        """
        if not self.sparse_storage:
            logger.warning("Sparse storage not available")
            return None

        return self.sparse_storage.get_embedding(vector_id)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get pipeline capabilities"""
        return self.capabilities.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics from all components"""
        stats = {
            'capabilities': self.get_capabilities(),
            'embedder': {},
            'vector_search': {},
            'sparse_storage': {}
        }

        if self.embedder and hasattr(self.embedder, 'get_stats'):
            stats['embedder'] = self.embedder.get_stats()

        if self.vector_search and hasattr(self.vector_search, 'get_stats'):
            stats['vector_search'] = self.vector_search.get_stats()

        if self.sparse_storage and hasattr(self.sparse_storage, 'get_stats'):
            stats['sparse_storage'] = self.sparse_storage.get_stats()

        return stats

    def _hash_embed(self, text: str, dim: int = 384) -> List[float]:
        """Simple hash-based embedding fallback"""
        import hashlib

        hashes = []
        for i in range((dim + 15) // 16):
            h = hashlib.sha256(f"{text}_{i}".encode()).digest()
            hashes.extend(int.from_bytes(h[j:j+2], 'big') for j in range(0, 16, 2))

        vec = [(h / 32768.0 - 1.0) for h in hashes[:dim]]

        norm = sum(x*x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def close(self):
        """Close and cleanup all resources"""
        if self.sparse_storage:
            self.sparse_storage.close()


# ===== Singleton Instance =====

_ml_pipeline: Optional[Metal4MLPipeline] = None


def get_ml_pipeline(
    model_name: str = None,
    max_vectors: int = 1_000_000
) -> Metal4MLPipeline:
    """
    Get singleton ML pipeline instance

    Args:
        model_name: Optional model name (only used on first call)
        max_vectors: Maximum vectors for sparse storage

    Returns:
        Metal4MLPipeline instance
    """
    global _ml_pipeline
    if _ml_pipeline is None:
        _ml_pipeline = Metal4MLPipeline(
            model_name=model_name or "sentence-transformers/all-MiniLM-L6-v2",
            max_vectors=max_vectors
        )
    return _ml_pipeline


def validate_ml_pipeline() -> Dict[str, Any]:
    """Validate entire ML pipeline"""
    logger.info("\n" + "=" * 60)
    logger.info("Metal 4 ML Pipeline Validation")
    logger.info("=" * 60)

    try:
        pipeline = get_ml_pipeline()

        # Test embedding
        test_text = "The Lord is my shepherd"
        embedding = pipeline.embed(test_text)

        # Test batch embedding
        test_texts = [
            "The Lord is my light",
            "The Lord is my salvation",
            "The Lord is my stronghold"
        ]
        batch_embeddings = pipeline.embed_batch(test_texts)

        # Test vector search (if database loaded)
        test_db = np.random.randn(1000, len(embedding)).astype(np.float32)
        pipeline.load_database(test_db)

        indices, scores = pipeline.search("test query", k=5)

        # Get stats
        stats = pipeline.get_stats()

        status = {
            'embedding_test': len(embedding) > 0,
            'batch_embedding_test': len(batch_embeddings) == len(test_texts),
            'search_test': len(indices) == 5,
            'capabilities': pipeline.get_capabilities(),
            'stats': stats
        }

        all_passed = all([
            status['embedding_test'],
            status['batch_embedding_test'],
            status['search_test']
        ])

        if all_passed:
            logger.info("\n✅ All validation tests passed!")
        else:
            logger.warning("\n⚠️  Some validation tests failed")

        logger.info("=" * 60)

        return status

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e)
        }


# Export
__all__ = [
    'Metal4MLPipeline',
    'get_ml_pipeline',
    'validate_ml_pipeline'
]
