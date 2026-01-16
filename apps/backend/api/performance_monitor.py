"""
Compatibility Shim for Performance Monitor

The implementation now lives in the `api.monitoring` package:
- api.monitoring.performance: PerformanceMonitor class

This shim maintains backward compatibility.
"""

from api.monitoring.performance import (
    PerformanceSnapshot,
    PerformanceMonitor,
    get_performance_monitor,
)

__all__ = [
    "PerformanceSnapshot",
    "PerformanceMonitor",
    "get_performance_monitor",
]
