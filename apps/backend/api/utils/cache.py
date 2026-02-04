"""
Caching utilities for MagnetarCode API.

Provides in-memory caching with TTL for performance optimization.
Can be extended to use Redis for distributed caching.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    """Cache entry with value and expiration."""

    value: Any
    expires_at: float


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL support.

    Features:
    - Time-based expiration (TTL)
    - LRU eviction when size limit reached
    - Cache hit/miss metrics
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries to store
        """
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = Lock()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check if expired
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 5 minutes)
        """
        with self._lock:
            # Evict oldest entry if cache is full
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_oldest()

            expires_at = time.time() + ttl
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Pattern to match (simple substring match)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def _evict_oldest(self) -> None:
        """Evict the oldest (first to expire) entry."""
        if not self._cache:
            return

        # Find entry with earliest expiration
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
        del self._cache[oldest_key]
        self._evictions += 1

    def get_metrics(self) -> dict[str, Any]:
        """
        Get cache metrics.

        Returns:
            Dictionary with hit/miss rates and other stats
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
            }


# Global cache instance
_cache = InMemoryCache(max_size=1000)


def get_cache() -> InMemoryCache:
    """Get global cache instance."""
    return _cache


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Unique cache key as string
    """
    # Create deterministic key from arguments
    key_data = {"args": args, "kwargs": sorted(kwargs.items())}
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = "") -> Callable:
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Optional prefix for cache key

    Example:
        @cached(ttl=60, key_prefix="user")
        async def get_user(user_id: str):
            return await fetch_user(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            _cache.set(key, result, ttl=ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl=ttl)

            return result

        # Return appropriate wrapper based on whether function is async
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ===== Specialized Cache Functions =====


def cache_ollama_models(ttl: int = 300):
    """
    Cache decorator specifically for Ollama model list.

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
    """
    return cached(ttl=ttl, key_prefix="ollama_models")


def cache_file_tree(ttl: int = 30):
    """
    Cache decorator for workspace file tree.

    Args:
        ttl: Time to live in seconds (default: 30 seconds)
    """
    return cached(ttl=ttl, key_prefix="file_tree")


def cache_vector_search(ttl: int = 60):
    """
    Cache decorator for vector search results.

    Args:
        ttl: Time to live in seconds (default: 1 minute)
    """
    return cached(ttl=ttl, key_prefix="vector_search")


def invalidate_workspace_cache(workspace_path: str) -> int:
    """
    Invalidate all cache entries related to a workspace.

    Args:
        workspace_path: Path to workspace

    Returns:
        Number of entries invalidated
    """
    return _cache.invalidate_pattern(f"file_tree:{workspace_path}")


def invalidate_ollama_cache() -> int:
    """
    Invalidate Ollama model cache.

    Returns:
        Number of entries invalidated
    """
    return _cache.invalidate_pattern("ollama_models")
