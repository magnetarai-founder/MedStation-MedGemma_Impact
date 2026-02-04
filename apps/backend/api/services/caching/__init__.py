"""
Smart Caching System for MagnetarCode

Provides intelligent, predictive caching with:
- Pre-warming based on usage patterns
- Predictive file loading
- Intelligent context prefetch for LLM calls
- LRU + frequency-based eviction
- Multiple backend support (memory, SQLite, Redis)
- Background refresh of stale entries

Usage:
    from api.services.caching import get_smart_cache, CacheBackend

    # Get smart cache instance
    cache = get_smart_cache()
    await cache.initialize()

    # Basic operations
    await cache.set("key", value, ttl=300)
    value = await cache.get("key")

    # Predictive caching
    await cache.warm_cache("workspace_id", workspace_root="/path/to/project")
    next_files = await cache.predict_next("current_file.py", workspace_id="ws_123")
    await cache.prefetch(next_files)

    # Get statistics
    stats = cache.get_stats()
    print(f"Hit rate: {stats.hit_rate:.2%}")
"""

from api.services.caching.smart_cache import (
    CacheBackend,
    CacheEntry,
    CacheStats,
    PredictionModel,
    SmartCache,
    get_smart_cache,
)

__all__ = [
    "SmartCache",
    "CacheEntry",
    "CacheStats",
    "PredictionModel",
    "CacheBackend",
    "get_smart_cache",
]
