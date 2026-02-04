"""
Performance monitoring decorators
"""
import logging
import time
from collections.abc import Callable
from functools import wraps

from .config import SLOW_QUERY_THRESHOLD_MS

logger = logging.getLogger(__name__)


def log_query_performance(operation: str):
    """Decorator to log database query performance"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(self, *args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                    logger.warning(
                        f"Slow query detected: {operation} took {duration_ms:.2f}ms "
                        f"(threshold: {SLOW_QUERY_THRESHOLD_MS}ms)"
                    )
                else:
                    logger.debug(f"Query: {operation} completed in {duration_ms:.2f}ms")

        return wrapper

    return decorator
