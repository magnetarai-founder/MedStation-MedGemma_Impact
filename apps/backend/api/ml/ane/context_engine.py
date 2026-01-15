#!/usr/bin/env python3
"""
ANE Context Engine for NeutronStar
Unified context preservation with Apple Neural Engine acceleration
Adapted from Jarvis Agent implementation

Features:
- Background vectorization of chat context using ANE-accelerated embeddings
- Thread-safe storage with configurable retention
- Automatic pruning of old vectors
- Metal/ANE acceleration when available
"""

import os
import json
import queue
import threading
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _flatten_context(data: Dict[str, Any]) -> str:
    """Deterministically flatten a context dict to a text payload"""
    try:
        return json.dumps(data, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(data)


def _cpu_embed_fallback(text: str, dims: int = 384) -> List[float]:
    """
    Lightweight CPU embedding fallback when MLX/ANE unavailable
    Uses hash-based projection into fixed-size vector
    """
    import hashlib

    vec = [0.0] * dims
    if not text:
        return vec

    # Multiple hashes for better distribution
    for i in range((dims + 15) // 16):
        h = hashlib.sha256(f"{text}_{i}".encode()).digest()
        for j in range(min(16, dims - i * 16)):
            vec[i * 16 + j] = h[j] / 255.0

    # L2 normalize
    norm = sum(x*x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]

    return vec


def _embed_with_ane(text: str) -> List[float]:
    """
    Unified embedding with ANE/Metal acceleration
    Falls back gracefully if hardware acceleration unavailable
    """
    # Try MLX embedder (uses Metal + ANE)
    try:
        from api.mlx_embedder import get_mlx_embedder
        embedder = get_mlx_embedder()
        if embedder.initialize():
            result = embedder.embed_single(text)
            if result:
                logger.debug(f"✅ Embedded with MLX (Metal+ANE): {len(result)} dims")
                return result
    except Exception as e:
        logger.debug(f"MLX embedder unavailable: {e}")

    # Try unified embedder
    try:
        from api.unified_embedder import embed_text
        result = embed_text(text)
        if result:
            return result
    except Exception:
        pass

    # CPU fallback
    logger.debug("Using CPU fallback for embedding")
    return _cpu_embed_fallback(text)


@dataclass
class _VectorizationJob:
    """Job for background vectorization"""
    session_id: str
    text: str
    timestamp: float


class ANEContextEngine:
    """
    Context preservation engine with Apple Neural Engine acceleration

    - Vectorizes chat context in background workers
    - Uses Metal/ANE for fast embedding generation
    - Stores vectors with configurable retention
    - Thread-safe for concurrent access
    """

    def __init__(self, workers: int = 2, retention_days: float = 30.0):
        """
        Initialize the ANE context engine

        Args:
            workers: Number of background worker threads
            retention_days: Days to retain vectors (0 = infinite)
        """
        self._job_queue: "queue.Queue[_VectorizationJob | None]" = queue.Queue()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Storage
        self._vectors: Dict[str, List[float]] = {}
        self._timestamps: Dict[str, float] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

        # Stats
        self._processed_count = 0
        self._error_count = 0

        # Retention
        self._retention_secs = max(0.0, retention_days * 86400.0)

        # Workers
        self._workers: List[threading.Thread] = []
        for i in range(max(1, workers)):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"ane_worker_{i}",
                daemon=True
            )
            thread.start()
            self._workers.append(thread)

        logger.info(f"✅ ANE Context Engine started ({workers} workers, {retention_days}d retention)")

    # ========== Public API ==========

    def preserve_context(
        self,
        session_id: str,
        context_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Queue context for vectorization (non-blocking)

        Args:
            session_id: Unique session identifier
            context_data: Context dict to vectorize
            metadata: Optional metadata to store with vector
        """
        text = _flatten_context(context_data)
        job = _VectorizationJob(
            session_id=session_id,
            text=text,
            timestamp=time.time()
        )

        if metadata:
            with self._lock:
                self._metadata[session_id] = metadata

        self._job_queue.put(job)
        logger.debug(f"Queued context for session {session_id}")

    def enqueue_vectorization(
        self,
        session_id: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Alias for preserve_context for backward compatibility

        Args:
            session_id: Unique session identifier
            context: Context dict to vectorize
        """
        self.preserve_context(session_id, context)

    def get_vector(self, session_id: str) -> Optional[List[float]]:
        """Get stored vector for a session"""
        with self._lock:
            vec = self._vectors.get(session_id)
            return list(vec) if vec else None

    def get_all_vectors(self) -> Dict[str, List[float]]:
        """Get all stored vectors"""
        with self._lock:
            return {sid: list(vec) for sid, vec in self._vectors.items()}

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar contexts using vector similarity

        Args:
            query: Query text to embed and search
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of {session_id, similarity, metadata}
        """
        query_vec = _embed_with_ane(query)
        if not query_vec:
            return []

        results = []

        with self._lock:
            for session_id, stored_vec in self._vectors.items():
                similarity = self._cosine_similarity(query_vec, stored_vec)

                if similarity >= threshold:
                    results.append({
                        'session_id': session_id,
                        'similarity': similarity,
                        'metadata': self._metadata.get(session_id, {})
                    })

        # Sort by similarity descending
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    def stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        with self._lock:
            return {
                'sessions_stored': len(self._vectors),
                'processed_count': self._processed_count,
                'error_count': self._error_count,
                'queue_size': self._job_queue.qsize(),
                'workers': len(self._workers),
                'retention_days': self._retention_secs / 86400.0
            }

    def prune_older_than(self, days: float) -> int:
        """
        Remove vectors older than N days

        Returns:
            Number of vectors pruned
        """
        if days <= 0:
            return 0

        cutoff = time.time() - (days * 86400.0)

        with self._lock:
            to_delete = [
                sid for sid, ts in self._timestamps.items()
                if ts < cutoff
            ]

            for sid in to_delete:
                self._vectors.pop(sid, None)
                self._timestamps.pop(sid, None)
                self._metadata.pop(sid, None)

            logger.info(f"Pruned {len(to_delete)} old vectors")
            return len(to_delete)

    def clear_all(self) -> None:
        """Clear all stored vectors"""
        with self._lock:
            self._vectors.clear()
            self._timestamps.clear()
            self._metadata.clear()
            logger.info("Cleared all vectors")

    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown the engine gracefully"""
        logger.info("Shutting down ANE Context Engine...")

        self._stop_event.set()

        # Send sentinel values to unblock workers
        for _ in self._workers:
            self._job_queue.put(None)

        # Wait for workers
        for worker in self._workers:
            worker.join(timeout=timeout)

        logger.info("✅ ANE Context Engine shutdown complete")

    # ========== Internal Methods ==========

    def _worker_loop(self) -> None:
        """Background worker for vectorization"""
        while not self._stop_event.is_set():
            try:
                job = self._job_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Sentinel to exit
            if job is None:
                break

            try:
                # Vectorize using ANE/Metal
                vector = _embed_with_ane(job.text)

                if vector:
                    with self._lock:
                        self._vectors[job.session_id] = vector
                        self._timestamps[job.session_id] = job.timestamp
                        self._processed_count += 1

                        # Auto-prune if retention set
                        if self._retention_secs > 0:
                            self._prune_old_unsafe()

                    logger.debug(f"✅ Vectorized session {job.session_id}")
                else:
                    with self._lock:
                        self._error_count += 1
                    logger.warning(f"Failed to vectorize session {job.session_id}")

            except Exception as e:
                with self._lock:
                    self._error_count += 1
                logger.error(f"Worker error: {e}")

    def _prune_old_unsafe(self) -> None:
        """Prune old vectors (must hold lock)"""
        if self._retention_secs <= 0:
            return

        cutoff = time.time() - self._retention_secs
        to_delete = [
            sid for sid, ts in self._timestamps.items()
            if ts < cutoff
        ]

        for sid in to_delete:
            self._vectors.pop(sid, None)
            self._timestamps.pop(sid, None)
            self._metadata.pop(sid, None)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Singleton instance
_ane_engine: Optional[ANEContextEngine] = None


def get_ane_engine() -> ANEContextEngine:
    """Get singleton ANE context engine"""
    global _ane_engine
    if _ane_engine is None:
        retention_days = float(os.getenv('ANE_RETENTION_DAYS', '30'))
        workers = int(os.getenv('ANE_WORKERS', '2'))
        _ane_engine = ANEContextEngine(workers=workers, retention_days=retention_days)
    return _ane_engine
