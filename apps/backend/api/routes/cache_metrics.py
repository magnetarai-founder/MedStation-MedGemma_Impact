"""
Cache Metrics API Endpoints

Provides endpoints to monitor cache performance:
- GET /api/cache/stats - Cache statistics (hit rate, size, etc.)
- POST /api/cache/flush - Clear cache (admin only)
- DELETE /api/cache/invalidate - Invalidate specific patterns
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from api.cache_service import get_cache
# Uncomment when auth is integrated:
# from api.auth_middleware import verify_token, require_founder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    hits: int
    misses: int
    hit_rate: float
    total_requests: int
    redis_total_commands: int
    redis_keys: int
    redis_memory_used: str


class InvalidateRequest(BaseModel):
    """Request to invalidate cache pattern"""
    pattern: str


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get cache performance statistics.

    Returns:
        Cache stats including hit rate, memory usage, etc.

    Example response:
        {
            "hits": 150,
            "misses": 50,
            "hit_rate": 75.0,
            "total_requests": 200,
            "redis_total_commands": 500,
            "redis_keys": 42,
            "redis_memory_used": "1.2M"
        }
    """
    try:
        cache = get_cache()
        stats = cache.get_stats()

        return CacheStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")


@router.post("/flush")
async def flush_cache():
    """
    Clear all cache entries.

    ⚠️ WARNING: This clears ALL cached data!
    Should be admin-only in production.

    Returns:
        Success message

    TODO: Add admin authentication
    """
    try:
        cache = get_cache()
        cache.flush_all()

        logger.warning("⚠️ Cache flushed by API request")

        return {
            "status": "success",
            "message": "Cache flushed successfully",
            "warning": "All cached data has been cleared"
        }

    except Exception as e:
        logger.error(f"Error flushing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to flush cache")


@router.post("/invalidate")
async def invalidate_cache_pattern(request: InvalidateRequest):
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: Pattern to match (e.g., "user:*", "ollama:*")

    Returns:
        Number of entries invalidated

    Examples:
        # Invalidate all user caches
        POST /api/cache/invalidate
        {"pattern": "user:*"}

        # Invalidate all Ollama model lists
        POST /api/cache/invalidate
        {"pattern": "ollama:models:*"}

    TODO: Add authentication
    """
    try:
        cache = get_cache()
        deleted = cache.delete_pattern(request.pattern)

        logger.info(f"Invalidated {deleted} cache entries matching '{request.pattern}'")

        return {
            "status": "success",
            "pattern": request.pattern,
            "deleted_count": deleted,
            "message": f"Invalidated {deleted} cache entries"
        }

    except Exception as e:
        logger.error(f"Error invalidating cache pattern: {e}")
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")


@router.delete("/key/{key}")
async def delete_cache_key(key: str):
    """
    Delete a specific cache key.

    Args:
        key: Cache key to delete

    Returns:
        Success status

    TODO: Add authentication
    """
    try:
        cache = get_cache()
        deleted = cache.delete(key)

        if deleted:
            return {
                "status": "success",
                "key": key,
                "message": "Cache key deleted"
            }
        else:
            return {
                "status": "not_found",
                "key": key,
                "message": "Cache key not found"
            }

    except Exception as e:
        logger.error(f"Error deleting cache key: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete cache key")


@router.get("/health")
async def cache_health():
    """
    Check if Redis cache is healthy.

    Returns:
        Health status

    Example response:
        {
            "status": "healthy",
            "redis_connected": true,
            "message": "Cache is operational"
        }
    """
    try:
        cache = get_cache()
        # Try a simple operation
        cache.redis.ping()

        return {
            "status": "healthy",
            "redis_connected": True,
            "message": "Cache is operational"
        }

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "message": f"Cache error: {str(e)}"
        }
