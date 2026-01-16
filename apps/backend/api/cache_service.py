"""
Compatibility Shim for Cache Service

The implementation now lives in the `api.cache` package:
- api.cache.service: CacheService class and utilities

This shim maintains backward compatibility.
"""

from api.cache.service import (
    CacheService,
    cached,
    get_cache,
    close_cache,
)

__all__ = [
    "CacheService",
    "cached",
    "get_cache",
    "close_cache",
]
