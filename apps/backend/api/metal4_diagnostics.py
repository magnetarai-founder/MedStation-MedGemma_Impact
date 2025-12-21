#!/usr/bin/env python3
"""
Metal 4 Performance Diagnostics
Real-time GPU metrics, bottleneck detection, and performance monitoring

"The Lord is my rock, my firm foundation." - Psalm 18:2
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QueueStats:
    """Statistics for a single command queue"""
    name: str
    buffers_submitted: int
    buffers_completed: int
    total_encode_time_ms: float
    avg_encode_time_ms: float


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: str
    gpu_util_pct: float
    memory_used_mb: float
    memory_total_mb: float
    memory_pressure: str
    frame_time_ms: float
    frames_per_second: float
    overlapped_operations: int


class Metal4Diagnostics:
    """
    Metal 4 performance monitoring and diagnostics

    Features:
    - Real-time GPU utilization tracking
    - Command buffer/queue statistics
    - Memory pressure monitoring
    - Bottleneck detection
    - Performance recommendations
    """

    def __init__(self, engine):
        """
        Initialize diagnostics

        Args:
            engine: Metal4Engine instance
        """
        self.engine = engine
        self.device = engine.device

        # Performance tracking
        self.frame_times = []
        self.max_frame_history = 60  # Track last 60 frames

        # Queue statistics
        self.queue_stats = {
            'render': QueueStats('Q_render', 0, 0, 0.0, 0.0),
            'ml': QueueStats('Q_ml', 0, 0, 0.0, 0.0),
            'blit': QueueStats('Q_blit', 0, 0, 0.0, 0.0)
        }

        # Operation counters
        self.operation_counts = {
            'embeddings': 0,
            'transcriptions': 0,
            'sql_queries': 0,
            'render_frames': 0,
            'blit_transfers': 0
        }

        # Timing stats
        self.last_frame_time = time.time()
        self.start_time = time.time()

        logger.info("✅ Metal4Diagnostics initialized")

    def record_frame(self) -> None:
        """Record a new frame time"""
        now = time.time()
        frame_time_ms = (now - self.last_frame_time) * 1000

        self.frame_times.append(frame_time_ms)
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)

        self.last_frame_time = now
        self.operation_counts['render_frames'] += 1

    def record_operation(self, operation_type: str, duration_ms: float, queue: str = 'ml') -> None:
        """
        Record an operation completion

        Args:
            operation_type: Type of operation (e.g., 'embedding', 'transcription')
            duration_ms: Operation duration in milliseconds
            queue: Which queue handled it ('render', 'ml', 'blit')
        """
        # Update operation count
        if operation_type in self.operation_counts:
            self.operation_counts[operation_type] += 1

        # Update queue stats
        if queue in self.queue_stats:
            stats = self.queue_stats[queue]
            stats.buffers_submitted += 1
            stats.buffers_completed += 1
            stats.total_encode_time_ms += duration_ms
            stats.avg_encode_time_ms = stats.total_encode_time_ms / stats.buffers_completed

    def get_memory_pressure(self) -> str:
        """
        Calculate memory pressure level

        Returns:
            'low', 'medium', or 'high'
        """
        try:
            # Get heap usage
            if self.engine.H_main:
                used = self.engine.H_main.usedSize()
                total = self.engine.H_main.size()
                utilization = used / total

                if utilization > 0.8:
                    return 'high'
                elif utilization > 0.5:
                    return 'medium'
                else:
                    return 'low'
        except (AttributeError, ZeroDivisionError):
            pass  # Metal heap not available

        return 'unknown'

    def get_fps(self) -> float:
        """Calculate current FPS based on recent frame times"""
        if not self.frame_times:
            return 0.0

        avg_frame_time_ms = sum(self.frame_times) / len(self.frame_times)
        if avg_frame_time_ms > 0:
            return 1000.0 / avg_frame_time_ms
        return 0.0

    def get_avg_frame_time(self) -> float:
        """Get average frame time in milliseconds"""
        if not self.frame_times:
            return 0.0
        return sum(self.frame_times) / len(self.frame_times)

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics snapshot"""
        # Calculate memory usage
        memory_used_mb = 0.0
        memory_total_mb = 0.0

        if self.engine.H_main:
            memory_used_mb = self.engine.H_main.usedSize() / (1024**2)
            memory_total_mb = self.engine.H_main.size() / (1024**2)

        # Estimate GPU utilization based on queue activity
        # This is approximate - Metal doesn't expose direct GPU util
        gpu_util_pct = min(100.0, (
            self.queue_stats['render'].buffers_submitted * 10 +
            self.queue_stats['ml'].buffers_submitted * 30 +
            self.queue_stats['blit'].buffers_submitted * 5
        ) / max(1, time.time() - self.start_time))

        # Count concurrent operations (rough estimate)
        overlapped_ops = sum(1 for stats in self.queue_stats.values() if stats.buffers_submitted > stats.buffers_completed)

        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            gpu_util_pct=min(100.0, gpu_util_pct),
            memory_used_mb=memory_used_mb,
            memory_total_mb=memory_total_mb,
            memory_pressure=self.get_memory_pressure(),
            frame_time_ms=self.get_avg_frame_time(),
            frames_per_second=self.get_fps(),
            overlapped_operations=overlapped_ops
        )

    def get_realtime_stats(self) -> Dict[str, Any]:
        """
        Get real-time statistics for API endpoint

        Returns comprehensive stats dict matching METAL4_IMPLEMENTATION_PLAN
        """
        metrics = self.get_performance_metrics()

        # Calculate queue latency (best-effort estimate)
        # Average of all queue encode times weighted by active buffers
        total_latency = 0.0
        total_active = 0
        for stats in self.queue_stats.values():
            active = stats.buffers_submitted - stats.buffers_completed
            if active > 0 and stats.avg_encode_time_ms > 0:
                total_latency += stats.avg_encode_time_ms * active
                total_active += active

        queue_latency_ms = round(total_latency / total_active, 2) if total_active > 0 else None

        # Calculate oldest job age (time since first operation started)
        # This is a best-effort estimate based on uptime and completed jobs
        uptime_s = time.time() - self.start_time
        total_completed = sum(s.buffers_completed for s in self.queue_stats.values())
        oldest_job_age_ms = round((uptime_s * 1000) / max(1, total_completed), 2) if total_completed > 0 else None

        return {
            'timestamp': metrics.timestamp,

            # Queue utilization
            'queues': {
                'render': {
                    'active_buffers': self.queue_stats['render'].buffers_submitted - self.queue_stats['render'].buffers_completed,
                    'total_submitted': self.queue_stats['render'].buffers_submitted,
                    'total_completed': self.queue_stats['render'].buffers_completed,
                    'avg_encode_time_ms': round(self.queue_stats['render'].avg_encode_time_ms, 2)
                },
                'ml': {
                    'active_buffers': self.queue_stats['ml'].buffers_submitted - self.queue_stats['ml'].buffers_completed,
                    'total_submitted': self.queue_stats['ml'].buffers_submitted,
                    'total_completed': self.queue_stats['ml'].buffers_completed,
                    'avg_encode_time_ms': round(self.queue_stats['ml'].avg_encode_time_ms, 2)
                },
                'blit': {
                    'active_buffers': self.queue_stats['blit'].buffers_submitted - self.queue_stats['blit'].buffers_completed,
                    'total_submitted': self.queue_stats['blit'].buffers_submitted,
                    'total_completed': self.queue_stats['blit'].buffers_completed,
                    'avg_encode_time_ms': round(self.queue_stats['blit'].avg_encode_time_ms, 2)
                }
            },

            # Queue diagnostics (Sprint 3)
            'queue_latency_ms': queue_latency_ms,
            'oldest_job_age_ms': oldest_job_age_ms,

            # Event states
            'events': {
                'frame_counter': self.engine.frame_counter if hasattr(self.engine, 'frame_counter') else 0,
                'embed_counter': self.engine.embed_counter if hasattr(self.engine, 'embed_counter') else 0,
                'rag_counter': self.engine.rag_counter if hasattr(self.engine, 'rag_counter') else 0,
                'frame_signaled': self.engine.E_frame.signaledValue() if self.engine.E_frame else 0,
                'embed_signaled': self.engine.E_embed.signaledValue() if self.engine.E_embed else 0,
                'rag_signaled': self.engine.E_rag.signaledValue() if self.engine.E_rag else 0
            },

            # Memory
            'memory': {
                'heap_used_mb': round(metrics.memory_used_mb, 2),
                'heap_total_mb': round(metrics.memory_total_mb, 2),
                'heap_utilization_pct': round((metrics.memory_used_mb / metrics.memory_total_mb * 100) if metrics.memory_total_mb > 0 else 0, 2),
                'pressure': metrics.memory_pressure
            },

            # Performance
            'performance': {
                'frame_time_ms': round(metrics.frame_time_ms, 2),
                'fps': round(metrics.frames_per_second, 1),
                'gpu_util_pct': round(metrics.gpu_util_pct, 1),
                'overlapped_ops': metrics.overlapped_operations
            },

            # Operation counts
            'operations': self.operation_counts.copy()
        }

    def detect_bottlenecks(self) -> List[str]:
        """
        Detect performance bottlenecks

        Returns:
            List of detected issues/recommendations
        """
        issues = []
        metrics = self.get_performance_metrics()

        # Check memory pressure
        if metrics.memory_pressure == 'high':
            issues.append("HIGH memory pressure - consider reducing batch sizes or clearing caches")

        # Check frame time
        if metrics.frame_time_ms > 16.6:
            issues.append(f"Frame time {metrics.frame_time_ms:.1f}ms exceeds 60fps target (16.6ms)")

        # Check if ML queue is blocking
        ml_active = self.queue_stats['ml'].buffers_submitted - self.queue_stats['ml'].buffers_completed
        if ml_active > 5:
            issues.append(f"ML queue has {ml_active} pending operations - possible bottleneck")

        # Check if render queue is blocked
        if self.queue_stats['render'].avg_encode_time_ms > 10.0:
            issues.append(f"Render encoding time {self.queue_stats['render'].avg_encode_time_ms:.1f}ms is high")

        # Check parallelism
        if metrics.overlapped_operations < 2:
            issues.append("Low parallelism - ensure operations use different queues")

        if not issues:
            issues.append("✅ No bottlenecks detected - performance is optimal")

        return issues


# Global instance
_diagnostics: Optional[Metal4Diagnostics] = None


def get_diagnostics() -> Optional[Any]:
    """Get singleton diagnostics instance"""
    global _diagnostics

    if _diagnostics is None:
        from metal4_engine import get_metal4_engine
        engine = get_metal4_engine()

        if not engine.is_available():
            logger.warning("Metal4Engine not available - diagnostics disabled")
            return None

        _diagnostics = Metal4Diagnostics(engine)

    return _diagnostics


__all__ = [
    'Metal4Diagnostics',
    'PerformanceMetrics',
    'QueueStats',
    'get_diagnostics'
]
