"""
Structured Logging Utilities

Provides JSON-formatted structured logging for better observability:
- Request/response logging
- Error tracking with context
- Performance monitoring
- Audit trails
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from functools import wraps


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs.

    Makes logs machine-readable for log aggregation tools
    (Elasticsearch, CloudWatch, Datadog, etc.)
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers = []

        # Add JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        # Try to get correlation ID from context
        try:
            from api.middleware.correlation import get_correlation_id

            correlation_id = get_correlation_id()
            if correlation_id:
                kwargs["correlation_id"] = correlation_id
        except (ImportError, AttributeError):
            pass  # Silently fail if correlation middleware not available

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }

        if level == "DEBUG":
            self.logger.debug(json.dumps(log_data))
        elif level == "INFO":
            self.logger.info(json.dumps(log_data))
        elif level == "WARNING":
            self.logger.warning(json.dumps(log_data))
        elif level == "ERROR":
            self.logger.error(json.dumps(log_data))
        elif level == "CRITICAL":
            self.logger.critical(json.dumps(log_data))

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, error: Exception | None = None, **kwargs):
        """
        Log error message with optional exception details

        Args:
            message: Error description
            error: Exception object (will extract traceback)
            **kwargs: Additional context
        """
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["traceback"] = traceback.format_exc()

        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log("CRITICAL", message, **kwargs)

    def request(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """
        Log HTTP request

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            **kwargs: Additional context (user_id, ip, etc.)
        """
        self._log(
            "INFO",
            "HTTP Request",
            event_type="http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )

    def performance(self, operation: str, duration_ms: float, success: bool = True, **kwargs):
        """
        Log performance metrics

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **kwargs: Additional metrics
        """
        self._log(
            "INFO",
            f"Performance: {operation}",
            event_type="performance",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=success,
            **kwargs,
        )

    def audit(self, action: str, resource: str, user_id: str | None = None, **kwargs):
        """
        Log audit trail event

        Args:
            action: Action performed (create, update, delete, etc.)
            resource: Resource affected
            user_id: User who performed action
            **kwargs: Additional context
        """
        self._log(
            "INFO",
            f"Audit: {action} {resource}",
            event_type="audit",
            action=action,
            resource=resource,
            user_id=user_id,
            **kwargs,
        )


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for standard Python logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def log_execution(
    operation: str,
    log_success: bool = True,
    log_failure: bool = True,
    logger: StructuredLogger | None = None,
):
    """
    Decorator to log function execution with timing.

    Args:
        operation: Operation name for logging
        log_success: Whether to log successful executions
        log_failure: Whether to log failed executions
        logger: Logger instance (creates default if None)

    Usage:
        @log_execution("user_authentication")
        async def authenticate_user(username, password):
            # ...
            return user
    """
    if logger is None:
        logger = StructuredLogger(__name__)

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error = None

            try:
                result = await func(*args, **kwargs)
                success = True
                return result

            except Exception as e:
                error = e
                raise

            finally:
                duration_ms = (time.time() - start_time) * 1000

                if success and log_success:
                    logger.performance(operation=operation, duration_ms=duration_ms, success=True)
                elif not success and log_failure:
                    logger.performance(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(error) if error else None,
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error = None

            try:
                result = func(*args, **kwargs)
                success = True
                return result

            except Exception as e:
                error = e
                raise

            finally:
                duration_ms = (time.time() - start_time) * 1000

                if success and log_success:
                    logger.performance(operation=operation, duration_ms=duration_ms, success=True)
                elif not success and log_failure:
                    logger.performance(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(error) if error else None,
                    )

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global loggers
_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


def configure_logging(level: str | None = None, json_format: bool = True):
    """
    Configure global logging settings.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, reads from LOG_LEVEL environment variable or defaults based on ENVIRONMENT
        json_format: Whether to use JSON formatting

    Environment variables:
        LOG_LEVEL: Explicit log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        ENVIRONMENT: Environment name (development, staging, production)
                     - development: DEBUG
                     - staging: INFO
                     - production: WARNING
    """
    import os

    # Determine log level
    if level is None:
        level = os.getenv("LOG_LEVEL")

        if level is None:
            # Auto-detect based on environment
            environment = os.getenv("ENVIRONMENT", "development").lower()

            if environment == "production":
                level = "WARNING"
            elif environment == "staging":
                level = "INFO"
            else:  # development
                level = "DEBUG"

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Add handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger.addHandler(handler)


# Example usage contexts


def log_api_request(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """Convenience function for logging API requests"""
    logger = get_logger("api.requests")
    logger.request(method, path, status_code, duration_ms, **kwargs)


def log_error(message: str, error: Exception, **kwargs):
    """Convenience function for logging errors"""
    logger = get_logger("api.errors")
    logger.error(message, error=error, **kwargs)


def log_audit(action: str, resource: str, user_id: str | None = None, **kwargs):
    """Convenience function for audit logging"""
    logger = get_logger("api.audit")
    logger.audit(action, resource, user_id=user_id, **kwargs)


def slow_operation_marker(threshold_ms: float = 1000.0, logger_name: str = "api.performance"):
    """
    Decorator to mark and log slow operations.

    Logs a warning if operation exceeds threshold.

    Args:
        threshold_ms: Threshold in milliseconds (default: 1000ms = 1s)
        logger_name: Logger name to use

    Usage:
        @slow_operation_marker(threshold_ms=500)
        async def expensive_database_query():
            # ... slow query ...
            return results

        # Logs warning if query takes >500ms
    """

    def decorator(func):
        logger = get_logger(logger_name)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = f"{func.__module__}.{func.__name__}"

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation detected: {operation}",
                        event_type="slow_operation",
                        operation=operation,
                        duration_ms=round(duration_ms, 2),
                        threshold_ms=threshold_ms,
                        slowness_factor=round(duration_ms / threshold_ms, 2),
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation detected: {operation}",
                        event_type="slow_operation",
                        operation=operation,
                        duration_ms=round(duration_ms, 2),
                        threshold_ms=threshold_ms,
                        slowness_factor=round(duration_ms / threshold_ms, 2),
                    )

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
