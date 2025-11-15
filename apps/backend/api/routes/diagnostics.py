"""
Mission Diagnostics Endpoint (skeleton).

GET /api/v1/diagnostics - returns system, GPU/Metal, and P2P summary metrics.
"""

from __future__ import annotations

import platform
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends

from api.auth_middleware import get_current_user


router = APIRouter(prefix="/api/v1", tags=["diagnostics"], dependencies=[Depends(get_current_user)])


def _system_overview() -> Dict[str, Any]:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=0.1)
    return {
        "os": platform.platform(),
        "cpu_percent": cpu,
        "ram": {"total_gb": round(vm.total / (1024**3), 2), "used_gb": round(vm.used / (1024**3), 2)},
        "disk": {"total_gb": round(disk.total / (1024**3), 2), "used_gb": round(disk.used / (1024**3), 2)},
    }


def _metal_overview() -> Dict[str, Any]:
    try:
        from metal4_engine import get_metal4_engine

        engine = get_metal4_engine()
        if engine and engine.is_available():
            rec = engine.device.recommendedMaxWorkingSetSize() if engine.device else 0
            return {
                "available": True,
                "initialized": getattr(engine, "_initialized", False),
                "device": engine.device.name() if engine.device else None,
                "recommended_working_set_gb": round(rec / (1024**3), 1) if rec else 0,
                "error": getattr(engine, "initialization_error", None),
            }
        return {"available": False, "initialized": False, "error": getattr(engine, "initialization_error", None)}
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.get("/diagnostics")
async def get_diagnostics():
    """Return system, GPU/Metal, and placeholder P2P summary."""
    data: Dict[str, Any] = {
        "system": _system_overview(),
        "metal": _metal_overview(),
        # P2P summary can be filled by querying p2p service if desired
        "p2p": {"peers": None, "status": "n/a"},
    }
    return data

