"""
Compatibility Shim for Response Cache

The implementation now lives in the `api.cache` package:
- api.cache.response: ResponseCache class and utilities

This shim maintains backward compatibility.
"""

from api.cache.response import (
    CacheEntry,
    ResponseCache,
    cache_response,
    get_cached,
    invalidate_cache,
    clear_cache,
    get_cache_stats,
    cleanup_expired_entries,
    build_cache_key,
)

__all__ = [
    "CacheEntry",
    "ResponseCache",
    "cache_response",
    "get_cached",
    "invalidate_cache",
    "clear_cache",
    "get_cache_stats",
    "cleanup_expired_entries",
    "build_cache_key",
]
