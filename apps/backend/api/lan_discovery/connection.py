"""
LAN Discovery Connection Management

Connection state, retry logic with exponential backoff, and health tracking.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state for hub connections"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class RetryConfig:
    """Configuration for connection retry logic"""
    max_retries: int = 5
    initial_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: float = 0.1  # ±10% randomization


@dataclass
class ConnectionHealth:
    """Tracks connection health status"""
    last_heartbeat: Optional[datetime] = None
    consecutive_failures: int = 0
    total_reconnects: int = 0
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_error: Optional[str] = None

    def record_success(self) -> None:
        """Record successful heartbeat/connection"""
        self.last_heartbeat = datetime.now(UTC)
        self.consecutive_failures = 0
        self.state = ConnectionState.CONNECTED
        self.last_error = None

    def record_failure(self, error: str) -> None:
        """Record failed heartbeat/connection"""
        self.consecutive_failures += 1
        self.last_error = error

    def record_reconnect(self) -> None:
        """Record reconnection attempt"""
        self.total_reconnects += 1
        self.state = ConnectionState.RECONNECTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "consecutive_failures": self.consecutive_failures,
            "total_reconnects": self.total_reconnects,
            "state": self.state.value,
            "last_error": self.last_error,
        }


class ConnectionRetryHandler:
    """
    Handles connection retry logic with exponential backoff.

    Usage:
        handler = ConnectionRetryHandler(config)
        async for delay in handler:
            try:
                await connect()
                handler.mark_success()
                break
            except ConnectionError as e:
                handler.mark_failure(str(e))
                # Loop continues with next delay
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempt = 0
        self._exhausted = False

    def __aiter__(self):
        self._attempt = 0
        self._exhausted = False
        return self

    async def __anext__(self) -> float:
        """Return next delay, or raise StopAsyncIteration if exhausted"""
        if self._exhausted or self._attempt >= self.config.max_retries:
            self._exhausted = True
            raise StopAsyncIteration

        delay = self._calculate_delay()
        self._attempt += 1

        if delay > 0:
            await asyncio.sleep(delay)

        return delay

    def _calculate_delay(self) -> float:
        """Calculate delay with exponential backoff and jitter"""
        if self._attempt == 0:
            return 0  # No delay for first attempt

        delay = self.config.initial_delay * (
            self.config.backoff_multiplier ** (self._attempt - 1)
        )
        delay = min(delay, self.config.max_delay)

        # Add jitter
        jitter_range = delay * self.config.jitter
        delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def mark_success(self) -> None:
        """Mark connection as successful, stops iteration"""
        self._exhausted = True

    def mark_failure(self, error: str) -> None:
        """Mark connection as failed, continues iteration"""
        logger.warning(
            f"Connection attempt {self._attempt}/{self.config.max_retries} failed: {error}"
        )

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def is_exhausted(self) -> bool:
        return self._exhausted
