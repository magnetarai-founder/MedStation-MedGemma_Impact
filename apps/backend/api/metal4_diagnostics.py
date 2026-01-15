"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.diagnostics import Metal4Diagnostics, get_diagnostics, QueueStats, PerformanceMetrics

__all__ = ["Metal4Diagnostics", "get_diagnostics", "QueueStats", "PerformanceMetrics"]
