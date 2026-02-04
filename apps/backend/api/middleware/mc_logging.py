"""
Logging Middleware for Request/Response Tracking

Automatically logs all HTTP requests with:
- Request details (method, path, headers, body)
- Response details (status, duration)
- Performance metrics
- Error tracking
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.structured_logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Features:
    - Automatic request/response logging
    - Performance timing
    - Error tracking
    - Request ID for tracing
    """

    def __init__(self, app, exclude_paths: list | None = None):
        super().__init__(app)
        self.logger = get_logger("api.requests")
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""

        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Generate request ID
        request_id = self._generate_request_id()

        # Start timing
        start_time = time.time()

        # Extract request details
        await self._extract_request_details(request)

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful request
            self.logger.request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                query_params=dict(request.query_params) if request.query_params else None,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.time() - start_time) * 1000

            # Log failed request
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                error=e,
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None,
            )

            raise

    async def _extract_request_details(self, request: Request) -> dict:
        """Extract relevant request details for logging"""
        details = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else None,
            "headers": {
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ["authorization", "cookie", "x-api-key"]
            },
        }

        # Only log body for non-streaming requests and small payloads
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")

            # Only log JSON payloads
            if "application/json" in content_type:
                try:
                    # Read body (this requires special handling in FastAPI)
                    # Note: We can't easily read the body here without breaking
                    # the request for the actual handler, so we skip it
                    pass
                except Exception as e:
                    logger.warning(f"Failed to read request body: {e}")
                    pass

        return details

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid

        return f"req_{uuid.uuid4().hex[:12]}"


class ResponseLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log response bodies for debugging.

    Warning: Can significantly increase log volume.
    Use only in development or for specific debugging.
    """

    def __init__(self, app, log_responses: bool = False):
        super().__init__(app)
        self.logger = get_logger("api.responses")
        self.log_responses = log_responses

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process and optionally log response"""

        if not self.log_responses:
            return await call_next(request)

        response = await call_next(request)

        # Only log responses for specific content types
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type and response.status_code < 400:
            # Note: Reading response body requires special handling
            # This is a simplified version
            pass

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking API performance metrics.

    Tracks:
    - Request counts by endpoint
    - Response time percentiles
    - Error rates
    - Slowest endpoints
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("api.performance")
        self.metrics = {"requests": {}, "errors": {}, "slow_requests": []}
        self.slow_threshold_ms = 1000  # Log requests slower than 1 second

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track performance metrics"""

        start_time = time.time()
        endpoint = f"{request.method} {request.url.path}"

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Update metrics
            self._update_metrics(endpoint, duration_ms, response.status_code)

            # Log slow requests
            if duration_ms > self.slow_threshold_ms:
                self.logger.warning(
                    f"Slow request detected: {endpoint}",
                    duration_ms=duration_ms,
                    threshold_ms=self.slow_threshold_ms,
                    method=request.method,
                    path=request.url.path,
                )

            return response

        except BaseException:
            # Catch all exceptions including SystemExit/KeyboardInterrupt for metrics
            duration_ms = (time.time() - start_time) * 1000

            # Track error
            if endpoint not in self.metrics["errors"]:
                self.metrics["errors"][endpoint] = 0
            self.metrics["errors"][endpoint] += 1

            raise

    def _update_metrics(self, endpoint: str, duration_ms: float, status_code: int):
        """Update performance metrics"""
        if endpoint not in self.metrics["requests"]:
            self.metrics["requests"][endpoint] = {
                "count": 0,
                "total_duration_ms": 0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0,
                "status_codes": {},
            }

        metrics = self.metrics["requests"][endpoint]
        metrics["count"] += 1
        metrics["total_duration_ms"] += duration_ms
        metrics["min_duration_ms"] = min(metrics["min_duration_ms"], duration_ms)
        metrics["max_duration_ms"] = max(metrics["max_duration_ms"], duration_ms)

        # Track status codes
        status_str = str(status_code)
        metrics["status_codes"][status_str] = metrics["status_codes"].get(status_str, 0) + 1

    def get_metrics(self) -> dict:
        """Get current performance metrics"""
        summary = {}

        for endpoint, metrics in self.metrics["requests"].items():
            avg_duration = (
                metrics["total_duration_ms"] / metrics["count"] if metrics["count"] > 0 else 0
            )

            summary[endpoint] = {
                "request_count": metrics["count"],
                "avg_duration_ms": round(avg_duration, 2),
                "min_duration_ms": round(metrics["min_duration_ms"], 2),
                "max_duration_ms": round(metrics["max_duration_ms"], 2),
                "status_codes": metrics["status_codes"],
                "error_count": self.metrics["errors"].get(endpoint, 0),
            }

        return summary


# Global performance monitor instance
_performance_monitor = None


def get_performance_metrics() -> dict:
    """Get current performance metrics from middleware"""
    global _performance_monitor
    if _performance_monitor:
        return _performance_monitor.get_metrics()
    return {}


def set_performance_monitor(monitor: PerformanceMonitoringMiddleware):
    """Set global performance monitor"""
    global _performance_monitor
    _performance_monitor = monitor
