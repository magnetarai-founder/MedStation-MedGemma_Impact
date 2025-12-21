"""
Global application state and caching.

This module manages:
- Session storage
- Query results cache with size limits
- Request deduplication cache
- Progress tracking for SSE streams
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# SESSION STORAGE
# ============================================================================

sessions: dict[str, dict] = {}


# ============================================================================
# QUERY RESULTS CACHE
# ============================================================================
# Query results cache with size limits to prevent OOM
# Limit: 100MB per result, 500MB total cache, 50 results max

MAX_RESULT_SIZE_MB = 100
MAX_CACHE_SIZE_MB = 500
MAX_CACHED_RESULTS = 50

query_results: dict[str, pd.DataFrame] = {}
_query_result_sizes: dict[str, int] = {}  # Track size in bytes
_total_cache_size: int = 0  # Total cache size in bytes


def _get_dataframe_size_bytes(df: pd.DataFrame) -> int:
    """Estimate DataFrame memory usage in bytes"""
    return df.memory_usage(deep=True).sum()


def _evict_oldest_query_result() -> None:
    """Evict the oldest query result from cache to free memory"""
    global _total_cache_size
    if not query_results:
        return

    # Get oldest query_id (first inserted)
    oldest_id = next(iter(query_results))
    size = _query_result_sizes.get(oldest_id, 0)

    del query_results[oldest_id]
    del _query_result_sizes[oldest_id]
    _total_cache_size -= size

    logger.info(f"Evicted query result {oldest_id} ({size / 1024 / 1024:.2f} MB) from cache")


def store_query_result(query_id: str, df: pd.DataFrame) -> bool:
    """
    Store query result with size limits. Returns False if result too large.

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

    # Evict oldest results until we have space
    while (len(query_results) >= MAX_CACHED_RESULTS or
           _total_cache_size + size_bytes > MAX_CACHE_SIZE_MB * 1024 * 1024):
        _evict_oldest_query_result()

    # Store result
    query_results[query_id] = df
    _query_result_sizes[query_id] = size_bytes
    _total_cache_size += size_bytes

    logger.debug(f"Cached query result {query_id} ({size_mb:.2f} MB), total cache: {_total_cache_size / 1024 / 1024:.2f} MB")
    return True


# ============================================================================
# REQUEST DEDUPLICATION
# ============================================================================
# Request deduplication (prevent double-click duplicate operations)
# Store request IDs with timestamps to detect duplicates within 60s window

_request_dedup_cache: defaultdict[str, float] = defaultdict(float)  # request_id -> timestamp
_dedup_lock = None  # Will be initialized as asyncio.Lock when needed
DEDUP_WINDOW_SECONDS = 60  # Consider duplicate if within 60 seconds


def is_duplicate_request(request_id: str) -> bool:
    """Check if request is a duplicate within time window"""
    global _dedup_lock
    if _dedup_lock is None:
        import asyncio
        _dedup_lock = asyncio.Lock()

    current_time = time.time()

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
# PROGRESS TRACKING (SSE)
# ============================================================================
# Progress tracking storage (in-memory, replace with Redis/DB in production)

_progress_streams: dict[str, dict[str, Any]] = {}  # {task_id: {status, progress, message, updated_at}}


def get_progress_stream(task_id: str) -> dict[str, Any] | None:
    """Get progress data for a task"""
    return _progress_streams.get(task_id)


def update_progress_stream(task_id: str, status: str, progress: int, message: str, updated_at: str) -> None:
    """Update progress tracking for a task"""
    _progress_streams[task_id] = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": updated_at
    }


def delete_progress_stream(task_id: str) -> bool:
    """Delete progress tracking for a task. Returns True if existed."""
    if task_id in _progress_streams:
        del _progress_streams[task_id]
        return True
    return False


def list_progress_streams() -> list[str]:
    """List all active progress tracking task IDs"""
    return list(_progress_streams.keys())
