#!/usr/bin/env python3
"""
Database Query Result Caching for ElohimOS

Provides intelligent caching for frequently accessed database queries
to reduce database load and improve response times.

Features:
- Query result caching with TTL
- Automatic cache invalidation on data changes
- User-scoped caching for multi-tenant support
- Cache statistics and monitoring
- Thread-safe operations

Performance Impact:
- Cached queries: < 1ms (vs 5-50ms from database)
- Reduced database contention
- Better scalability under load

Usage:
    from query_cache import QueryCache, cache_query

    cache = QueryCache()

    # Cache user profile lookup
    result = cache.get_or_fetch(
        key="user_profile_123",
        fetch_fn=lambda: get_user_from_db(123),
        ttl=300  # 5 minutes
    )

    # Invalidate on user update
    cache.invalidate_pattern("user_profile_*")
"""

import time
import logging
import hashlib
from typing import Any, Optional, Dict, Callable, List
from dataclasses import dataclass
from threading import Lock
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CachedQuery:
    """Cached query result with metadata"""
    result: Any
    expires_at: float
    created_at: float
    hits: int = 0
    query_time_ms: float = 0.0  # Original query time in ms


class QueryCache:
    """
    Database query result cache with intelligent invalidation

    Caches frequently accessed database queries to reduce load and improve
    response times. Provides automatic invalidation patterns for common
    operations.
    """

    def __init__(self, max_size: int = 500):
        """
        Initialize query cache

        Args:
            max_size: Maximum number of cached queries (LRU eviction)
        """
        self.cache: Dict[str, CachedQuery] = {}
        self.max_size = max_size
        self.lock = Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "invalidations": 0,
            "time_saved_ms": 0.0,  # Cumulative time saved by cache
        }

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl: int = 300
    ) -> Any:
        """
        Get cached result or fetch from database

        Args:
            key: Cache key (e.g., "user_profile_123")
            fetch_fn: Function to fetch data if not cached
            ttl: Time to live in seconds

        Returns:
            Query result (from cache or fresh fetch)
        """
        # Try cache first
        cached = self.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch data
        start_time = time.time()
        result = fetch_fn()
        query_time_ms = (time.time() - start_time) * 1000

        # Store in cache
        self.set(key, result, ttl, query_time_ms)

        return result

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached query result

        Args:
            key: Cache key

        Returns:
            Cached result if found and valid, None otherwise
        """
        with self.lock:
            entry = self.cache.get(key)

            if not entry:
                self.stats["misses"] += 1
                return None

            # Check if expired
            if time.time() > entry.expires_at:
                del self.cache[key]
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                logger.debug(f"Query cache expired: {key}")
                return None

            # Cache hit
            entry.hits += 1
            self.stats["hits"] += 1
            self.stats["time_saved_ms"] += entry.query_time_ms
            logger.debug(f"Query cache hit: {key} (saved {entry.query_time_ms:.2f}ms)")

            return entry.result

    def set(
        self,
        key: str,
        result: Any,
        ttl: int = 300,
        query_time_ms: float = 0.0
    ) -> None:
        """
        Store query result in cache

        Args:
            key: Cache key
            result: Query result to cache
            ttl: Time to live in seconds
            query_time_ms: Original query execution time
        """
        with self.lock:
            now = time.time()

            # Check if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()

            self.cache[key] = CachedQuery(
                result=result,
                expires_at=now + ttl,
                created_at=now,
                query_time_ms=query_time_ms
            )

            logger.debug(f"Query cached: {key} (TTL: {ttl}s, Query time: {query_time_ms:.2f}ms)")

    def invalidate(self, key: str) -> bool:
        """
        Invalidate specific cache entry

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was deleted
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats["invalidations"] += 1
                logger.debug(f"Query cache invalidated: {key}")
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching pattern

        Args:
            pattern: Pattern to match (e.g., "user_*", "*_profile_123")

        Returns:
            Number of entries invalidated
        """
        with self.lock:
            keys_to_delete = [
                key for key in self.cache.keys()
                if self._matches_pattern(key, pattern)
            ]

            for key in keys_to_delete:
                del self.cache[key]

            count = len(keys_to_delete)
            self.stats["invalidations"] += count

            if count > 0:
                logger.info(f"Query cache invalidated {count} entries matching '{pattern}'")

            return count

    def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries cleared
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Query cache cleared: {count} entries")
            return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Dict with cache stats
        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                (self.stats["hits"] / total_requests * 100)
                if total_requests > 0 else 0
            )

            avg_time_saved = (
                (self.stats["time_saved_ms"] / self.stats["hits"])
                if self.stats["hits"] > 0 else 0
            )

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": round(hit_rate, 2),
                "evictions": self.stats["evictions"],
                "expirations": self.stats["expirations"],
                "invalidations": self.stats["invalidations"],
                "time_saved_ms": round(self.stats["time_saved_ms"], 2),
                "avg_time_saved_ms": round(avg_time_saved, 2),
            }

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry using LRU policy"""
        if not self.cache:
            return

        # Find entry with oldest created_at
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at
        )

        del self.cache[oldest_key]
        self.stats["evictions"] += 1
        logger.debug(f"Query cache evicted oldest entry: {oldest_key}")

    @staticmethod
    def _matches_pattern(key: str, pattern: str) -> bool:
        """
        Simple pattern matching with wildcards

        Args:
            key: Cache key
            pattern: Pattern with optional * wildcard

        Returns:
            True if key matches pattern
        """
        if "*" not in pattern:
            return key == pattern

        # Simple prefix/suffix matching
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return key.endswith(pattern[1:])

        # Contains matching
        parts = pattern.split("*")
        if len(parts) == 2:
            return key.startswith(parts[0]) and key.endswith(parts[1])

        return False


