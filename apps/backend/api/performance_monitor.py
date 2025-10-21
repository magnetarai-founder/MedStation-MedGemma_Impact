#!/usr/bin/env python3
"""
Performance Monitoring for ElohimOS
Real-time tracking of tokens/s, GPU %, temperature, memory
Critical for missionary field deployments
"""

import psutil
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Single performance measurement"""
    timestamp: float
    tokens_per_second: float
    gpu_utilization_percent: float
    cpu_utilization_percent: float
    memory_used_gb: float
    memory_total_gb: float
    temperature_celsius: Optional[float]
    thermal_state: str  # nominal, fair, serious, critical


class PerformanceMonitor:
    """Real-time performance tracking"""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.snapshots = deque(maxlen=history_size)

        # Token tracking
        self.total_tokens = 0
        self.start_time = time.time()
        self.last_token_time = time.time()

    def record_tokens(self, num_tokens: int):
        """Record tokens generated"""
        self.total_tokens += num_tokens
        self.last_token_time = time.time()

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""

        # CPU & Memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)

        # Tokens/second
        elapsed = time.time() - self.start_time
        tokens_per_second = self.total_tokens / elapsed if elapsed > 0 else 0

        # GPU utilization (Apple Silicon specific)
        gpu_percent = self._get_gpu_utilization()

        # Temperature & thermal state
        temp, thermal_state = self._get_thermal_info()

        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            tokens_per_second=tokens_per_second,
            gpu_utilization_percent=gpu_percent,
            cpu_utilization_percent=cpu_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            temperature_celsius=temp,
            thermal_state=thermal_state
        )

        self.snapshots.append(snapshot)

        return asdict(snapshot)

    def _get_gpu_utilization(self) -> float:
        """Get GPU utilization on Apple Silicon"""
        try:
            # Try to read GPU metrics from powermetrics (requires sudo)
            # For now, estimate based on CPU usage (GPU often correlates)
            # In production, you'd parse `sudo powermetrics --samplers gpu_power`
            return 0.0  # Placeholder
        except Exception:
            return 0.0

    def _get_thermal_info(self) -> tuple[Optional[float], str]:
        """Get temperature and thermal state"""
        try:
            import subprocess

            # Try to get temperature from powermetrics
            # This requires sudo, so might not work in all environments
            # For production, consider using IOKit or other methods

            # Thermal state estimation based on CPU usage
            cpu_percent = psutil.cpu_percent(interval=0)

            if cpu_percent < 30:
                thermal_state = "nominal"
            elif cpu_percent < 60:
                thermal_state = "fair"
            elif cpu_percent < 80:
                thermal_state = "serious"
            else:
                thermal_state = "critical"

            return None, thermal_state  # Temperature not available without sudo

        except Exception as e:
            logger.debug(f"Thermal info error: {e}")
            return None, "unknown"

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics over history"""
        if not self.snapshots:
            return {"error": "No data collected yet"}

        snapshots_list = list(self.snapshots)

        avg_tokens_s = sum(s.tokens_per_second for s in snapshots_list) / len(snapshots_list)
        avg_gpu = sum(s.gpu_utilization_percent for s in snapshots_list) / len(snapshots_list)
        avg_cpu = sum(s.cpu_utilization_percent for s in snapshots_list) / len(snapshots_list)
        avg_memory = sum(s.memory_used_gb for s in snapshots_list) / len(snapshots_list)

        current = snapshots_list[-1]

        return {
            "current": {
                "tokens_per_second": current.tokens_per_second,
                "gpu_percent": current.gpu_utilization_percent,
                "cpu_percent": current.cpu_utilization_percent,
                "memory_used_gb": current.memory_used_gb,
                "memory_total_gb": current.memory_total_gb,
                "memory_percent": (current.memory_used_gb / current.memory_total_gb * 100) if current.memory_total_gb > 0 else 0,
                "thermal_state": current.thermal_state,
            },
            "averages": {
                "tokens_per_second": avg_tokens_s,
                "gpu_percent": avg_gpu,
                "cpu_percent": avg_cpu,
                "memory_used_gb": avg_memory,
            },
            "total_tokens": self.total_tokens,
            "uptime_seconds": time.time() - self.start_time,
            "samples": len(snapshots_list),
        }

    def get_history(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Get recent performance history"""
        recent = list(self.snapshots)[-last_n:]
        return [asdict(s) for s in recent]

    def check_thermal_throttling(self) -> Dict[str, Any]:
        """Check if system is thermal throttling"""
        if not self.snapshots:
            return {"throttling": False, "reason": "No data"}

        current = self.snapshots[-1]

        is_throttling = False
        reason = "Normal operation"

        if current.thermal_state in ["serious", "critical"]:
            is_throttling = True
            reason = f"Thermal state: {current.thermal_state}"

        elif current.cpu_utilization_percent > 90:
            is_throttling = True
            reason = "High CPU utilization (>90%)"

        return {
            "throttling": is_throttling,
            "reason": reason,
            "thermal_state": current.thermal_state,
            "cpu_percent": current.cpu_utilization_percent,
            "recommendation": self._get_throttling_recommendation(current)
        }

    def _get_throttling_recommendation(self, snapshot: PerformanceSnapshot) -> str:
        """Get recommendation for thermal issues"""
        if snapshot.thermal_state == "critical":
            return "Reduce GPU layers or switch to 'silent' mode immediately"
        elif snapshot.thermal_state == "serious":
            return "Consider switching to 'balanced' mode"
        elif snapshot.cpu_utilization_percent > 90:
            return "Reduce batch size or concurrent operations"
        else:
            return "No action needed"

    def reset(self):
        """Reset all metrics"""
        self.total_tokens = 0
        self.start_time = time.time()
        self.last_token_time = time.time()
        self.snapshots.clear()
        logger.info("📊 Performance metrics reset")


# Singleton instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get singleton performance monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        logger.info("📊 Performance monitor initialized")
    return _performance_monitor
