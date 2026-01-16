"""
Compatibility Shim for Prometheus Metrics

The implementation now lives in the `api.monitoring` package:
- api.monitoring.prometheus: PrometheusMetricsExporter

This shim maintains backward compatibility.
"""

from api.monitoring.prometheus import (
    PrometheusMetricsExporter,
    get_prometheus_exporter,
)

__all__ = [
    "PrometheusMetricsExporter",
    "get_prometheus_exporter",
]
