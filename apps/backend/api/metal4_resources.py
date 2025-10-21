#!/usr/bin/env python3
"""
Metal 4 Resource Management
Handles buffers, tensors, and unified memory heap allocations

"The Lord is my rock, my firm foundation." - Psalm 18:2
"""

import logging
from typing import Optional, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class BufferType(Enum):
    """Types of Metal buffers for different use cases"""
    EMBEDDINGS = "embeddings"      # Embedding vectors (NxD float32)
    TEXT_TOKENS = "text_tokens"    # Tokenized text (NxM int32)
    RAG_CONTEXT = "rag_context"    # RAG retrieved context
    SQL_RESULTS = "sql_results"    # Database query results
    UI_VERTICES = "ui_vertices"    # UI rendering data
    STAGING = "staging"            # Temporary upload/download


class Metal4ResourceManager:
    """
    Manages Metal 4 unified memory resources

    Features:
    - Zero-copy buffer allocation from shared heap
    - Tensor management for ML operations
    - Automatic memory pressure tracking
    - Sparse resource allocation (Metal 4)
    """

    def __init__(self, engine):
        """
        Initialize resource manager

        Args:
            engine: Metal4Engine instance with initialized device and heap
        """
        self.engine = engine
        self.device = engine.device
        self.heap = engine.H_main

        # Resource tracking
        self.allocated_buffers = {}
        self.buffer_sizes = {}
        self.total_allocated = 0

        # Default sizes (in bytes) - optimized for 128GB system
        self.default_sizes = {
            BufferType.EMBEDDINGS: 1024 * 384 * 4,      # 1K vectors x 384 dims x float32
            BufferType.TEXT_TOKENS: 1024 * 512 * 4,     # 1K sequences x 512 tokens x int32
            BufferType.RAG_CONTEXT: 1024 * 1024,        # 1MB context buffer
            BufferType.SQL_RESULTS: 10 * 1024 * 1024,   # 10MB results buffer
            BufferType.UI_VERTICES: 256 * 1024,         # 256KB vertices
            BufferType.STAGING: 1024 * 1024             # 1MB staging
        }

        logger.info("✅ Metal4ResourceManager initialized")
        logger.info(f"   Heap size: {self.heap.size() / (1024**2):.2f} MB")
        logger.info(f"   Heap used: {self.heap.usedSize() / (1024**2):.2f} MB")

    def allocate_buffer(
        self,
        buffer_type: BufferType,
        size: Optional[int] = None,
        label: Optional[str] = None
    ):
        """
        Allocate a Metal buffer from the unified memory heap

        Args:
            buffer_type: Type of buffer to allocate
            size: Size in bytes (uses default if None)
            label: Optional debug label

        Returns:
            MTLBuffer or None if allocation fails
        """
        try:
            import Metal

            # Get size
            alloc_size = size if size is not None else self.default_sizes.get(buffer_type, 1024*1024)

            # Allocate from device with unified memory (zero-copy)
            # Note: Direct device allocation is simpler than heap placement for now
            buffer = self.device.newBufferWithLength_options_(
                alloc_size,
                Metal.MTLResourceStorageModeShared  # Unified memory - CPU and GPU both access
            )

            if buffer is None:
                logger.error(f"❌ Failed to allocate {buffer_type.value} buffer ({alloc_size} bytes)")
                return None

            # Set label for debugging
            if label:
                buffer.setLabel_(label)
            else:
                buffer.setLabel_(f"{buffer_type.value}_buffer")

            # Track allocation
            buffer_id = id(buffer)
            self.allocated_buffers[buffer_id] = buffer
            self.buffer_sizes[buffer_id] = alloc_size
            self.total_allocated += alloc_size

            logger.debug(f"✓ Allocated {buffer_type.value}: {alloc_size / 1024:.2f} KB")
            logger.debug(f"  Total allocated: {self.total_allocated / (1024**2):.2f} MB")

            return buffer

        except Exception as e:
            logger.error(f"❌ Buffer allocation failed: {e}")
            return None

    def allocate_tensor_buffer(
        self,
        shape: Tuple[int, ...],
        dtype_size: int = 4,
        label: Optional[str] = None
    ):
        """
        Allocate a buffer for tensor data

        Args:
            shape: Tensor shape (e.g., (batch, dim))
            dtype_size: Bytes per element (4 for float32, 2 for float16)
            label: Optional debug label

        Returns:
            MTLBuffer or None
        """
        # Calculate size
        num_elements = 1
        for dim in shape:
            num_elements *= dim

        size = num_elements * dtype_size

        return self.allocate_buffer(
            BufferType.EMBEDDINGS,
            size=size,
            label=label or f"tensor_{'x'.join(map(str, shape))}"
        )

    def release_buffer(self, buffer):
        """
        Release a buffer (Python wrapper - Metal handles actual deallocation)

        Args:
            buffer: MTLBuffer to release
        """
        buffer_id = id(buffer)

        if buffer_id in self.allocated_buffers:
            size = self.buffer_sizes[buffer_id]
            del self.allocated_buffers[buffer_id]
            del self.buffer_sizes[buffer_id]
            self.total_allocated -= size

            logger.debug(f"✓ Released buffer: {size / 1024:.2f} KB")
            logger.debug(f"  Total allocated: {self.total_allocated / (1024**2):.2f} MB")

    def get_memory_stats(self):
        """Get current memory usage statistics"""
        return {
            'heap_size_mb': self.heap.size() / (1024**2),
            'heap_used_mb': self.heap.usedSize() / (1024**2),
            'tracked_allocations': len(self.allocated_buffers),
            'tracked_allocated_mb': self.total_allocated / (1024**2),
            'heap_utilization_pct': (self.heap.usedSize() / self.heap.size()) * 100
        }

    def create_embedding_buffers(self, batch_size: int = 64, embed_dim: int = 384):
        """
        Create buffers for embedding pipeline

        Args:
            batch_size: Number of texts to embed in parallel
            embed_dim: Embedding dimension

        Returns:
            dict with input and output buffers
        """
        return {
            'input_tokens': self.allocate_tensor_buffer(
                (batch_size, 512),  # batch x max_seq_length
                dtype_size=4,  # int32
                label="embed_input_tokens"
            ),
            'output_embeddings': self.allocate_tensor_buffer(
                (batch_size, embed_dim),  # batch x embedding_dim
                dtype_size=4,  # float32
                label="embed_output_vectors"
            )
        }

    def create_rag_buffers(self, num_vectors: int = 1000, vector_dim: int = 384):
        """
        Create buffers for RAG vector search

        Args:
            num_vectors: Number of vectors in index
            vector_dim: Vector dimension

        Returns:
            dict with query and results buffers
        """
        return {
            'query_vector': self.allocate_tensor_buffer(
                (1, vector_dim),
                dtype_size=4,
                label="rag_query_vector"
            ),
            'vector_index': self.allocate_tensor_buffer(
                (num_vectors, vector_dim),
                dtype_size=4,
                label="rag_vector_index"
            ),
            'similarity_scores': self.allocate_tensor_buffer(
                (num_vectors,),
                dtype_size=4,
                label="rag_similarity_scores"
            )
        }


# Global instance
_resource_manager: Optional[Metal4ResourceManager] = None


def get_resource_manager():
    """Get singleton resource manager instance"""
    global _resource_manager

    if _resource_manager is None:
        from metal4_engine import get_metal4_engine
        engine = get_metal4_engine()

        if not engine.is_available() or engine.H_main is None:
            logger.warning("Metal4Engine not available - resource manager disabled")
            return None

        _resource_manager = Metal4ResourceManager(engine)

    return _resource_manager


__all__ = [
    'Metal4ResourceManager',
    'BufferType',
    'get_resource_manager'
]
