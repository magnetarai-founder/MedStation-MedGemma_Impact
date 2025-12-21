"""
System information and diagnostic API endpoints.

Provides system information, health checks, diagnostics, and fallback endpoints.
"""

import logging
import subprocess
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth_middleware import get_current_user

router = APIRouter(tags=["System"])
logger = logging.getLogger(__name__)


@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ElohimOS API", "version": "1.0.0"}


@router.get("/api/system/info")
async def get_system_info(current_user: dict = Depends(get_current_user)):
    """
    Get system information including Metal GPU capabilities and memory.

    Requires authentication to prevent fingerprinting attacks.
    """
    info = {
        "total_memory_gb": 0,
        "metal_available_memory_gb": 0,
        "metal_device_name": None,
        "metal_available": False,
        "metal_initialized": False,
        "metal_error": None,  # NEW: Expose initialization errors to frontend
    }

    # Get total system memory using sysctl
    try:
        result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
        if result.returncode == 0:
            memsize = int(result.stdout.split(':')[1].strip())
            info["total_memory_gb"] = round(memsize / (1024**3), 1)
    except (subprocess.SubprocessError, ValueError, IndexError):
        pass  # System info not available

    # Get Metal device info and recommendedMaxWorkingSetSize
    try:
        from metal4_engine import get_metal4_engine
        engine = get_metal4_engine()

        if engine.is_available():
            info["metal_available"] = True
            info["metal_initialized"] = engine._initialized
            info["metal_device_name"] = engine.device.name() if engine.device else None

            # Expose initialization error if any
            if engine.initialization_error:
                info["metal_error"] = engine.initialization_error

            # This is the key value - Metal's recommended max working set size
            # This is what should be used for calculating model loading capacity
            if engine.device:
                recommended_max = engine.device.recommendedMaxWorkingSetSize()
                info["metal_available_memory_gb"] = round(recommended_max / (1024**3), 1)
        else:
            # Metal not available at all
            if hasattr(engine, 'initialization_error') and engine.initialization_error:
                info["metal_error"] = engine.initialization_error
    except Exception as e:
        info["metal_error"] = f"Failed to query Metal engine: {str(e)}"

    return info


@router.get("/metrics")
async def prometheus_metrics(current_user: dict = Depends(get_current_user)):
    """
    Prometheus metrics endpoint (Phase 5.2)

    Returns metrics in Prometheus text format for scraping.
    Requires authentication to protect operational data.

    Includes:
    - System metrics (CPU, RAM, disk, network)
    - Metal 4 GPU metrics (if available)
    - Application metrics (users, workflows, vault)
    - Health status

    Response format: text/plain (Prometheus format)
    """
    try:
        from prometheus_metrics import get_prometheus_exporter
        prometheus_exporter = get_prometheus_exporter()
    except ImportError:
        raise HTTPException(status_code=503, detail="Prometheus metrics not available")

    if not prometheus_exporter:
        raise HTTPException(status_code=503, detail="Prometheus metrics not available")

    try:
        metrics_text = prometheus_exporter.collect_metrics()
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to collect Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Quick health check endpoint (Phase 5.4)

    Lightweight health check for liveness probes.
    Target: < 100ms response time.

    Checks:
    - Database connectivity
    - System resources (memory, disk)

    Returns:
        JSON with health status
    """
    try:
        from health_diagnostics import get_health_diagnostics
        health_diagnostics = get_health_diagnostics()
    except ImportError:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    if not health_diagnostics:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    try:
        health = health_diagnostics.check_health()
        status_code = 200 if health["status"] == "healthy" else 503
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/diagnostics")
async def system_diagnostics(force_refresh: bool = False):
    """
    Comprehensive system diagnostics endpoint (Phase 5.4)

    Detailed diagnostics for troubleshooting and monitoring.
    Results cached for 60 seconds to avoid overhead.

    Includes:
    - All component health status
    - System information
    - Metal 4 GPU details
    - Dependency validation
    - Performance metrics

    Query params:
        force_refresh: Force fresh diagnostics (bypass cache)

    Returns:
        JSON with comprehensive diagnostics
    """
    try:
        from health_diagnostics import get_health_diagnostics
        health_diagnostics = get_health_diagnostics()
    except ImportError:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    if not health_diagnostics:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    try:
        diagnostics = health_diagnostics.get_diagnostics(force_refresh=force_refresh)
        return diagnostics
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


# ============================================================================
# FALLBACK ENDPOINTS
# ============================================================================


@router.get("/api/v1/admin/device/overview")
async def _fallback_admin_device_overview(request: Request, current_user: dict = Depends(get_current_user)):
    """Fallback Admin device overview endpoint to avoid 404 if admin router fails to load"""
    # Require Founder Rights (Founder Admin)
    if current_user.get("role") != "founder_rights":
        raise HTTPException(status_code=403, detail="Founder Rights (Founder Admin) access required")

    # Try to forward to admin_service implementation if available
    try:
        try:
            from api.admin_service import get_device_overview as _real_overview  # type: ignore
        except ImportError:
            from admin_service import get_device_overview as _real_overview  # type: ignore
        return await _real_overview(request, current_user)
    except Exception:
        # Graceful minimal overview if admin_service is unavailable
        return {
            "device_overview": {
                "total_users": None,
                "active_users_7d": None,
                "users_by_role": None,
                "total_chat_sessions": None,
                "total_workflows": None,
                "total_work_items": None,
                "total_documents": None,
                "data_dir_size_bytes": None,
                "data_dir_size_human": None,
            },
            "timestamp": datetime.now(UTC).isoformat()
        }


@router.post("/api/v1/terminal/spawn-system")
async def _fallback_spawn_system_terminal(current_user: dict = Depends(get_current_user)):
    """Fallback Terminal spawn endpoint to avoid 404 if terminal router fails to load"""
    # Allow only founder_rights or super_admin by default
    role = current_user.get("role")
    if role not in ("founder_rights", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to spawn terminal")

    # Try to forward to terminal_api implementation if available
    try:
        try:
            from api.terminal_api import spawn_system_terminal as _real_spawn  # type: ignore
        except ImportError:
            from terminal_api import spawn_system_terminal as _real_spawn  # type: ignore
        return await _real_spawn(current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to spawn system terminal: {e}. Ensure Terminal/iTerm/Warp are installed and grant Automation/Accessibility permissions."
            )
        )
