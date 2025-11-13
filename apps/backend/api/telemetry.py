"""
Telemetry Counters for Model Operations

Best-effort, non-blocking metrics collection for operational insights.
Failures are silent - telemetry never blocks application flow.
"""

import logging
from typing import Optional, Dict
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class TelemetryCounters:
    """
    Lightweight telemetry counter system

    Tracks operational metrics for dashboards and monitoring:
    - Model preference toggles
    - Hot slot assignments
    - Session model updates
    - Token near-limit warnings
    - Context summarization invocations

    Thread-safe, in-memory counters with optional persistence.
    """

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self._lock = Lock()
        self._enabled = True

    def increment(self, metric_name: str, value: int = 1) -> None:
        """
        Increment a counter by the specified value

        Args:
            metric_name: Name of the metric (e.g., "model.preference.toggle")
            value: Amount to increment (default: 1)
        """
        if not self._enabled:
            return

        try:
            with self._lock:
                self.counters[metric_name] += value
        except Exception as e:
            # Silent failure - telemetry must never block operations
            logger.debug(f"Telemetry increment failed for {metric_name}: {e}")

    def get_counter(self, metric_name: str) -> int:
        """
        Get current value of a counter

        Args:
            metric_name: Name of the metric

        Returns:
            Current counter value (0 if not found)
        """
        try:
            with self._lock:
                return self.counters.get(metric_name, 0)
        except Exception as e:
            logger.debug(f"Telemetry get failed for {metric_name}: {e}")
            return 0

    def get_all_counters(self) -> Dict[str, int]:
        """
        Get all current counter values

        Returns:
            Dictionary of metric names to values
        """
        try:
            with self._lock:
                return dict(self.counters)
        except Exception as e:
            logger.debug(f"Telemetry get_all failed: {e}")
            return {}

    def reset_counter(self, metric_name: str) -> None:
        """
        Reset a specific counter to zero

        Args:
            metric_name: Name of the metric to reset
        """
        try:
            with self._lock:
                if metric_name in self.counters:
                    self.counters[metric_name] = 0
        except Exception as e:
            logger.debug(f"Telemetry reset failed for {metric_name}: {e}")

    def disable(self) -> None:
        """Disable telemetry collection"""
        self._enabled = False

    def enable(self) -> None:
        """Enable telemetry collection"""
        self._enabled = True


# Global telemetry instance
_telemetry: Optional[TelemetryCounters] = None


def get_telemetry() -> TelemetryCounters:
    """
    Get or create global telemetry instance

    Returns:
        TelemetryCounters instance
    """
    global _telemetry

    if _telemetry is None:
        _telemetry = TelemetryCounters()

    return _telemetry


# Metric name constants
class TelemetryMetric:
    """Standard telemetry metric names"""

    # Model Operations
    MODEL_PREFERENCE_TOGGLED = "model.preference.toggled"
    MODEL_HOT_SLOT_ASSIGNED = "model.hot_slot.assigned"
    MODEL_SESSION_UPDATED = "model.session.updated"

    # Session Operations
    TOKEN_NEAR_LIMIT_WARNING = "session.token.near_limit"
    SUMMARIZE_CONTEXT_INVOKED = "session.summarize.invoked"

    # Chat Operations
    MESSAGES_SENT = "chat.messages.sent"
    FILES_UPLOADED = "chat.files.uploaded"


def track_metric(metric_name: str, value: int = 1) -> None:
    """
    Convenience function to track a metric

    Non-blocking, silent on failure.

    Args:
        metric_name: Name of the metric (use TelemetryMetric constants)
        value: Amount to increment (default: 1)
    """
    try:
        telemetry = get_telemetry()
        telemetry.increment(metric_name, value)
    except Exception as e:
        # Silent failure
        logger.debug(f"Metric tracking failed for {metric_name}: {e}")
