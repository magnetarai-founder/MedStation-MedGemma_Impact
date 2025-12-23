"""
Cache Metrics API Endpoints

Provides endpoints to monitor cache performance and management.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from api.cache_service import get_cache
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.auth_middleware import get_current_user, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cache", tags=["cache"])

# Admin roles allowed to perform destructive cache operations
ADMIN_ROLES = {"founder_rights", "super_admin", "admin"}


def _require_admin(current_user: User) -> None:
    """Raise 403 if user is not an admin."""
    role = getattr(current_user, 'role', None) or current_user.get('role') if isinstance(current_user, dict) else None
    if role not in ADMIN_ROLES:
        logger.warning(
            f"Unauthorized cache operation attempt by user {getattr(current_user, 'user_id', 'unknown')} with role {role}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                error_code=ErrorCode.FORBIDDEN,
                message="Admin privileges required for cache operations"
            ).model_dump()
        )


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


@router.get(
    "/stats",
    response_model=SuccessResponse[CacheStatsResponse],
    status_code=status.HTTP_200_OK,
    name="cache_get_stats",
    summary="Get cache statistics",
    description="Get cache performance statistics including hit rate, memory usage, and key counts"
)
async def get_cache_stats() -> SuccessResponse[CacheStatsResponse]:
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

        return SuccessResponse(
            data=CacheStatsResponse(**stats),
            message="Cache statistics retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get cache stats", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve cache statistics"
            ).model_dump()
        )


class FlushResponse(BaseModel):
    status: str
    message: str
    warning: str


@router.post(
    "/flush",
    response_model=SuccessResponse[FlushResponse],
    status_code=status.HTTP_200_OK,
    name="cache_flush",
    summary="Flush cache",
    description="Clear all cache entries (WARNING: Clears ALL cached data - admin only)"
)
async def flush_cache(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[FlushResponse]:
    """
    Clear all cache entries.

    ⚠️ WARNING: This clears ALL cached data!
    Requires admin, super_admin, or founder_rights role.

    Returns:
        Success message
    """
    _require_admin(current_user)

    try:
        cache = get_cache()
        cache.flush_all()

        user_id = getattr(current_user, 'user_id', 'unknown')
        logger.warning(f"Cache flushed by admin user {user_id}")

        return SuccessResponse(
            data=FlushResponse(
                status="success",
                message="Cache flushed successfully",
                warning="All cached data has been cleared"
            ),
            message="Cache flushed successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to flush cache", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to flush cache"
            ).model_dump()
        )


class InvalidateResponse(BaseModel):
    status: str
    pattern: str
    deleted_count: int
    message: str


@router.post(
    "/invalidate",
    response_model=SuccessResponse[InvalidateResponse],
    status_code=status.HTTP_200_OK,
    name="cache_invalidate_pattern",
    summary="Invalidate cache pattern",
    description="Invalidate cache entries matching a pattern (e.g., 'user:*', 'ollama:*')"
)
async def invalidate_cache_pattern(
    request: InvalidateRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[InvalidateResponse]:
    """
    Invalidate cache entries matching a pattern.

    Requires admin, super_admin, or founder_rights role.

    Args:
        pattern: Pattern to match (e.g., "user:*", "ollama:*")

    Returns:
        Number of entries invalidated

    Examples:
        # Invalidate all user caches
        POST /api/v1/cache/invalidate
        {"pattern": "user:*"}

        # Invalidate all Ollama model lists
        POST /api/v1/cache/invalidate
        {"pattern": "ollama:models:*"}
    """
    _require_admin(current_user)

    try:
        cache = get_cache()
        deleted = cache.delete_pattern(request.pattern)

        logger.info(f"Invalidated {deleted} cache entries matching '{request.pattern}'")

        return SuccessResponse(
            data=InvalidateResponse(
                status="success",
                pattern=request.pattern,
                deleted_count=deleted,
                message=f"Invalidated {deleted} cache entries"
            ),
            message=f"Invalidated {deleted} cache entr{'y' if deleted == 1 else 'ies'}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to invalidate cache pattern", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to invalidate cache"
            ).model_dump()
        )


class DeleteKeyResponse(BaseModel):
    status: str
    key: str
    message: str


@router.delete(
    "/key/{key}",
    response_model=SuccessResponse[DeleteKeyResponse],
    status_code=status.HTTP_200_OK,
    name="cache_delete_key",
    summary="Delete cache key",
    description="Delete a specific cache key"
)
async def delete_cache_key(
    key: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[DeleteKeyResponse]:
    """
    Delete a specific cache key.

    Requires admin, super_admin, or founder_rights role.

    Args:
        key: Cache key to delete

    Returns:
        Success status
    """
    _require_admin(current_user)

    try:
        cache = get_cache()
        deleted = cache.delete(key)

        if deleted:
            return SuccessResponse(
                data=DeleteKeyResponse(
                    status="success",
                    key=key,
                    message="Cache key deleted"
                ),
                message=f"Cache key '{key}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Cache key not found"
                ).model_dump()
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete cache key '{key}'", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete cache key"
            ).model_dump()
        )


class CacheHealthResponse(BaseModel):
    status: str
    redis_connected: bool
    message: str


@router.get(
    "/health",
    response_model=SuccessResponse[CacheHealthResponse],
    status_code=status.HTTP_200_OK,
    name="cache_health_check",
    summary="Cache health check",
    description="Check if Redis cache is healthy and operational"
)
async def cache_health() -> SuccessResponse[CacheHealthResponse]:
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

        return SuccessResponse(
            data=CacheHealthResponse(
                status="healthy",
                redis_connected=True,
                message="Cache is operational"
            ),
            message="Cache is healthy"
        )

    except Exception as e:
        logger.error(f"Cache health check failed", exc_info=True)
        # Return unhealthy status but with 200 OK (not an error from API perspective)
        return SuccessResponse(
            data=CacheHealthResponse(
                status="unhealthy",
                redis_connected=False,
                message=f"Cache error: {str(e)}"
            ),
            message="Cache is unhealthy"
        )
