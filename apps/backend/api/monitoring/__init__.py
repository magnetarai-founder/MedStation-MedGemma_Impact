"""
Monitoring Package

Observability and metrics for ElohimOS:
- Lightweight operation metrics
- Prometheus metrics export
- Health check endpoints
- Request timing middleware
"""

from api.monitoring.metrics import (
    MetricSnapshot,
    OperationMetrics,
    MetricsCollector,
    get_metrics,
)
from api.monitoring.prometheus import (
    PrometheusMetricsExporter,
    get_prometheus_exporter,
)
from api.monitoring.routes import router
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
    # Metrics
    "MetricSnapshot",
    "OperationMetrics",
    "MetricsCollector",
    "get_metrics",
    # Prometheus
    "PrometheusMetricsExporter",
    "get_prometheus_exporter",
    # Routes
    "router",
    # Middleware
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
