"""
Circuit Breaker Pattern Implementation

Provides resilience for external service calls by:
- Detecting failing services and preventing cascading failures
- Automatically recovering when services come back online
- Providing fallback behavior during outages
- Tracking failure metrics for monitoring

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests fail fast
- HALF_OPEN: Testing if service has recovered
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service failing, fast-fail
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open to close
    timeout: int = 60  # Seconds before attempting recovery
    expected_exception: type = Exception  # Exception type to catch


@dataclass
class CircuitBreakerMetrics:
    """Metrics for monitoring circuit breaker"""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""

    def __init__(self, service_name: str, retry_after: int):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {service_name}. " f"Retry after {retry_after} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Usage:
        cb = CircuitBreaker(name="ollama", failure_threshold=5)

        @cb.call
        async def call_ollama():
            # Call external service
            return await ollama_client.generate()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            expected_exception=expected_exception,
        )
        self.metrics = CircuitBreakerMetrics()
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self.metrics.state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.metrics.last_failure_time is None:
            return True

        elapsed = time.time() - self.metrics.last_failure_time
        return elapsed >= self.config.timeout

    def _record_success(self):
        """Record successful call"""
        with self._lock:
            self.metrics.total_calls += 1
            self.metrics.total_successes += 1

            if self.metrics.state == CircuitState.HALF_OPEN:
                self.metrics.success_count += 1

                # Close circuit if enough successes
                if self.metrics.success_count >= self.config.success_threshold:
                    self._transition_to_closed()

            elif self.metrics.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.metrics.failure_count = 0

    def _record_failure(self):
        """Record failed call"""
        with self._lock:
            self.metrics.total_calls += 1
            self.metrics.total_failures += 1
            self.metrics.failure_count += 1
            self.metrics.last_failure_time = time.time()

            if self.metrics.state == CircuitState.HALF_OPEN:
                # Failed during recovery test, reopen circuit
                self._transition_to_open()

            elif self.metrics.state == CircuitState.CLOSED:
                # Open circuit if threshold exceeded
                if self.metrics.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()

    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.metrics.state = CircuitState.OPEN
        self.metrics.last_state_change = time.time()
        self.metrics.success_count = 0
        logger.warning(f"CircuitBreaker {self.name}: OPEN", failures=self.metrics.failure_count)

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.metrics.state = CircuitState.HALF_OPEN
        self.metrics.last_state_change = time.time()
        self.metrics.failure_count = 0
        self.metrics.success_count = 0
        logger.info(f"CircuitBreaker {self.name}: HALF_OPEN (testing recovery)")

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.metrics.state = CircuitState.CLOSED
        self.metrics.last_state_change = time.time()
        self.metrics.failure_count = 0
        self.metrics.success_count = 0
        logger.info(f"CircuitBreaker {self.name}: CLOSED (recovered)")

    def call(self, fallback: Callable | None = None):
        """
        Decorator to protect function with circuit breaker.

        Args:
            fallback: Optional fallback function to call when circuit is open

        Usage:
            @circuit_breaker.call(fallback=lambda: {"status": "unavailable"})
            async def call_service():
                return await external_api.call()
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Check circuit state
                if self.metrics.state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self._transition_to_half_open()
                    else:
                        # Circuit still open, fail fast
                        if fallback:
                            return (
                                fallback(*args, **kwargs)
                                if not asyncio.iscoroutinefunction(fallback)
                                else await fallback(*args, **kwargs)
                            )

                        retry_after = int(
                            self.config.timeout - (time.time() - self.metrics.last_failure_time)
                        )
                        raise CircuitBreakerOpenError(self.name, max(0, retry_after))

                # Attempt call
                try:
                    result = await func(*args, **kwargs)
                    self._record_success()
                    return result

                except self.config.expected_exception:
                    self._record_failure()

                    # Use fallback if available
                    if fallback:
                        return (
                            fallback(*args, **kwargs)
                            if not asyncio.iscoroutinefunction(fallback)
                            else await fallback(*args, **kwargs)
                        )

                    raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Check circuit state
                if self.metrics.state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self._transition_to_half_open()
                    else:
                        # Circuit still open, fail fast
                        if fallback:
                            return fallback(*args, **kwargs)

                        retry_after = int(
                            self.config.timeout - (time.time() - self.metrics.last_failure_time)
                        )
                        raise CircuitBreakerOpenError(self.name, max(0, retry_after))

                # Attempt call
                try:
                    result = func(*args, **kwargs)
                    self._record_success()
                    return result

                except self.config.expected_exception:
                    self._record_failure()

                    # Use fallback if available
                    if fallback:
                        return fallback(*args, **kwargs)

                    raise

            import inspect

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for monitoring"""
        return {
            "name": self.name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_calls": self.metrics.total_calls,
            "total_failures": self.metrics.total_failures,
            "total_successes": self.metrics.total_successes,
            "failure_rate": (
                self.metrics.total_failures / self.metrics.total_calls * 100
                if self.metrics.total_calls > 0
                else 0
            ),
            "last_failure_time": self.metrics.last_failure_time,
            "last_state_change": self.metrics.last_state_change,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }

    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            self._transition_to_closed()


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: int = 60,
    expected_exception: type = Exception,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.

    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening
        success_threshold: Number of successes to close from half-open
        timeout: Seconds before attempting recovery
        expected_exception: Exception type to catch

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
                expected_exception=expected_exception,
            )
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers"""
    with _registry_lock:
        return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """Reset all circuit breakers to CLOSED state"""
    with _registry_lock:
        for cb in _circuit_breakers.values():
            cb.reset()
