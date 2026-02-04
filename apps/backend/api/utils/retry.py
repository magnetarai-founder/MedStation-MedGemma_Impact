"""
Retry and Error Recovery Utilities

Provides decorators and utilities for robust error handling:
- Exponential backoff retry
- Configurable retry strategies
- Graceful degradation
- Error logging and tracking
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retry_on: tuple[type[Exception], ...] = (Exception,)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool = True,
) -> float:
    """
    Calculate delay for exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(initial_delay * (exponential_base**attempt), max_delay)

    if jitter:
        import random

        # Add ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: type[Exception] | tuple[type[Exception], ...] = Exception,
    on_retry: Callable[[int, Exception], None] | None = None,
    fallback: Callable | None = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        retry_on: Exception types to retry on
        on_retry: Callback function called on each retry
        fallback: Fallback function to call if all retries fail

    Usage:
        @retry(max_attempts=5, initial_delay=2.0)
        async def unreliable_api_call():
            return await external_api.fetch()

        @retry(
            max_attempts=3,
            retry_on=(ConnectionError, TimeoutError),
            fallback=lambda: {"status": "cached"}
        )
        async def fetch_with_fallback():
            return await api.get_data()
    """
    # Normalize retry_on to tuple
    if not isinstance(retry_on, tuple):
        retry_on = (retry_on,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    # Log the retry attempt
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}: "
                        f"{type(e).__name__}: {e}"
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    # Don't delay after last attempt
                    if attempt < max_attempts - 1:
                        delay = calculate_backoff_delay(
                            attempt, initial_delay, max_delay, exponential_base, jitter
                        )
                        await asyncio.sleep(delay)

            # All retries exhausted
            logger.error(f"All {max_attempts} retry attempts exhausted for {func.__name__}")

            # Use fallback if provided
            if fallback:
                logger.info(f"Using fallback for {func.__name__}")
                return (
                    fallback(*args, **kwargs)
                    if not asyncio.iscoroutinefunction(fallback)
                    else await fallback(*args, **kwargs)
                )

            # Raise retry exhausted error
            raise RetryExhaustedError(max_attempts, last_exception)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}: "
                        f"{type(e).__name__}: {e}"
                    )

                    if on_retry:
                        on_retry(attempt + 1, e)

                    if attempt < max_attempts - 1:
                        delay = calculate_backoff_delay(
                            attempt, initial_delay, max_delay, exponential_base, jitter
                        )
                        time.sleep(delay)

            logger.error(f"All {max_attempts} retry attempts exhausted for {func.__name__}")

            if fallback:
                logger.info(f"Using fallback for {func.__name__}")
                return fallback(*args, **kwargs)

            raise RetryExhaustedError(max_attempts, last_exception)

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class GracefulDegradation:
    """
    Context manager for graceful degradation.

    Allows code to degrade gracefully when optional features fail.

    Usage:
        with GracefulDegradation(default_value=[]):
            result = expensive_optional_feature()
    """

    def __init__(
        self,
        default_value=None,
        log_errors: bool = True,
        suppress_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.default_value = default_value
        self.log_errors = log_errors
        self.suppress_exceptions = suppress_exceptions
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, self.suppress_exceptions):
            if self.log_errors:
                logger.warning(f"Graceful degradation triggered: {exc_type.__name__}: {exc_val}")
            self.exception = exc_val
            return True  # Suppress exception
        return False


def with_timeout(timeout_seconds: float, fallback=None):
    """
    Decorator to add timeout to async functions.

    Args:
        timeout_seconds: Maximum execution time in seconds
        fallback: Value to return on timeout

    Usage:
        @with_timeout(timeout_seconds=5.0, fallback={"status": "timeout"})
        async def slow_operation():
            await asyncio.sleep(10)
            return {"status": "success"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Function {func.__name__} timed out after {timeout_seconds}s")
                if fallback is not None:
                    return fallback
                raise

        return wrapper

    return decorator


class ErrorBudget:
    """
    Track error budget for SRE-style error management.

    Helps track if a service is within acceptable error rates.
    """

    def __init__(self, window_size: int = 100, error_threshold: float = 0.01):
        """
        Args:
            window_size: Number of recent requests to track
            error_threshold: Maximum acceptable error rate (e.g., 0.01 = 1%)
        """
        self.window_size = window_size
        self.error_threshold = error_threshold
        self.requests: list[bool] = []  # True = success, False = error

    def record_success(self):
        """Record a successful request"""
        self.requests.append(True)
        if len(self.requests) > self.window_size:
            self.requests.pop(0)

    def record_error(self):
        """Record a failed request"""
        self.requests.append(False)
        if len(self.requests) > self.window_size:
            self.requests.pop(0)

    def get_error_rate(self) -> float:
        """Get current error rate"""
        if not self.requests:
            return 0.0
        errors = sum(1 for r in self.requests if not r)
        return errors / len(self.requests)

    def is_within_budget(self) -> bool:
        """Check if error rate is within acceptable threshold"""
        return self.get_error_rate() <= self.error_threshold

    def get_remaining_budget(self) -> float:
        """Get remaining error budget as percentage"""
        current_rate = self.get_error_rate()
        if current_rate >= self.error_threshold:
            return 0.0
        return (self.error_threshold - current_rate) / self.error_threshold * 100


def safe_execute(func: Callable, *args, default=None, log_errors: bool = True, **kwargs):
    """
    Safely execute a function, returning default value on error.

    Useful for optional operations that shouldn't crash the main flow.

    Args:
        func: Function to execute
        *args: Positional arguments
        default: Default value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments

    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.warning(
                f"safe_execute caught error in {func.__name__}: " f"{type(e).__name__}: {e}"
            )
        return default


async def safe_execute_async(
    func: Callable, *args, default=None, log_errors: bool = True, **kwargs
):
    """
    Safely execute an async function, returning default value on error.

    Args:
        func: Async function to execute
        *args: Positional arguments
        default: Default value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments

    Returns:
        Function result or default value
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.warning(
                f"safe_execute_async caught error in {func.__name__}: " f"{type(e).__name__}: {e}"
            )
        return default
