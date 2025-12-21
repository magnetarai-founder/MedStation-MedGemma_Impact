"""
Chat service - Performance monitoring and panic mode operations.

Handles:
- Performance metrics collection
- Performance statistics
- Performance history
- Thermal throttling detection
- Panic mode triggers and status
"""

import logging
from typing import Dict, Any

from .lazy_init import _get_performance_monitor, _get_panic_mode

logger = logging.getLogger(__name__)


def get_current_performance() -> Dict[str, Any]:
    """Get current performance metrics"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.get_current_metrics()


def get_performance_statistics() -> Dict[str, Any]:
    """Get performance statistics over time"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.get_statistics()


def get_performance_history(last_n: int = 20) -> Dict[str, Any]:
    """Get recent performance history"""
    performance_monitor = _get_performance_monitor()
    history = performance_monitor.get_history(last_n)
    return {"history": history}


def check_thermal_throttling() -> Dict[str, Any]:
    """Check for thermal throttling"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.check_thermal_throttling()


def reset_performance_metrics() -> Dict[str, Any]:
    """Reset performance metrics"""
    performance_monitor = _get_performance_monitor()
    performance_monitor.reset()
    return {"status": "success", "message": "Performance metrics reset"}


async def trigger_panic_mode(reason: str = "Manual activation") -> Dict[str, Any]:
    """Trigger panic mode - EMERGENCY"""
    panic_mode = _get_panic_mode()
    result = await panic_mode.trigger_panic(reason)
    return result


def get_panic_status() -> Dict[str, Any]:
    """Get current panic mode status"""
    panic_mode = _get_panic_mode()
    return panic_mode.get_panic_status()


def reset_panic_mode() -> Dict[str, Any]:
    """Reset panic mode"""
    panic_mode = _get_panic_mode()
    panic_mode.reset_panic()
    return {"status": "success", "message": "Panic mode reset"}
