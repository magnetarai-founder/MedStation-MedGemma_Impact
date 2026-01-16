"""
Compatibility Shim for Observability Middleware

The implementation now lives in the `api.monitoring` package:
- api.monitoring.middleware: Request timing and observability

This shim maintains backward compatibility.
"""

from api.monitoring.middleware import (
    RequestTimingMiddleware,
    RequestMetrics,
    add_observability_middleware,
    get_request_metrics,
    get_endpoint_metrics,
    get_error_metrics,
    reset_metrics,
    SLOW_REQUEST_THRESHOLD_MS,
    VERY_SLOW_REQUEST_THRESHOLD_MS,
)

__all__ = [
    "RequestTimingMiddleware",
    "RequestMetrics",
    "add_observability_middleware",
    "get_request_metrics",
    "get_endpoint_metrics",
    "get_error_metrics",
    "reset_metrics",
    "SLOW_REQUEST_THRESHOLD_MS",
    "VERY_SLOW_REQUEST_THRESHOLD_MS",
]
