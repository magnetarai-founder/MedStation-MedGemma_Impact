"""
Compatibility Shim for Query Cache

The implementation now lives in the `api.cache` package:
- api.cache.query: QueryCache class and utilities

This shim maintains backward compatibility.
"""

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

__all__ = [
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
]
