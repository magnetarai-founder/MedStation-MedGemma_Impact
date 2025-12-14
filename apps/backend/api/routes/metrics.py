"""
Metrics API Endpoints

Exposes system metrics for monitoring and observability:
- Request performance (timing, throughput, errors)
- Database query performance (slow queries, averages)
- Cache performance (hit rate, memory usage)
- Error tracking (recent errors, error types)

Usage:
    from fastapi import FastAPI
    from api.routes.metrics import router as metrics_router

    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, List
import logging

from api.observability_middleware import (
    get_request_metrics,
    get_endpoint_metrics,
    get_error_metrics,
    reset_metrics as reset_request_metrics
)
from api.db_profiler import get_query_stats, reset_query_stats
from api.cache_service import get_cache
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["metrics"]
)


@router.get("/health", response_model=SuccessResponse[Dict])
async def health_check() -> SuccessResponse[Dict]:
    """
    Basic health check for monitoring systems.

    Returns:
        Simple health status
    """
    return SuccessResponse(
        data={
            "status": "healthy",
            "service": "magnetar-studio-backend"
        },
        message="Metrics service operational"
    )


@router.get("/system")
async def get_system_metrics() -> Dict:
    """
    Get combined system metrics from all sources.

    Returns:
        Comprehensive system metrics including:
        - Request performance
        - Database query performance
        - Cache performance
    """
    try:
        # Request metrics
        request_stats = get_request_metrics()

        # Database metrics
        db_stats = get_query_stats()

        # Cache metrics
        cache = get_cache()
        cache_stats = cache.get_stats()

        return {
            "requests": request_stats,
            "database": db_stats,
            "cache": cache_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system metrics", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve system metrics"
            ).model_dump()
        )


@router.get("/requests")
async def get_request_stats() -> Dict:
    """
    Get request timing and throughput statistics.

    Returns:
        - total_requests: Total number of requests handled
        - successful_requests: Requests that completed successfully
        - failed_requests: Requests that returned errors
        - slow_requests: Requests > 1 second
        - very_slow_requests: Requests > 5 seconds
        - average_time_ms: Average request processing time
        - total_time_ms: Total processing time
    """
    try:
        return get_request_metrics()
    except Exception as e:
        logger.error(f"Failed to get request metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get request metrics: {str(e)}")


@router.get("/endpoints")
async def get_endpoint_stats(limit: int = 10) -> Dict:
    """
    Get per-endpoint performance statistics.

    Args:
        limit: Number of top endpoints to return (default: 10)

    Returns:
        List of endpoints with:
        - endpoint: HTTP method and path
        - count: Number of requests
        - average_time_ms: Average processing time
        - total_time_ms: Total processing time
        - errors: Number of errors
        - error_rate: Percentage of requests that failed
    """
    try:
        endpoints = get_endpoint_metrics(limit=limit)
        return {
            "endpoints": endpoints,
            "total_endpoints": len(endpoints)
        }
    except Exception as e:
        logger.error(f"Failed to get endpoint metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get endpoint metrics: {str(e)}")


@router.get("/errors")
async def get_error_stats() -> Dict:
    """
    Get error tracking statistics.

    Returns:
        - error_counts: Count of each error type
        - recent_errors: Last 10 errors with timestamps and details
        - total_error_types: Number of unique error types
    """
    try:
        return get_error_metrics()
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get error metrics: {str(e)}")


@router.get("/database")
async def get_database_stats() -> Dict:
    """
    Get database query performance statistics.

    Returns:
        - total_queries: Total number of queries executed
        - slow_queries: Queries > 50ms
        - very_slow_queries: Queries > 200ms
        - failed_queries: Queries that failed
        - average_time_ms: Average query execution time
        - total_time_ms: Total query execution time
    """
    try:
        return get_query_stats()
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database metrics: {str(e)}")


@router.get("/cache")
async def get_cache_stats() -> Dict:
    """
    Get cache performance statistics.

    Returns:
        - hits: Number of cache hits
        - misses: Number of cache misses
        - hit_rate: Percentage of requests served from cache
        - total_requests: Total cache requests
        - redis_keys: Number of keys in Redis
        - redis_memory_used: Memory used by Redis
    """
    try:
        cache = get_cache()
        stats = cache.get_stats()

        # Add Redis server info
        info = cache.redis.info('memory')
        stats['redis_memory_used'] = info.get('used_memory_human', 'unknown')
        stats['redis_keys'] = cache.redis.dbsize()

        return stats
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache metrics: {str(e)}")


@router.post("/reset")
async def reset_all_metrics() -> Dict:
    """
    Reset all metrics counters.

    WARNING: This will clear all accumulated statistics.
    Use only for testing or after maintenance.

    Returns:
        Confirmation of reset
    """
    try:
        # Reset request metrics
        reset_request_metrics()

        # Reset database metrics
        reset_query_stats()

        # Note: Cache stats are part of CacheService instance, reset via cache.reset_stats()
        cache = get_cache()
        cache.hits = 0
        cache.misses = 0

        logger.info("🔄 All metrics reset")

        return {
            "status": "success",
            "message": "All metrics have been reset",
            "timestamp": "now"
        }
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {str(e)}")


@router.get("/summary")
async def get_metrics_summary() -> Dict:
    """
    Get a quick summary of all metrics.

    Returns:
        High-level overview of system performance
    """
    try:
        request_stats = get_request_metrics()
        db_stats = get_query_stats()
        cache = get_cache()
        cache_stats = cache.get_stats()

        # Calculate summary stats
        total_requests = request_stats.get('total_requests', 0)
        failed_requests = request_stats.get('failed_requests', 0)
        success_rate = ((total_requests - failed_requests) / total_requests * 100) if total_requests > 0 else 0

        slow_request_rate = (request_stats.get('slow_requests', 0) / total_requests * 100) if total_requests > 0 else 0

        return {
            "overview": {
                "total_requests": total_requests,
                "success_rate_percent": round(success_rate, 2),
                "average_response_time_ms": request_stats.get('average_time_ms', 0),
                "slow_request_rate_percent": round(slow_request_rate, 2)
            },
            "performance": {
                "cache_hit_rate_percent": cache_stats.get('hit_rate', 0),
                "database_queries": db_stats.get('total_queries', 0),
                "database_avg_time_ms": db_stats.get('average_time_ms', 0),
                "slow_database_queries": db_stats.get('slow_queries', 0)
            },
            "health": {
                "failed_requests": failed_requests,
                "failed_database_queries": db_stats.get('failed_queries', 0),
                "error_types": len(get_error_metrics().get('error_counts', {}))
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")