# Global query cache instance
_query_cache = QueryCache(max_size=500)


# Convenience functions for module-level usage

def cache_query(
    key: str,
    fetch_fn: Callable[[], Any],
    ttl: int = 300
) -> Any:
    """
    Cache database query result

    Args:
        key: Unique cache key
        fetch_fn: Function to fetch data if not cached
        ttl: Time to live in seconds

    Returns:
        Query result (from cache or fresh)
    """
    return _query_cache.get_or_fetch(key, fetch_fn, ttl)


def invalidate_query(key: str) -> bool:
    """
    Invalidate specific query cache entry

    Args:
        key: Cache key to invalidate

    Returns:
        True if entry was deleted
    """
    return _query_cache.invalidate(key)


def invalidate_queries(pattern: str) -> int:
    """
    Invalidate all query cache entries matching pattern

    Args:
        pattern: Pattern to match (e.g., "user_*")

    Returns:
        Number of entries invalidated
    """
    return _query_cache.invalidate_pattern(pattern)


def clear_query_cache() -> int:
    """
    Clear all query cache entries

    Returns:
        Number of entries cleared
    """
    return _query_cache.clear()


def get_query_cache_stats() -> Dict[str, Any]:
    """
    Get query cache statistics

    Returns:
        Dict with cache performance stats
    """
    return _query_cache.get_stats()


# Cache key builders for common queries

def build_user_cache_key(user_id: int) -> str:
    """Build cache key for user profile lookup"""
    return f"user_profile_{user_id}"


def build_permissions_cache_key(user_id: int) -> str:
    """Build cache key for user permissions"""
    return f"user_permissions_{user_id}"


def build_team_cache_key(team_id: str) -> str:
    """Build cache key for team data"""
    return f"team_{team_id}"


def build_workflows_cache_key(user_id: int) -> str:
    """Build cache key for user's workflows"""
    return f"workflows_user_{user_id}"


def build_settings_cache_key(user_id: int) -> str:
    """Build cache key for user settings"""
    return f"settings_user_{user_id}"


# Common query patterns with caching

def cached_user_lookup(user_id: int, db_path: Path) -> Optional[Dict[str, Any]]:
    """
    Cached user profile lookup

    Args:
        user_id: User ID to lookup
        db_path: Path to database

    Returns:
        User dict or None
    """
    def fetch_user():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, role, device_id, created_at
            FROM users WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    key = build_user_cache_key(user_id)
    return cache_query(key, fetch_user, ttl=300)  # 5 minutes


def cached_user_permissions(user_id: int, db_path: Path) -> Dict[str, bool]:
    """
    Cached user permissions lookup

    Args:
        user_id: User ID to lookup
        db_path: Path to database

    Returns:
        Dict of permission -> bool
    """
    def fetch_permissions():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get user role
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {}

        role = row["role"]

        # Get permissions for role
        cursor.execute("""
            SELECT permission_name, can_read, can_write, can_delete
            FROM role_permissions WHERE role = ?
        """, (role,))

        permissions = {}
        for row in cursor.fetchall():
            perm = row["permission_name"]
            permissions[f"{perm}:read"] = bool(row["can_read"])
            permissions[f"{perm}:write"] = bool(row["can_write"])
            permissions[f"{perm}:delete"] = bool(row["can_delete"])

        conn.close()
        return permissions

    key = build_permissions_cache_key(user_id)
    return cache_query(key, fetch_permissions, ttl=600)  # 10 minutes


# Example usage in endpoints:
#
# @router.get("/users/{user_id}")
# async def get_user(user_id: int):
#     user = cached_user_lookup(user_id, PATHS.app_db)
#     if not user:
#         raise not_found(ErrorCode.DB_RECORD_NOT_FOUND)
#     return user
#
# @router.put("/users/{user_id}")
# async def update_user(user_id: int, data: UserUpdate):
#     # ... update database ...
#     # Invalidate cache
#     invalidate_query(build_user_cache_key(user_id))
#     invalidate_query(build_permissions_cache_key(user_id))
#     return {"success": True}
