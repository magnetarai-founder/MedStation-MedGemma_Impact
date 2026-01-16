"""
Monitoring Package

Comprehensive observability and metrics for ElohimOS:
- Lightweight operation metrics
- Prometheus metrics export
- Health check endpoints
- Request timing middleware
- Health diagnostics
- Performance monitoring
- Telemetry counters
- Structured logging
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

# Health Diagnostics
from api.monitoring.diagnostics import (
    HealthDiagnostics,
    get_health_diagnostics,
)

# Performance Monitor
from api.monitoring.performance import (
    PerformanceSnapshot,
    PerformanceMonitor,
    get_performance_monitor,
)

# Telemetry
from api.monitoring.telemetry import (
    TelemetryCounters,
    TelemetryMetric,
    get_telemetry,
    track_metric,
)

# Structured Logger
from api.monitoring.logger import (
    StructuredLogFormatter,
    get_logger,
    log_with_context,
    info_with_context,
    error_with_context,
    warning_with_context,
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
    # Health Diagnostics
    "HealthDiagnostics",
    "get_health_diagnostics",
    # Performance
    "PerformanceSnapshot",
    "PerformanceMonitor",
    "get_performance_monitor",
    # Telemetry
    "TelemetryCounters",
    "TelemetryMetric",
    "get_telemetry",
    "track_metric",
    # Structured Logger
    "StructuredLogFormatter",
    "get_logger",
    "log_with_context",
    "info_with_context",
    "error_with_context",
    "warning_with_context",
]
