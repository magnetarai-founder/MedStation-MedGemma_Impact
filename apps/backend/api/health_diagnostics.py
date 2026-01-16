"""
Compatibility Shim for Health Diagnostics

The implementation now lives in the `api.monitoring` package:
- api.monitoring.diagnostics: HealthDiagnostics class

This shim maintains backward compatibility.
"""

from api.monitoring.diagnostics import (
    HealthDiagnostics,
    get_health_diagnostics,
)

__all__ = [
    "HealthDiagnostics",
    "get_health_diagnostics",
]
