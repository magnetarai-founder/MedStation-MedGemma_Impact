"""
Metrics API Endpoints

Exposes system metrics for monitoring and observability:
- Request performance (timing, throughput, errors)
- Database query performance (slow queries, averages)
- Cache performance (hit rate, memory usage)
- Error tracking (recent errors, error types)

Follows MagnetarStudio API standards (see API_STANDARDS.md).
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
from api.routes.schemas import SuccessResponse
from api.errors import http_404
from api.core.exceptions import handle_exceptions

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["metrics"]
)


@router.get(
    "/health",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_health_check",
    summary="Metrics health check",
    description="Basic health check for monitoring systems"
)
async def health_check() -> SuccessResponse[Dict]:
    """Basic health check for monitoring systems"""
    return SuccessResponse(
        data={
            "status": "healthy",
            "service": "magnetar-studio-backend"
        },
        message="Metrics service operational"
    )


@router.get(
    "/system",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_system",
    summary="Get system metrics",
    description="Get combined system metrics from all sources (requests, database, cache)"
)
@handle_exceptions("get system metrics")
async def get_system_metrics() -> SuccessResponse[Dict]:
    """Get combined system metrics from all sources"""
    request_stats = get_request_metrics()
    db_stats = get_query_stats()
    cache = get_cache()
    cache_stats = cache.get_stats()

    metrics_data = {
        "requests": request_stats,
        "database": db_stats,
        "cache": cache_stats
    }

    return SuccessResponse(
        data=metrics_data,
        message="System metrics retrieved successfully"
    )


@router.get(
    "/requests",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_requests",
    summary="Get request metrics",
    description="Get request timing and throughput statistics"
)
@handle_exceptions("get request metrics")
async def get_request_stats() -> SuccessResponse[Dict]:
    """
    Get request timing and throughput statistics

    Returns:
        - total_requests: Total number of requests handled
        - successful_requests: Requests that completed successfully
        - failed_requests: Requests that returned errors
        - slow_requests: Requests > 1 second
        - very_slow_requests: Requests > 5 seconds
        - average_time_ms: Average request processing time
        - total_time_ms: Total processing time
    """
    metrics_data = get_request_metrics()
    return SuccessResponse(
        data=metrics_data,
        message="Request metrics retrieved successfully"
    )


@router.get(
    "/endpoints",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_endpoints",
    summary="Get endpoint metrics",
    description="Get per-endpoint performance statistics"
)
@handle_exceptions("get endpoint metrics")
async def get_endpoint_stats(limit: int = 10) -> SuccessResponse[Dict]:
    """
    Get per-endpoint performance statistics

    Args:
        limit: Number of top endpoints to return (default: 10)

    Returns:
        List of endpoints with count, average_time_ms, total_time_ms, errors, error_rate
    """
    endpoints = get_endpoint_metrics(limit=limit)
    metrics_data = {
        "endpoints": endpoints,
        "total_endpoints": len(endpoints)
    }

    return SuccessResponse(
        data=metrics_data,
        message=f"Retrieved {len(endpoints)} endpoint{'s' if len(endpoints) != 1 else ''}"
    )


@router.get(
    "/errors",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_errors",
    summary="Get error metrics",
    description="Get error tracking statistics"
)
@handle_exceptions("get error metrics")
async def get_error_stats() -> SuccessResponse[Dict]:
    """
    Get error tracking statistics

    Returns:
        - error_counts: Count of each error type
        - recent_errors: Last 10 errors with timestamps and details
        - total_error_types: Number of unique error types
    """
    metrics_data = get_error_metrics()
    return SuccessResponse(
        data=metrics_data,
        message="Error metrics retrieved successfully"
    )


@router.get(
    "/database",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_database",
    summary="Get database metrics",
    description="Get database query performance statistics"
)
@handle_exceptions("get database metrics")
async def get_database_stats() -> SuccessResponse[Dict]:
    """
    Get database query performance statistics

    Returns:
        - total_queries: Total number of queries executed
        - slow_queries: Queries > 50ms
        - very_slow_queries: Queries > 200ms
        - failed_queries: Queries that failed
        - average_time_ms: Average query execution time
        - total_time_ms: Total query execution time
    """
    metrics_data = get_query_stats()
    return SuccessResponse(
        data=metrics_data,
        message="Database metrics retrieved successfully"
    )


@router.get(
    "/cache",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_cache",
    summary="Get cache metrics",
    description="Get cache performance statistics"
)
@handle_exceptions("get cache metrics")
async def get_cache_stats() -> SuccessResponse[Dict]:
    """
    Get cache performance statistics

    Returns:
        - hits: Number of cache hits
        - misses: Number of cache misses
        - hit_rate: Percentage of requests served from cache
        - total_requests: Total cache requests
        - redis_keys: Number of keys in Redis
        - redis_memory_used: Memory used by Redis
    """
    cache = get_cache()
    stats = cache.get_stats()

    # Add Redis server info
    info = cache.redis.info('memory')
    stats['redis_memory_used'] = info.get('used_memory_human', 'unknown')
    stats['redis_keys'] = cache.redis.dbsize()

    return SuccessResponse(
        data=stats,
        message="Cache metrics retrieved successfully"
    )


@router.post(
    "/reset",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_reset",
    summary="Reset all metrics",
    description="Reset all metrics counters (use only for testing or after maintenance)"
)
@handle_exceptions("reset all metrics")
async def reset_all_metrics() -> SuccessResponse[Dict]:
    """
    Reset all metrics counters

    WARNING: This will clear all accumulated statistics.
    Use only for testing or after maintenance.
    """
    # Reset request metrics
    reset_request_metrics()

    # Reset database metrics
    reset_query_stats()

    # Note: Cache stats are part of CacheService instance
    cache = get_cache()
    cache.hits = 0
    cache.misses = 0

    logger.info("All metrics reset")

    reset_data = {
        "status": "success",
        "timestamp": "now"
    }

    return SuccessResponse(
        data=reset_data,
        message="All metrics have been reset"
    )


@router.get(
    "/summary",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_summary",
    summary="Get metrics summary",
    description="Get a quick summary of all metrics for system performance overview"
)
@handle_exceptions("get metrics summary")
async def get_metrics_summary() -> SuccessResponse[Dict]:
    """
    Get a quick summary of all metrics

    Returns:
        High-level overview of system performance including:
        - Overview: total requests, success rate, response time
        - Performance: cache hit rate, database query stats
        - Health: failed requests, failed queries, error types
    """
    request_stats = get_request_metrics()
    db_stats = get_query_stats()
    cache = get_cache()
    cache_stats = cache.get_stats()

    # Calculate summary stats
    total_requests = request_stats.get('total_requests', 0)
    failed_requests = request_stats.get('failed_requests', 0)
    success_rate = ((total_requests - failed_requests) / total_requests * 100) if total_requests > 0 else 0

    slow_request_rate = (request_stats.get('slow_requests', 0) / total_requests * 100) if total_requests > 0 else 0

    summary_data = {
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

    return SuccessResponse(
        data=summary_data,
        message="Metrics summary retrieved successfully"
    )


# ============================================================================
# OPERATION-LEVEL METRICS (from metrics.py service)
# ============================================================================


@router.get(
    "/operations/summary",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_operations_summary",
    summary="Get operation-level metrics summary",
    description="Get system-wide observability metrics for operations"
)
@handle_exceptions("get operations summary")
async def get_operations_summary() -> SuccessResponse[Dict]:
    """
    Get system-wide observability metrics

    Returns summary of operation counts, latencies, and errors for:
    - SQL query execution
    - Data uploads
    - P2P sync operations
    - File transfers

    Useful for identifying bottlenecks and performance issues in production.
    """
    from metrics import get_metrics
    metrics_collector = get_metrics()
    summary = metrics_collector.get_summary()

    return SuccessResponse(
        data=summary,
        message="Operations metrics summary retrieved successfully"
    )


@router.get(
    "/operations/{operation}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_get_operation",
    summary="Get detailed metrics for specific operation",
    description="Get detailed metrics including latencies and error rates for a specific operation"
)
@handle_exceptions("get operation metrics", resource_type="Operation")
async def get_operation_metrics_detail(operation: str) -> SuccessResponse[Dict]:
    """
    Get detailed metrics for a specific operation

    Args:
        operation: Operation name (e.g., 'sql_query_execution', 'data_upload', 'p2p_sync')

    Returns:
        Detailed metrics including count, avg/p50/p95/p99 latencies, error rate
    """
    from metrics import get_metrics
    metrics_collector = get_metrics()
    snapshot = metrics_collector.get_snapshot(operation)

    if not snapshot:
        raise http_404(f"No metrics found for operation: {operation}", resource="operation")

    return SuccessResponse(
        data=snapshot,
        message=f"Metrics for operation '{operation}' retrieved successfully"
    )


@router.post(
    "/operations/reset",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="metrics_reset_operations",
    summary="Reset operation metrics",
    description="Reset metrics for all operations or a specific operation (admin only)"
)
@handle_exceptions("reset operation metrics")
async def reset_operation_metrics(operation: str | None = None) -> SuccessResponse[Dict]:
    """
    Reset metrics (admin only)

    Args:
        operation: Optional operation to reset. If not provided, resets all metrics.
    """
    from metrics import get_metrics
    metrics_collector = get_metrics()
    metrics_collector.reset(operation)

    reset_data = {
        "status": "reset",
        "operation": operation or "all"
    }

    return SuccessResponse(
        data=reset_data,
        message=f"Metrics reset for {operation or 'all operations'}"
    )
