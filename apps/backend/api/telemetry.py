"""
Compatibility Shim for Telemetry

The implementation now lives in the `api.monitoring` package:
- api.monitoring.telemetry: TelemetryCounters class

This shim maintains backward compatibility.
"""

from api.monitoring.telemetry import (
    TelemetryCounters,
    TelemetryMetric,
    get_telemetry,
    track_metric,
)

__all__ = [
    "TelemetryCounters",
    "TelemetryMetric",
    "get_telemetry",
    "track_metric",
]
