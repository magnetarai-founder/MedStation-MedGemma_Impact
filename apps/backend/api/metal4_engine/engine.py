"""
Metal 4 Unified Command Queue Engine

Manages three specialized queues:
- Q_render: Graphics/UI (60fps, never blocks)
- Q_ml: ML/Compute (embeddings, inference, SQL)
- Q_blit: Async transfers (background I/O)

Uses event-based synchronization for zero-overhead coordination.
"""

import logging
from collections.abc import Callable
from typing import Any

from api.metal4_engine.capabilities import (
    MetalVersion,
    MetalCapabilities,
    detect_metal_capabilities,
)

logger = logging.getLogger(__name__)


class Metal4Engine:
    """
    Unified Metal 4 command queue engine

    Manages three specialized queues:
    - Q_render: Graphics/UI (60fps, never blocks)
    - Q_ml: ML/Compute (embeddings, inference, SQL)
    - Q_blit: Async transfers (background I/O)

    Uses event-based synchronization for zero-overhead coordination
    """

    def __init__(self):
        """Initialize Metal 4 engine with capability detection"""
        self.capabilities = detect_metal_capabilities()
        self._initialized = False

        # Queue handles (will be initialized if Metal 4 available)
        self.Q_render = None
        self.Q_ml = None
        self.Q_blit = None

        # Synchronization primitives
        self.E_frame = None  # Frame heartbeat
        self.E_data = None   # Data ready
        self.E_embed = None  # Embeddings ready
        self.E_rag = None    # RAG context ready

        # Event counters
        self.frame_counter = 0
        self.embed_counter = 0
        self.rag_counter = 0

        # Resource heaps
        self.H_main = None  # Main shared heap

        # Stats
        self.stats = {
            'frames_rendered': 0,
            'ml_operations': 0,
            'blit_operations': 0,
            'active_command_buffers': 0
        }

        # Initialization error tracking (for user notification)
        self.initialization_error: str | None = None

        # Try to initialize if Metal 4 available
        if self.capabilities.version == MetalVersion.METAL_4:
            self._initialize_metal4()
        elif self.capabilities.version.value >= MetalVersion.METAL_3.value:
            self._initialize_metal3_fallback()
        else:
            logger.warning("Metal 4 not available - using CPU fallback")
            self.initialization_error = "Metal 4 not available on this system"

    def _initialize_metal4(self) -> None:
        """
        Initialize full Metal 4 pipeline with unified command queues

        NOW USING REAL METAL APIs VIA PyObjC!
        """
        try:
            import Metal

            # Create Metal device
            device = Metal.MTLCreateSystemDefaultDevice()
            if device is None:
                logger.error("Failed to create Metal device")
                logger.error("CRITICAL: GPU acceleration unavailable - falling back to CPU")
                logger.error("Performance will be severely degraded for AI operations")
                self.initialization_error = "Metal device creation failed - GPU unavailable"
                return

            self.device = device

            # Create three specialized command queues (Metal 4 architecture)
            self.Q_render = device.newCommandQueue()  # Graphics/UI (60fps, never blocks)
            self.Q_ml = device.newCommandQueue()      # ML/Compute (embeddings, inference, SQL)
            self.Q_blit = device.newCommandQueue()    # Async transfers (background I/O)

            if not all([self.Q_render, self.Q_ml, self.Q_blit]):
                logger.error("Failed to create command queues")
                return

            # Create shared events for synchronization (Metal 3+ feature)
            self.E_frame = device.newSharedEvent()  # Frame heartbeat (UI tick)
            self.E_data = device.newSharedEvent()   # Data ready
            self.E_embed = device.newSharedEvent()  # Embeddings ready
            self.E_rag = device.newSharedEvent()    # RAG context ready

            if not all([self.E_frame, self.E_data, self.E_embed, self.E_rag]):
                logger.error("Failed to create shared events")
                return

            # Create unified memory heap (Metal 4 placement resources)
            heap_desc = Metal.MTLHeapDescriptor.alloc().init()
            heap_size_mb = self.capabilities.recommended_heap_size_mb
            heap_desc.setSize_(heap_size_mb * 1024 * 1024)  # Convert MB to bytes
            heap_desc.setStorageMode_(Metal.MTLStorageModeShared)  # Unified memory

            # Try to use Metal 4 placement heaps for sparse allocation
            try:
                heap_desc.setType_(Metal.MTLHeapTypePlacement)
                logger.info("   Using Metal 4 placement heaps (sparse allocation)")
            except AttributeError:
                logger.warning("   Metal 4 placement heaps not available - using automatic")

            self.H_main = device.newHeapWithDescriptor_(heap_desc)

            if self.H_main is None:
                logger.warning("Failed to create heap - zero-copy features disabled")

            self._initialized = True

            logger.info("Metal 4 engine initialized with REAL Metal APIs")
            logger.info(f"   Device: {device.name()}")
            logger.info(f"   Unified Memory: {self.capabilities.supports_unified_memory}")
            logger.info(f"   Max Buffer: {device.maxBufferLength() / (1024**3):.2f} GB")
            logger.info(f"   Heap Size: {heap_size_mb} MB")
            logger.info(f"   Command Queues: Q_render, Q_ml, Q_blit")
            logger.info(f"   Shared Events: E_frame, E_data, E_embed, E_rag")
            logger.info(f"   ML Command Encoder: {self.capabilities.supports_ml_command_encoder}")

        except ImportError as e:
            logger.error(f"Metal framework not available: {e}")
            logger.error("   Install with: pip install pyobjc-framework-Metal")
            logger.error("CRITICAL: GPU acceleration unavailable - falling back to CPU")
            self.initialization_error = f"Metal framework not available: {e}"
        except Exception as e:
            logger.error(f"Metal 4 initialization failed: {e}")
            logger.error("CRITICAL: GPU acceleration unavailable - falling back to CPU")
            import traceback
            traceback.print_exc()
            self.initialization_error = f"Metal 4 initialization failed: {e}"

    def _initialize_metal3_fallback(self) -> None:
        """Initialize with Metal 3 fallback (basic MPS)"""
        try:
            import torch

            if torch.backends.mps.is_available():
                self._initialized = True
                logger.info("Metal 3 fallback initialized (basic MPS)")
            else:
                logger.warning("MPS not available")

        except ImportError:
            logger.warning("PyTorch not available")

    def is_available(self) -> bool:
        """Check if Metal 4 engine is available and initialized"""
        return self._initialized

    def get_device(self) -> str:
        """
        Get optimal device for ML operations

        Returns:
            "mps" for Metal, "cuda" for NVIDIA, "cpu" for fallback
        """
        if not self._initialized:
            return "cpu"

        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        return "cpu"

    def get_capabilities_dict(self) -> dict[str, Any]:
        """Get capabilities as dictionary for API response"""
        return {
            'available': self.capabilities.available,
            'version': self.capabilities.version.value,
            'device_name': self.capabilities.device_name,
            'is_apple_silicon': self.capabilities.is_apple_silicon,
            'features': {
                'unified_memory': self.capabilities.supports_unified_memory,
                'mps': self.capabilities.supports_mps,
                'ane': self.capabilities.supports_ane,
                'sparse_resources': self.capabilities.supports_sparse_resources,
                'ml_command_encoder': self.capabilities.supports_ml_command_encoder
            },
            'memory': {
                'max_buffer_mb': self.capabilities.max_buffer_size_mb,
                'recommended_heap_mb': self.capabilities.recommended_heap_size_mb
            },
            'initialized': self._initialized
        }

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics"""
        return {
            **self.stats,
            'device': self.get_device(),
            'capabilities': self.get_capabilities_dict()
        }

    # ========================================================================
    # TICK FLOW - Metal 4 Unified Command Buffer Architecture
    # ========================================================================

    def kick_frame(self) -> None:
        """
        Start new frame - signal all queues

        This is the heartbeat of the Metal 4 architecture.
        Call this at the start of each UI frame or operation tick.
        """
        if not self._initialized or not self.Q_render or not self.E_frame:
            return

        try:
            # Create command buffer on render queue
            cmd = self.Q_render.commandBuffer()

            # Signal frame event to wake up all dependent operations
            cmd.encodeSignalEvent_value_(self.E_frame, self.frame_counter)

            # Commit (non-blocking)
            cmd.commit()

            # Increment frame counter
            self.frame_counter += 1
            self.stats['frames_rendered'] += 1

            # Only log every 100 frames to reduce I/O overhead
            if self.frame_counter % 100 == 0:
                logger.debug(f"Frame {self.frame_counter} kicked")

        except Exception as e:
            logger.error(f"Failed to kick frame: {e}")

    def process_chat_message(
        self,
        user_message: str,
        embedder: Callable[[str], Any] | None = None,
        rag_retriever: Callable[[Any], Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Full chat pipeline on ML queue with event-based synchronization

        Pipeline:
        1. Wait for frame to start
        2. Embed user message
        3. Signal embeddings ready
        4. Retrieve RAG context
        5. Signal RAG ready
        6. Generate response (would integrate with Ollama/etc)

        Args:
            user_message: User's chat message
            embedder: Embedding function (text -> vector)
            rag_retriever: RAG retrieval function (vector -> context)

        Returns:
            dict with embedding, context, and timing info
        """
        if not self._initialized or not self.Q_ml:
            logger.warning("Metal 4 not available - using CPU fallback")
            return self._process_chat_cpu_fallback(user_message, embedder, rag_retriever)

        try:
            import time
            start_time = time.time()

            # Create command buffer on ML queue
            cmd = self.Q_ml.commandBuffer()

            # WAIT for frame to start (ensures sync with UI)
            cmd.encodeWaitForEvent_value_(self.E_frame, self.frame_counter)

            # ===== STEP 1: EMBED MESSAGE =====
            # For now, we'll do this on CPU and copy to GPU
            # (Full Metal embedding implementation in Week 2)
            embedding = None
            if embedder:
                embedding = embedder(user_message)

            # SIGNAL embeddings ready
            self.embed_counter += 1
            cmd.encodeSignalEvent_value_(self.E_embed, self.embed_counter)

            # ===== STEP 2: RAG RETRIEVAL =====
            # Wait for embeddings to be ready
            cmd.encodeWaitForEvent_value_(self.E_embed, self.embed_counter)

            # Retrieve context (CPU for now)
            context = None
            if rag_retriever and embedding:
                context = rag_retriever(embedding)

            # SIGNAL RAG ready
            self.rag_counter += 1
            cmd.encodeSignalEvent_value_(self.E_rag, self.rag_counter)

            # Commit the command buffer (executes all operations)
            cmd.commit()

            # Wait for completion (in real usage, this would be async)
            cmd.waitUntilCompleted()

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats['ml_operations'] += 1

            # Only log slow operations (>100ms) to reduce noise
            if elapsed_ms > 100:
                logger.info(f"Chat message processed in {elapsed_ms:.2f}ms")
                logger.info(f"   Frame: {self.frame_counter}, Embed: {self.embed_counter}, RAG: {self.rag_counter}")

            # Record diagnostics
            try:
                from metal4_diagnostics import get_diagnostics
                diag = get_diagnostics()
                if diag:
                    diag.record_operation('embeddings', elapsed_ms, 'ml')
            except (ImportError, AttributeError):
                pass  # Diagnostics not available

            return {
                'embedding': embedding,
                'context': context,
                'elapsed_ms': elapsed_ms,
                'frame_counter': self.frame_counter,
                'embed_counter': self.embed_counter,
                'rag_counter': self.rag_counter
            }

        except Exception as e:
            logger.error(f"Chat message processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_chat_cpu_fallback(
        self,
        user_message: str,
        embedder: Callable[[str], Any] | None,
        rag_retriever: Callable[[Any], Any] | None
    ) -> dict[str, Any]:
        """CPU fallback when Metal not available"""
        import time
        start_time = time.time()

        embedding = embedder(user_message) if embedder else None
        context = rag_retriever(embedding) if (rag_retriever and embedding) else None

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            'embedding': embedding,
            'context': context,
            'elapsed_ms': elapsed_ms,
            'fallback': True
        }

    def process_sql_query(
        self,
        sql: str,
        embedder: Callable[[str], Any] | None = None
    ) -> dict[str, Any] | None:
        """
        DuckDB query + embedding on ML queue
        Runs in parallel with UI and chat!

        Pipeline:
        1. Wait for frame
        2. Execute SQL query (CPU for now)
        3. Embed results while UI continues
        4. Signal embeddings ready

        Args:
            sql: SQL query string
            embedder: Function to embed result rows

        Returns:
            dict with results, embeddings, and timing
        """
        if not self._initialized or not self.Q_ml:
            return self._process_sql_cpu_fallback(sql, embedder)

        try:
            import time
            start_time = time.time()

            # Create command buffer on ML queue
            cmd = self.Q_ml.commandBuffer()

            # WAIT for frame
            cmd.encodeWaitForEvent_value_(self.E_frame, self.frame_counter)

            # ===== STEP 1: EXECUTE SQL =====
            # (GPU kernels for SQL would go here in Week 3)
            # For now, execute on CPU
            results = None
            try:
                import duckdb
                conn = duckdb.connect(':memory:')
                results = conn.execute(sql).fetchall()
                logger.debug(f"SQL executed: {len(results)} rows")
            except Exception as e:
                logger.error(f"SQL execution failed: {e}")

            # ===== STEP 2: EMBED RESULTS =====
            embeddings = None
            if embedder and results:
                # Convert results to text and embed
                result_texts = [str(row) for row in results[:100]]  # Limit for now
                embeddings = [embedder(text) for text in result_texts]
                logger.debug(f"Embedded {len(embeddings)} result rows")

            # SIGNAL embeddings ready
            self.embed_counter += 1
            cmd.encodeSignalEvent_value_(self.E_embed, self.embed_counter)

            # Commit
            cmd.commit()
            cmd.waitUntilCompleted()

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats['ml_operations'] += 1

            logger.info(f"SQL query processed in {elapsed_ms:.2f}ms")

            return {
                'results': results,
                'embeddings': embeddings,
                'elapsed_ms': elapsed_ms,
                'frame_counter': self.frame_counter,
                'embed_counter': self.embed_counter
            }

        except Exception as e:
            logger.error(f"SQL query processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_sql_cpu_fallback(
        self,
        sql: str,
        embedder: Callable[[str], Any] | None
    ) -> dict[str, Any]:
        """CPU fallback for SQL processing"""
        import time
        start_time = time.time()

        results = None
        try:
            import duckdb
            conn = duckdb.connect(':memory:')
            results = conn.execute(sql).fetchall()
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")

        embeddings = None
        if embedder and results:
            result_texts = [str(row) for row in results[:100]]
            embeddings = [embedder(text) for text in result_texts]

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            'results': results,
            'embeddings': embeddings,
            'elapsed_ms': elapsed_ms,
            'fallback': True
        }

    def render_ui_frame(self, rag_ready: bool = False) -> dict[str, Any]:
        """
        Render UI with last-known data
        NEVER waits for ML to complete!

        Args:
            rag_ready: Whether to check if RAG data is ready

        Returns:
            dict with render stats
        """
        if not self._initialized or not self.Q_render:
            return {'rendered': False, 'fallback': True}

        try:
            import time
            start_time = time.time()

            # Create command buffer on render queue
            cmd = self.Q_render.commandBuffer()

            # WAIT for frame heartbeat only (never wait for ML!)
            cmd.encodeWaitForEvent_value_(self.E_frame, self.frame_counter)

            # Check if RAG data is ready (non-blocking check)
            rag_available = False
            if rag_ready and self.E_rag:
                current_rag = self.E_rag.signaledValue()
                rag_available = current_rag >= self.rag_counter

                if rag_available:
                    logger.debug("RAG data available - rendering with context")
                else:
                    logger.debug("RAG not ready yet - rendering placeholder")

            # In real implementation, would encode render commands here
            # For now, just track the frame

            # Commit
            cmd.commit()
            cmd.waitUntilCompleted()

            elapsed_ms = (time.time() - start_time) * 1000
            self.stats['frames_rendered'] += 1

            # Record frame time in diagnostics
            try:
                from metal4_diagnostics import get_diagnostics
                diag = get_diagnostics()
                if diag:
                    diag.record_frame()
            except (ImportError, AttributeError):
                pass  # Diagnostics not available

            return {
                'rendered': True,
                'rag_available': rag_available,
                'frame_time_ms': elapsed_ms,
                'frame_counter': self.frame_counter
            }

        except Exception as e:
            logger.error(f"UI render failed: {e}")
            return {'rendered': False, 'error': str(e)}

    def async_memory_operations(self, source_buffer: Any, dest_buffer: Any) -> Any | None:
        """
        Background transfers - keep off critical path
        Uses Q_blit for async data movement

        Args:
            source_buffer: Source MTLBuffer
            dest_buffer: Destination MTLBuffer

        Returns:
            Command buffer for async tracking
        """
        if not self._initialized or not self.Q_blit:
            return None

        try:
            # Create command buffer on blit queue
            cmd = self.Q_blit.commandBuffer()

            # Create blit encoder
            blit_encoder = cmd.blitCommandEncoder()

            # Copy data (async - happens in background)
            min_length = min(source_buffer.length(), dest_buffer.length())
            blit_encoder.copyFromBuffer_sourceOffset_toBuffer_destinationOffset_size_(
                source_buffer, 0,
                dest_buffer, 0,
                min_length
            )

            blit_encoder.endEncoding()

            # Commit (non-blocking)
            cmd.commit()

            self.stats['blit_operations'] += 1
            logger.debug(f"Async blit queued: {min_length / 1024:.2f} KB")

            return cmd

        except Exception as e:
            logger.error(f"Async blit failed: {e}")
            return None

    # ========================================================================
    # END TICK FLOW
    # ========================================================================

    def optimize_for_operation(self, operation_type: str) -> dict[str, Any]:
        """
        Get optimization settings for specific operation

        Args:
            operation_type: 'embedding', 'inference', 'sql', 'render'

        Returns:
            Optimization settings dict
        """
        base_settings = {
            'device': self.get_device(),
            'use_fp16': self.capabilities.is_apple_silicon,
            'batch_size': 32
        }

        if operation_type == 'embedding':
            return {
                **base_settings,
                'use_mps_graph': self.capabilities.version.value >= MetalVersion.METAL_4.value,
                'use_unified_memory': self.capabilities.supports_unified_memory,
                'batch_size': 64
            }

        elif operation_type == 'inference':
            return {
                **base_settings,
                'use_ml_encoder': self.capabilities.supports_ml_command_encoder,
                'use_ane': self.capabilities.supports_ane,
                'stream_tokens': True
            }

        elif operation_type == 'sql':
            return {
                **base_settings,
                'use_gpu_kernels': self.capabilities.version.value >= MetalVersion.METAL_4.value,
                'use_sparse_resources': self.capabilities.supports_sparse_resources,
                'parallel_aggregations': True
            }

        elif operation_type == 'render':
            return {
                **base_settings,
                'target_fps': 60,
                'never_block': True,
                'use_ring_buffer': True
            }

        return base_settings
