"""
Compatibility Shim for Structured Logger

The implementation now lives in the `api.monitoring` package:
- api.monitoring.logger: StructuredLogFormatter and utilities

This shim maintains backward compatibility.
"""

from api.monitoring.logger import (
    StructuredLogFormatter,
    get_logger,
    log_with_context,
    info_with_context,
    error_with_context,
    warning_with_context,
)

__all__ = [
    "StructuredLogFormatter",
    "get_logger",
    "log_with_context",
    "info_with_context",
    "error_with_context",
    "warning_with_context",
]
