"""
Redis Caching Service

Provides high-performance caching for API responses, expensive computations,
and frequently accessed data.

Features:
- Async Redis operations
- Automatic key prefixing
- TTL management
- JSON serialization
- Cache invalidation patterns
- Performance metrics
"""

import hashlib
import json
import logging
from typing import Any

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class CacheService:
    """
    Async Redis cache service for high-performance caching.

    Usage:
        cache = CacheService("redis://localhost:6379/0")

        # Simple get/set
        await cache.set("key", {"data": "value"}, ttl=300)
        data = await cache.get("key")

        # Pattern-based deletion
        await cache.delete_pattern("user:*")

        # Cache decorator
        @cache.cached(ttl=60, key_prefix="expensive")
        async def expensive_operation(user_id: str):
            # ... expensive work ...
            return result
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "magnetar:",
        default_ttl: int = 300,  # 5 minutes
        enabled: bool = True,
    ):
        """
        Initialize cache service.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
            default_ttl: Default TTL in seconds
            enabled: Whether caching is enabled
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.enabled = enabled and REDIS_AVAILABLE
        self._redis: redis.Redis | None = None

        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled")

    async def connect(self):
        """Connect to Redis"""
        if not self.enabled:
            return

        try:
            self._redis = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            # Test connection
            await self._redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
            self._redis = None

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Closed Redis connection")

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix"""
        return f"{self.key_prefix}{key}"

    def _hash_key(self, *args, **kwargs) -> str:
        """Generate hash key from function arguments"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self._redis:
            return None

        try:
            full_key = self._make_key(key)
            value = await self._redis.get(full_key)

            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._redis:
            return False

        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # Serialize value
            if isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps(value)

            # Set with TTL
            await self._redis.setex(full_key, ttl, serialized)
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        if not self.enabled or not self._redis:
            return False

        try:
            full_key = self._make_key(key)
            result = await self._redis.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self._redis:
            return 0

        try:
            full_pattern = self._make_key(pattern)

            # Find all matching keys
            keys = []
            async for key in self._redis.scan_iter(match=full_pattern):
                keys.append(key)

            # Delete in batch
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self._redis:
            return False

        try:
            full_key = self._make_key(key)
            return await self._redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        if not self.enabled or not self._redis:
            return -2

        try:
            full_key = self._make_key(key)
            return await self._redis.ttl(full_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -2

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.

        Args:
            key: Counter key
            amount: Amount to increment by

        Returns:
            New counter value
        """
        if not self.enabled or not self._redis:
            return 0

        try:
            full_key = self._make_key(key)
            return await self._redis.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        if not self.enabled or not self._redis:
            return {"enabled": False}

        try:
            info = await self._redis.info("stats")
            return {
                "enabled": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
                ),
                "keys": await self._redis.dbsize(),
                "memory_used": info.get("used_memory_human", "0B"),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def cached(self, ttl: int | None = None, key_prefix: str = "", key_builder=None):
        """
        Decorator for caching function results.

        Args:
            ttl: Cache TTL in seconds
            key_prefix: Prefix for cache key
            key_builder: Custom function to build cache key

        Usage:
            @cache.cached(ttl=300, key_prefix="expensive")
            async def expensive_function(user_id: str):
                # ... expensive work ...
                return result
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)

                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    arg_hash = self._hash_key(*args, **kwargs)
                    cache_key = f"{key_prefix}:{func.__name__}:{arg_hash}"

                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_value

                # Execute function and cache result
                logger.debug(f"Cache miss for {cache_key}")
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl=ttl)

                return result

            return wrapper

        return decorator


# Global cache instance
_cache_service: CacheService | None = None


def get_cache() -> CacheService:
    """Get global cache service instance"""
    global _cache_service

    if _cache_service is None:
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"

        _cache_service = CacheService(redis_url=redis_url, enabled=enabled)

    return _cache_service


async def init_cache():
    """Initialize cache service"""
    cache = get_cache()
    await cache.connect()


async def close_cache():
    """Close cache service"""
    cache = get_cache()
    await cache.close()
