"""
Observability Middleware

Provides request/response timing, error tracking, and metrics collection.

Features:
- Request timing (total time, processing time)
- Slow request detection
- Error tracking and aggregation
- Request/response logging
- Metrics collection

Usage:
    from fastapi import FastAPI
    from api.observability_middleware import add_observability_middleware

    app = FastAPI()
    add_observability_middleware(app)
"""

import time
import logging
import traceback
from typing import Callable, Dict, List
from datetime import datetime
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Configuration
SLOW_REQUEST_THRESHOLD_MS = 1000  # Log requests > 1 second
VERY_SLOW_REQUEST_THRESHOLD_MS = 5000  # Warn on requests > 5 seconds


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing and log slow requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timing."""
        start_time = time.time()
        path = request.url.path
        method = request.method

        try:
            # Process request
            response = await call_next(request)

            # Calculate timing
            elapsed_ms = (time.time() - start_time) * 1000

            # Log based on timing
            status_code = response.status_code

            if elapsed_ms > VERY_SLOW_REQUEST_THRESHOLD_MS:
                logger.warning(
                    f"⚠️  VERY SLOW REQUEST ({elapsed_ms:.0f}ms): "
                    f"{method} {path} → {status_code}"
                )
            elif elapsed_ms > SLOW_REQUEST_THRESHOLD_MS:
                logger.info(
                    f"🐌 Slow request ({elapsed_ms:.0f}ms): "
                    f"{method} {path} → {status_code}"
                )
            else:
                logger.debug(
                    f"✓ {method} {path} → {status_code} ({elapsed_ms:.0f}ms)"
                )

            # Add timing header
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

            # Track metrics
            RequestMetrics.record_request(
                method=method,
                path=path,
                status_code=status_code,
                elapsed_ms=elapsed_ms
            )

            return response

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000

            logger.error(
                f"❌ Request failed ({elapsed_ms:.0f}ms): "
                f"{method} {path} - {type(e).__name__}: {e}"
            )
            logger.debug(f"Traceback: {traceback.format_exc()}")

            # Track error
            RequestMetrics.record_error(
                method=method,
                path=path,
                error_type=type(e).__name__,
                elapsed_ms=elapsed_ms
            )

            # Return 500 error
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "type": type(e).__name__,
                    "detail": str(e) if logger.level <= logging.DEBUG else "See server logs"
                }
            )


class RequestMetrics:
    """Track request metrics for monitoring."""

    _total_requests = 0
    _slow_requests = 0
    _very_slow_requests = 0
    _failed_requests = 0
    _total_time_ms = 0.0

    # Track by endpoint
    _endpoint_stats: Dict[str, Dict] = defaultdict(lambda: {
        "count": 0,
        "total_time_ms": 0.0,
        "errors": 0
    })

    # Track errors by type
    _error_counts: Dict[str, int] = defaultdict(int)

    # Recent errors for debugging
    _recent_errors: List[Dict] = []
    _max_recent_errors = 50

    @classmethod
    def record_request(cls, method: str, path: str, status_code: int, elapsed_ms: float):
        """Record a successful request."""
        cls._total_requests += 1
        cls._total_time_ms += elapsed_ms

        if elapsed_ms > VERY_SLOW_REQUEST_THRESHOLD_MS:
            cls._very_slow_requests += 1
        elif elapsed_ms > SLOW_REQUEST_THRESHOLD_MS:
            cls._slow_requests += 1

        # Track by endpoint
        endpoint_key = f"{method} {path}"
        cls._endpoint_stats[endpoint_key]["count"] += 1
        cls._endpoint_stats[endpoint_key]["total_time_ms"] += elapsed_ms

        if status_code >= 400:
            cls._failed_requests += 1
            cls._endpoint_stats[endpoint_key]["errors"] += 1

    @classmethod
    def record_error(cls, method: str, path: str, error_type: str, elapsed_ms: float):
        """Record a request error."""
        cls._failed_requests += 1
        cls._total_requests += 1
        cls._total_time_ms += elapsed_ms

        # Track error type
        cls._error_counts[error_type] += 1

        # Track by endpoint
        endpoint_key = f"{method} {path}"
        cls._endpoint_stats[endpoint_key]["count"] += 1
        cls._endpoint_stats[endpoint_key]["total_time_ms"] += elapsed_ms
        cls._endpoint_stats[endpoint_key]["errors"] += 1

        # Store recent error
        cls._recent_errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "path": path,
            "error_type": error_type,
            "elapsed_ms": elapsed_ms
        })

        # Keep only recent errors
        if len(cls._recent_errors) > cls._max_recent_errors:
            cls._recent_errors.pop(0)

    @classmethod
    def get_stats(cls) -> dict:
        """Get overall request statistics."""
        avg_time = cls._total_time_ms / cls._total_requests if cls._total_requests > 0 else 0

        return {
            "total_requests": cls._total_requests,
            "successful_requests": cls._total_requests - cls._failed_requests,
            "failed_requests": cls._failed_requests,
            "slow_requests": cls._slow_requests,
            "very_slow_requests": cls._very_slow_requests,
            "average_time_ms": round(avg_time, 2),
            "total_time_ms": round(cls._total_time_ms, 2)
        }

    @classmethod
    def get_endpoint_stats(cls, limit: int = 10) -> List[Dict]:
        """Get statistics by endpoint (top N by request count)."""
        stats = []

        for endpoint, data in cls._endpoint_stats.items():
            avg_time = data["total_time_ms"] / data["count"] if data["count"] > 0 else 0

            stats.append({
                "endpoint": endpoint,
                "count": data["count"],
                "average_time_ms": round(avg_time, 2),
                "total_time_ms": round(data["total_time_ms"], 2),
                "errors": data["errors"],
                "error_rate": round((data["errors"] / data["count"] * 100) if data["count"] > 0 else 0, 2)
            })

        # Sort by request count
        stats.sort(key=lambda x: x["count"], reverse=True)

        return stats[:limit]

    @classmethod
    def get_error_stats(cls) -> Dict:
        """Get error statistics by type."""
        return {
            "error_counts": dict(cls._error_counts),
            "recent_errors": cls._recent_errors[-10:],  # Last 10 errors
            "total_error_types": len(cls._error_counts)
        }

    @classmethod
    def reset(cls):
        """Reset all statistics."""
        cls._total_requests = 0
        cls._slow_requests = 0
        cls._very_slow_requests = 0
        cls._failed_requests = 0
        cls._total_time_ms = 0.0
        cls._endpoint_stats.clear()
        cls._error_counts.clear()
        cls._recent_errors.clear()


def add_observability_middleware(app: FastAPI):
    """
    Add observability middleware to FastAPI app.

    Args:
        app: FastAPI application instance

    Example:
        app = FastAPI()
        add_observability_middleware(app)
    """
    app.add_middleware(RequestTimingMiddleware)
    logger.info("✅ Observability middleware enabled")


def get_request_metrics() -> dict:
    """Get current request metrics."""
    return RequestMetrics.get_stats()


def get_endpoint_metrics(limit: int = 10) -> List[Dict]:
    """Get endpoint-specific metrics."""
    return RequestMetrics.get_endpoint_stats(limit)


def get_error_metrics() -> Dict:
    """Get error metrics."""
    return RequestMetrics.get_error_stats()


def reset_metrics():
    """Reset all metrics."""
    RequestMetrics.reset()
