"""
System Diagnostics Routes

Provides comprehensive system health monitoring for Mission Dashboard:
- System metrics (CPU, RAM, disk)
- Metal/GPU status (macOS)
- Ollama model information
- P2P network status
- Database health

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_middleware import get_current_user
from api.config_paths import get_config_paths
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)
PATHS = get_config_paths()


router = APIRouter(prefix="/api/v1", tags=["diagnostics"])


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
    """Get Metal/GPU status (macOS only)"""
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


def _ollama_overview() -> Dict[str, Any]:
    """Get Ollama status and model count"""
    try:
        import httpx

        # Quick health check
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            return {
                "available": True,
                "model_count": len(models),
                "models": [m["name"] for m in models[:5]],  # First 5 models
                "status": "running"
            }
        else:
            return {"available": False, "status": "unreachable", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"available": False, "status": "offline", "error": str(e)}


def _p2p_overview() -> Dict[str, Any]:
    """Get P2P network status"""
    try:
        # Check if P2P service is available
        # This is a placeholder - actual implementation would query the P2P service
        from api.p2p_mesh_service import get_p2p_status
        status = get_p2p_status()
        return {
            "status": status.get("status", "unknown"),
            "peers": status.get("peer_count", 0),
            "services": status.get("services", [])
        }
    except Exception as e:
        # Fallback if P2P service not available
        return {"status": "unavailable", "peers": 0, "error": str(e)}


def _database_overview() -> Dict[str, Any]:
    """Get database health metrics"""
    try:
        import sqlite3
        from api.config_paths import get_config_paths

        paths = get_config_paths()
        db_path = paths.data_dir / "elohimos.db"

        if not db_path.exists():
            return {"status": "not_initialized", "size_mb": 0}

        # Get database size
        size_bytes = db_path.stat().st_size
        size_mb = round(size_bytes / (1024**2), 2)

        # Quick connection test
        with sqlite3.connect(str(db_path), timeout=2.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

        return {
            "status": "healthy",
            "size_mb": size_mb,
            "table_count": table_count,
            "path": str(db_path)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get(
    "/diagnostics",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_system_diagnostics",
    summary="Get system diagnostics",
    description="Get comprehensive system health metrics (CPU, RAM, disk, Metal/GPU, Ollama, P2P, database)"
)
async def get_diagnostics(
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Return comprehensive system diagnostics for Mission Dashboard

    Returns system, Metal, Ollama, P2P, and database metrics.
    Falls back to partial diagnostics on error (non-critical).
    """
    try:
        data: Dict[str, Any] = {
            "system": _system_overview(),
            "metal": _metal_overview(),
            "ollama": _ollama_overview(),
            "p2p": _p2p_overview(),
            "database": _database_overview(),
            "timestamp": psutil.boot_time(),  # System uptime reference
        }

        logger.debug("Diagnostics collected successfully")
        return SuccessResponse(
            data=data,
            message="System diagnostics retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Diagnostics collection failed", exc_info=True)
        # Return partial diagnostics even on error (non-critical)
        partial_data = {
            "system": _system_overview(),
            "metal": {"available": False, "error": "Collection failed"},
            "ollama": {"available": False, "error": "Collection failed"},
            "p2p": {"status": "error", "peers": 0},
            "database": {"status": "error"},
            "partial": True
        }
        return SuccessResponse(
            data=partial_data,
            message="Partial diagnostics retrieved (some metrics unavailable)"
        )

