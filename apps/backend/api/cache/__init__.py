"""
Cache Package

Caching utilities for MedStation:
- Generic cache service with Redis/memory backends
- Query caching for database operations
- Response caching for API endpoints
"""

from api.cache.service import (
    CacheService,
    cached,
    get_cache,
    close_cache,
)
from api.cache.query import (
    CachedQuery,
    QueryCache,
    cache_query,
    invalidate_query,
    invalidate_queries,
    clear_query_cache,
    get_query_cache_stats,
    build_user_cache_key,
    build_permissions_cache_key,
    build_team_cache_key,
    build_workflows_cache_key,
    build_settings_cache_key,
    cached_user_lookup,
    cached_user_permissions,
)
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
    # Service
    "CacheService",
    "cached",
    "get_cache",
    "close_cache",
    # Query cache
    "CachedQuery",
    "QueryCache",
    "cache_query",
    "invalidate_query",
    "invalidate_queries",
    "clear_query_cache",
    "get_query_cache_stats",
    "build_user_cache_key",
    "build_permissions_cache_key",
    "build_team_cache_key",
    "build_workflows_cache_key",
    "build_settings_cache_key",
    "cached_user_lookup",
    "cached_user_permissions",
    # Response cache
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
