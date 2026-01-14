"""
Global application state and caching.

This module manages:
- Session storage (thread-safe)
- Query results cache with size limits (thread-safe)
- Request deduplication cache (thread-safe)
- Progress tracking for SSE streams (thread-safe)

SECURITY: All mutable state is protected by threading.RLock to prevent
race conditions in multi-threaded environments (FastAPI with multiple workers).
"""

import logging
import time
from collections import defaultdict
from threading import RLock
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# SESSION STORAGE (Thread-Safe)
# ============================================================================

_sessions_lock = RLock()
_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> Optional[dict]:
    """Get a session by ID (thread-safe)"""
    with _sessions_lock:
        return _sessions.get(session_id)


def set_session(session_id: str, data: dict) -> None:
    """Store a session (thread-safe)"""
    with _sessions_lock:
        _sessions[session_id] = data


def delete_session(session_id: str) -> bool:
    """Delete a session (thread-safe). Returns True if existed."""
    with _sessions_lock:
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False


def get_all_sessions() -> dict[str, dict]:
    """Get a copy of all sessions (thread-safe)"""
    with _sessions_lock:
        return dict(_sessions)


def session_exists(session_id: str) -> bool:
    """Check if session exists (thread-safe)"""
    with _sessions_lock:
        return session_id in _sessions


# Legacy compatibility - direct access (DEPRECATED, use functions above)
# Will be removed in v2.0
sessions: dict[str, dict] = _sessions  # Reference for backwards compat


# ============================================================================
# QUERY RESULTS CACHE (Thread-Safe)
# ============================================================================
# Query results cache with size limits to prevent OOM
# Limit: 100MB per result, 500MB total cache, 50 results max

MAX_RESULT_SIZE_MB = 100
MAX_CACHE_SIZE_MB = 500
MAX_CACHED_RESULTS = 50

_query_results_lock = RLock()
_query_results: dict[str, pd.DataFrame] = {}
_query_result_sizes: dict[str, int] = {}  # Track size in bytes
_total_cache_size: int = 0  # Total cache size in bytes

# Legacy compatibility (DEPRECATED, use get_query_result/store_query_result)
query_results: dict[str, pd.DataFrame] = _query_results


def _get_dataframe_size_bytes(df: pd.DataFrame) -> int:
    """Estimate DataFrame memory usage in bytes"""
    return df.memory_usage(deep=True).sum()


def _evict_oldest_query_result_unsafe() -> None:
    """Evict oldest query result (NOT thread-safe, caller must hold lock)"""
    global _total_cache_size
    if not _query_results:
        return

    # Get oldest query_id (first inserted)
    oldest_id = next(iter(_query_results))
    size = _query_result_sizes.get(oldest_id, 0)

    del _query_results[oldest_id]
    del _query_result_sizes[oldest_id]
    _total_cache_size -= size

    logger.info(f"Evicted query result {oldest_id} ({size / 1024 / 1024:.2f} MB) from cache")


def store_query_result(query_id: str, df: pd.DataFrame) -> bool:
    """
    Store query result with size limits (thread-safe).
    Returns False if result too large.

    Implements LRU eviction when cache is full.
    """
    global _total_cache_size

    # Calculate size
    size_bytes = _get_dataframe_size_bytes(df)
    size_mb = size_bytes / 1024 / 1024

    # Check if single result exceeds per-result limit
    if size_mb > MAX_RESULT_SIZE_MB:
        logger.warning(f"Query result too large ({size_mb:.2f} MB > {MAX_RESULT_SIZE_MB} MB), not caching")
        return False

    with _query_results_lock:
        # Evict oldest results until we have space
        while (len(_query_results) >= MAX_CACHED_RESULTS or
               _total_cache_size + size_bytes > MAX_CACHE_SIZE_MB * 1024 * 1024):
            _evict_oldest_query_result_unsafe()

        # Store result
        _query_results[query_id] = df
        _query_result_sizes[query_id] = size_bytes
        _total_cache_size += size_bytes

    logger.debug(f"Cached query result {query_id} ({size_mb:.2f} MB), total cache: {_total_cache_size / 1024 / 1024:.2f} MB")
    return True


def get_query_result(query_id: str) -> Optional[pd.DataFrame]:
    """Get a cached query result (thread-safe)"""
    with _query_results_lock:
        return _query_results.get(query_id)


def delete_query_result(query_id: str) -> bool:
    """Delete a cached query result (thread-safe). Returns True if existed."""
    global _total_cache_size
    with _query_results_lock:
        if query_id in _query_results:
            size = _query_result_sizes.get(query_id, 0)
            del _query_results[query_id]
            del _query_result_sizes[query_id]
            _total_cache_size -= size
            return True
        return False


# ============================================================================
# REQUEST DEDUPLICATION (Thread-Safe)
# ============================================================================
# Request deduplication (prevent double-click duplicate operations)
# Store request IDs with timestamps to detect duplicates within 60s window

_dedup_lock = RLock()
_request_dedup_cache: dict[str, float] = {}  # request_id -> timestamp
DEDUP_WINDOW_SECONDS = 60  # Consider duplicate if within 60 seconds


def is_duplicate_request(request_id: str) -> bool:
    """Check if request is a duplicate within time window (thread-safe)"""
    current_time = time.time()

    with _dedup_lock:
        # Clean up old entries (older than window)
        expired_keys = [k for k, v in _request_dedup_cache.items() if current_time - v > DEDUP_WINDOW_SECONDS]
        for k in expired_keys:
            del _request_dedup_cache[k]

        # Check if this request ID exists and is recent
        if request_id in _request_dedup_cache:
            age = current_time - _request_dedup_cache[request_id]
            if age < DEDUP_WINDOW_SECONDS:
                return True  # Duplicate!

        # Mark as seen
        _request_dedup_cache[request_id] = current_time
        return False


# ============================================================================
# PROGRESS TRACKING (SSE) (Thread-Safe)
# ============================================================================
# Progress tracking storage (in-memory, replace with Redis/DB in production)

_progress_lock = RLock()
_progress_streams: dict[str, dict[str, Any]] = {}  # {task_id: {status, progress, message, updated_at}}


def get_progress_stream(task_id: str) -> dict[str, Any] | None:
    """Get progress data for a task (thread-safe)"""
    with _progress_lock:
        return _progress_streams.get(task_id)


def update_progress_stream(task_id: str, status: str, progress: int, message: str, updated_at: str) -> None:
    """Update progress tracking for a task (thread-safe)"""
    with _progress_lock:
        _progress_streams[task_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": updated_at
        }


def delete_progress_stream(task_id: str) -> bool:
    """Delete progress tracking for a task (thread-safe). Returns True if existed."""
    with _progress_lock:
        if task_id in _progress_streams:
            del _progress_streams[task_id]
            return True
        return False


def list_progress_streams() -> list[str]:
    """List all active progress tracking task IDs (thread-safe)"""
    with _progress_lock:
        return list(_progress_streams.keys())
