"""
Chat service - Health and system status operations.

Handles:
- Health checks
- System memory stats
- Ollama server status
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def check_health() -> Dict[str, Any]:
    """Check Ollama health status"""
    from .. import system as system_mod
    return await system_mod.check_health()


async def get_system_memory() -> Dict[str, Any]:
    """Get actual system memory stats for Mac"""
    try:
        import psutil

        virtual_mem = psutil.virtual_memory()

        total_gb = virtual_mem.total / (1024 ** 3)
        available_gb = virtual_mem.available / (1024 ** 3)
        used_gb = virtual_mem.used / (1024 ** 3)

        usable_percentage = 0.8
        usable_for_models_gb = total_gb * usable_percentage

        return {
            "total_gb": round(total_gb, 2),
            "available_gb": round(available_gb, 2),
            "used_gb": round(used_gb, 2),
            "percent_used": virtual_mem.percent,
            "usable_for_models_gb": round(usable_for_models_gb, 2),
            "usable_percentage": usable_percentage
        }

    except ImportError:
        raise Exception("psutil library not available for memory detection")
    except Exception as e:
        logger.error(f"Failed to get system memory: {e}")
        raise
