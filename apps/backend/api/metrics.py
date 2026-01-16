"""
Compatibility Shim for Metrics

The implementation now lives in the `api.monitoring` package:
- api.monitoring.metrics: MetricsCollector and related classes

This shim maintains backward compatibility.
"""

from api.monitoring.metrics import (
    MetricSnapshot,
    OperationMetrics,
    MetricsCollector,
    get_metrics,
)

__all__ = [
    "MetricSnapshot",
    "OperationMetrics",
    "MetricsCollector",
    "get_metrics",
]
