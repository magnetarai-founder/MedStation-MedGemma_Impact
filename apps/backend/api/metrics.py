"""
Lightweight Observability Metrics for ElohimOS
Tracks operation counts and latencies for production bottleneck identification
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics for a specific operation"""
    operation: str
    count: int
    total_duration_ms: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    last_recorded: str
    errors: int = 0


@dataclass
class OperationMetrics:
    """Metrics for a single operation type"""
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    durations: List[float] = field(default_factory=list)
    errors: int = 0
    last_recorded: Optional[datetime] = None

    # Keep last 1000 durations for percentile calculation
    max_durations_stored: int = 1000

    def record(self, duration_ms: float, error: bool = False):
        """Record a new operation execution"""
        self.count += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.last_recorded = datetime.utcnow()

        if error:
            self.errors += 1

        # Store duration for percentile calculation
        self.durations.append(duration_ms)
        if len(self.durations) > self.max_durations_stored:
            self.durations.pop(0)

    def get_snapshot(self, operation_name: str) -> MetricSnapshot:
        """Get current metrics snapshot"""
        avg = self.total_duration_ms / self.count if self.count > 0 else 0

        # Calculate percentiles
        sorted_durations = sorted(self.durations)
        p50 = self._percentile(sorted_durations, 50)
        p95 = self._percentile(sorted_durations, 95)
        p99 = self._percentile(sorted_durations, 99)

        return MetricSnapshot(
            operation=operation_name,
            count=self.count,
            total_duration_ms=round(self.total_duration_ms, 2),
            avg_duration_ms=round(avg, 2),
            min_duration_ms=round(self.min_duration_ms if self.min_duration_ms != float('inf') else 0, 2),
            max_duration_ms=round(self.max_duration_ms, 2),
            p50_duration_ms=round(p50, 2),
            p95_duration_ms=round(p95, 2),
            p99_duration_ms=round(p99, 2),
            last_recorded=self.last_recorded.isoformat() if self.last_recorded else "never",
            errors=self.errors
        )

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0

        index = (len(sorted_values) - 1) * percentile / 100
        floor_index = int(index)
        ceil_index = min(floor_index + 1, len(sorted_values) - 1)

        if floor_index == ceil_index:
            return sorted_values[floor_index]

        # Linear interpolation
        lower = sorted_values[floor_index]
        upper = sorted_values[ceil_index]
        fraction = index - floor_index

        return lower + (upper - lower) * fraction


class MetricsCollector:
    """
    Centralized metrics collector

    Usage:
        metrics = get_metrics()

        # Record operation
        with metrics.track("sql_query"):
            execute_sql_query()

        # Or manually
        start = time.time()
        result = execute_sql_query()
        metrics.record("sql_query", (time.time() - start) * 1000)

        # Get snapshot
        snapshot = metrics.get_snapshot("sql_query")
        print(f"Avg: {snapshot.avg_duration_ms}ms, P95: {snapshot.p95_duration_ms}ms")
    """

    def __init__(self):
        self._metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._lock = Lock()

    def record(self, operation: str, duration_ms: float, error: bool = False):
        """Record an operation execution"""
        with self._lock:
            self._metrics[operation].record(duration_ms, error)

            if duration_ms > 1000:  # Log slow operations (>1s)
                logger.warning(f"⏱️  Slow operation '{operation}': {duration_ms:.2f}ms")

    def track(self, operation: str):
        """Context manager for tracking operation duration"""
        return _MetricsContext(self, operation)

    def increment_error(self, operation: str):
        """Increment error count for an operation"""
        with self._lock:
            self._metrics[operation].errors += 1

    def get_snapshot(self, operation: str) -> Optional[MetricSnapshot]:
        """Get metrics snapshot for specific operation"""
        with self._lock:
            if operation not in self._metrics:
                return None
            return self._metrics[operation].get_snapshot(operation)

    def get_all_snapshots(self) -> List[MetricSnapshot]:
        """Get all metrics snapshots"""
        with self._lock:
            return [
                metrics.get_snapshot(op_name)
                for op_name, metrics in self._metrics.items()
            ]

    def get_summary(self) -> Dict:
        """Get summary of all metrics"""
        snapshots = self.get_all_snapshots()

        return {
            "total_operations": sum(s.count for s in snapshots),
            "total_errors": sum(s.errors for s in snapshots),
            "tracked_operations": len(snapshots),
            "operations": [
                {
                    "name": s.operation,
                    "count": s.count,
                    "avg_ms": s.avg_duration_ms,
                    "p95_ms": s.p95_duration_ms,
                    "errors": s.errors,
                    "error_rate": round(s.errors / s.count * 100, 2) if s.count > 0 else 0
                }
                for s in sorted(snapshots, key=lambda x: x.count, reverse=True)
            ]
        }

    def reset(self, operation: Optional[str] = None):
        """Reset metrics for specific operation or all operations"""
        with self._lock:
            if operation:
                if operation in self._metrics:
                    del self._metrics[operation]
            else:
                self._metrics.clear()


class _MetricsContext:
    """Context manager for tracking operation duration"""

    def __init__(self, collector: MetricsCollector, operation: str):
        self.collector = collector
        self.operation = operation
        self.start_time = None
        self.error = False

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.error = exc_type is not None
            self.collector.record(self.operation, duration_ms, error=self.error)
        return False  # Don't suppress exceptions


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
