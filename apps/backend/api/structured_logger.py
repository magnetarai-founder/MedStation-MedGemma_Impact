"""
Structured Logging Utilities for ElohimOS
Provides request ID propagation and structured log output
"""

import logging
import json
from typing import Any, Dict, Optional
from contextvars import ContextVar
from datetime import datetime

# Import request_id context from main
try:
    from main import request_id_ctx
except ImportError:
    # Fallback if imported before main
    request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class StructuredLogFormatter(logging.Formatter):
    """
    JSON formatter for structured logging with request_id propagation

    Usage:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with request_id"""

        # Get request_id from context
        request_id = request_id_ctx.get()

        log_obj = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request_id if available
        if request_id:
            log_obj["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra"):
            log_obj.update(record.extra)

        return json.dumps(log_obj)


def get_logger(name: str, structured: bool = False) -> logging.Logger:
    """
    Get a logger instance with optional structured output

    Args:
        name: Logger name (usually __name__)
        structured: If True, use JSON structured output

    Returns:
        Logger instance

    Usage:
        # Standard logging (default)
        logger = get_logger(__name__)

        # Structured JSON logging
        logger = get_logger(__name__, structured=True)
    """
    logger = logging.getLogger(name)

    if structured and not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log with automatic request_id context inclusion

    Args:
        logger: Logger instance
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        message: Log message
        extra: Additional structured fields

    Usage:
        log_with_context(logger, 'info', 'User logged in', {'user_id': 'abc123'})
    """
    request_id = request_id_ctx.get()

    log_data = extra or {}
    if request_id:
        log_data["request_id"] = request_id

    log_fn = getattr(logger, level.lower())
    log_fn(message, extra=log_data)


# Convenience functions
def info_with_context(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log info with request context"""
    log_with_context(logger, "info", message, kwargs)


def error_with_context(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log error with request context"""
    log_with_context(logger, "error", message, kwargs)


def warning_with_context(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log warning with request context"""
    log_with_context(logger, "warning", message, kwargs)
