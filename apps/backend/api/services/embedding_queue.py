"""
Batch Embedding Queue for 3-5x Throughput

Queues embedding requests and processes them in batches for optimal efficiency.
Instead of generating embeddings one-by-one, this batches them and generates
32 embeddings at once, reducing model inference overhead.

Usage:
    from api.services.embedding_queue import get_embedding_queue

    queue = get_embedding_queue()
    embedding = await queue.enqueue("text to embed")
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class EmbeddingBatchQueue:
    """
    Batches embedding requests for 3-5x higher throughput.

    Features:
    - Automatic batching up to batch_size embeddings
    - Time-based flushing (max_wait_ms) to prevent latency
    - Graceful error handling per-request
    - Background processing task
    """

    def __init__(
        self,
        embedding_fn: Callable[[list[str]], list[list[float]]],
        batch_size: int = 32,
        max_wait_ms: int = 100,
    ):
        """
        Initialize embedding batch queue.

        Args:
            embedding_fn: Async function that generates embeddings for a batch
            batch_size: Maximum batch size (default: 32)
            max_wait_ms: Maximum wait time before processing batch (default: 100ms)
        """
        self.embedding_fn = embedding_fn
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms / 1000.0  # Convert to seconds

        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.processor_task: asyncio.Task | None = None

        # Metrics
        self.total_requests = 0
        self.total_batches = 0
        self.total_batch_time = 0.0

    async def start(self):
        """Start the background batch processor"""
        if self.running:
            logger.warning("Embedding queue already running")
            return

        self.running = True
        self.processor_task = asyncio.create_task(self._process_batches())
        logger.info(
            f"Started embedding batch queue (batch_size={self.batch_size}, "
            f"max_wait={self.max_wait_ms*1000}ms)"
        )

    async def stop(self):
        """Stop the background batch processor"""
        if not self.running:
            return

        self.running = False
        if self.processor_task:
            # Process remaining items
            await self.queue.join()
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"Stopped embedding queue - Processed {self.total_requests} requests "
            f"in {self.total_batches} batches "
            f"(avg batch time: {self.total_batch_time/max(self.total_batches, 1):.2f}s)"
        )

    async def enqueue(self, text: str) -> list[float]:
        """
        Queue text for embedding generation.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            RuntimeError: If queue is not running
        """
        if not self.running:
            raise RuntimeError("Embedding queue not running. Call start() first.")

        # Create a future to wait for the result
        future: asyncio.Future[list[float]] = asyncio.Future()

        # Add to queue
        await self.queue.put((text, future))
        self.total_requests += 1

        # Wait for result
        return await future

    async def _process_batches(self):
        """Background task that processes batches"""
        logger.info("Embedding batch processor started")

        while self.running:
            try:
                batch = await self._collect_batch()

                if not batch:
                    # No items collected, sleep briefly
                    await asyncio.sleep(0.01)
                    continue

                # Process batch
                await self._process_batch(batch)

            except asyncio.CancelledError:
                logger.info("Embedding processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}", exc_info=True)
                await asyncio.sleep(0.1)

    async def _collect_batch(self) -> list[tuple[str, asyncio.Future]]:
        """
        Collect a batch of requests.

        Returns:
            List of (text, future) tuples
        """
        batch = []
        deadline = time.time() + self.max_wait_ms

        while len(batch) < self.batch_size:
            timeout = max(0, deadline - time.time())

            if timeout <= 0:
                # Deadline reached
                break

            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                batch.append(item)
            except asyncio.TimeoutError:
                # Timeout reached, process what we have
                break

        return batch

    async def _process_batch(self, batch: list[tuple[str, asyncio.Future]]):
        """
        Process a batch of embedding requests.

        Args:
            batch: List of (text, future) tuples
        """
        if not batch:
            return

        start_time = time.time()
        texts = [text for text, _ in batch]
        futures = [future for _, future in batch]

        try:
            # Generate embeddings in batch
            embeddings = await self.embedding_fn(texts)

            # Set results
            for future, embedding in zip(futures, embeddings, strict=False):
                if not future.done():
                    future.set_result(embedding)

            # Mark tasks as done
            for _ in batch:
                self.queue.task_done()

            # Update metrics
            self.total_batches += 1
            batch_time = time.time() - start_time
            self.total_batch_time += batch_time

            logger.debug(
                f"Processed batch of {len(batch)} embeddings in {batch_time:.3f}s "
                f"({len(batch)/batch_time:.1f} embeddings/sec)"
            )

        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)

            # Set error for all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)

            # Mark tasks as done even on error
            for _ in batch:
                self.queue.task_done()

    def get_metrics(self) -> dict[str, Any]:
        """Get queue metrics"""
        avg_batch_size = self.total_requests / max(self.total_batches, 1)
        avg_batch_time = self.total_batch_time / max(self.total_batches, 1)

        return {
            "running": self.running,
            "queue_size": self.queue.qsize(),
            "total_requests": self.total_requests,
            "total_batches": self.total_batches,
            "avg_batch_size": avg_batch_size,
            "avg_batch_time_seconds": avg_batch_time,
            "throughput_per_second": self.total_requests / max(self.total_batch_time, 0.001),
        }


# Global singleton instance
_embedding_queue: EmbeddingBatchQueue | None = None


def get_embedding_queue() -> EmbeddingBatchQueue:
    """
    Get global embedding queue instance.

    Returns:
        EmbeddingBatchQueue instance

    Note: Must call start() before using
    """
    global _embedding_queue
    if _embedding_queue is None:
        raise RuntimeError(
            "Embedding queue not initialized. "
            "Call init_embedding_queue(embedding_fn) first."
        )
    return _embedding_queue


def init_embedding_queue(
    embedding_fn: Callable[[list[str]], list[list[float]]],
    batch_size: int = 32,
    max_wait_ms: int = 100,
) -> EmbeddingBatchQueue:
    """
    Initialize global embedding queue.

    Args:
        embedding_fn: Async function that generates embeddings
        batch_size: Maximum batch size
        max_wait_ms: Maximum wait time

    Returns:
        EmbeddingBatchQueue instance
    """
    global _embedding_queue
    if _embedding_queue is not None:
        logger.warning("Embedding queue already initialized")
        return _embedding_queue

    _embedding_queue = EmbeddingBatchQueue(
        embedding_fn=embedding_fn, batch_size=batch_size, max_wait_ms=max_wait_ms
    )
    logger.info("Initialized global embedding queue")
    return _embedding_queue
