#!/usr/bin/env python3
"""
Monitoring Routes for ElohimOS API
Health checks, Metal 4 diagnostics, and system monitoring
"""

import logging
import os
import time
import psutil
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from .rate_limiter import rate_limiter, get_client_ip
except ImportError:
    from rate_limiter import rate_limiter, get_client_ip

try:
    from .auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


@router.get("/health")
async def get_system_health(request: Request):
    """
    Comprehensive system health check

    Returns status for all services and system resources
    """
    # Rate limit: 60 health checks per minute
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"monitoring:health:{client_ip}", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 requests per minute.")

    start_time = time.time()

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "system": {}
    }

    # Check API (always healthy if we're responding)
    health_status["services"]["api"] = {
        "status": "healthy",
        "message": "API responding",
        "latency_ms": round((time.time() - start_time) * 1000, 2)
    }

    # Check database
    try:
        from data_engine import get_data_engine
        engine = get_data_engine()

        db_start = time.time()
        # Simple query to test database
        engine.conn.execute("SELECT 1").fetchone()
        db_latency = (time.time() - db_start) * 1000

        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Database responding",
            "latency_ms": round(db_latency, 2)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = {
            "status": "down",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    # Check Ollama
    try:
        from chat_service import ollama_client

        ollama_start = time.time()
        models = await ollama_client.list_models()
        ollama_latency = (time.time() - ollama_start) * 1000

        health_status["services"]["ollama"] = {
            "status": "healthy",
            "message": f"{len(models)} models available",
            "latency_ms": round(ollama_latency, 2),
            "details": {
                "model_count": len(models)
            }
        }
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        health_status["services"]["ollama"] = {
            "status": "down",
            "message": "Ollama not available"
        }

    # Check embeddings
    try:
        try:
            from unified_embedder import get_unified_embedder
            embedder = get_unified_embedder()
        except (ImportError, AttributeError):
            embedder = None

        if embedder and embedder.is_available():
            health_status["services"]["embeddings"] = {
                "status": "healthy",
                "message": f"Using {embedder.backend}",
                "details": {
                    "backend": embedder.backend,
                    "model": embedder.model_name
                }
            }
        else:
            health_status["services"]["embeddings"] = {
                "status": "down",
                "message": "Embeddings unavailable"
            }
    except Exception as e:
        logger.warning(f"Embeddings health check failed: {e}")
        health_status["services"]["embeddings"] = {
            "status": "down",
            "message": str(e)
        }

    # Check P2P
    try:
        try:
            from offline_data_sync import get_sync_service
            sync_service = get_sync_service()
        except (ImportError, AttributeError):
            sync_service = None

        if sync_service:
            peer_count = len(sync_service.discovered_peers)
            health_status["services"]["p2p"] = {
                "status": "healthy",
                "message": f"{peer_count} peers discovered",
                "details": {
                    "peer_count": peer_count,
                    "device_id": sync_service.device_id
                }
            }
        else:
            health_status["services"]["p2p"] = {
                "status": "degraded",
                "message": "P2P not initialized"
            }
    except Exception as e:
        logger.warning(f"P2P health check failed: {e}")
        health_status["services"]["p2p"] = {
            "status": "down",
            "message": str(e)
        }

    # Check vault
    try:
        from vault_service import get_vault_service
        vault = get_vault_service()

        if vault:
            is_unlocked = vault.is_unlocked
            health_status["services"]["vault"] = {
                "status": "healthy" if is_unlocked else "degraded",
                "message": "Unlocked" if is_unlocked else "Locked",
                "details": {
                    "unlocked": is_unlocked,
                    "encryption": "AES-256-GCM"
                }
            }
        else:
            health_status["services"]["vault"] = {
                "status": "down",
                "message": "Vault not initialized"
            }
    except Exception as e:
        logger.warning(f"Vault health check failed: {e}")
        health_status["services"]["vault"] = {
            "status": "down",
            "message": str(e)
        }

    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        health_status["system"] = {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_used_mb": round(memory.used / (1024**2), 2),
            "memory_total_mb": round(memory.total / (1024**2), 2)
        }

        # Check if system is under heavy load
        if cpu_percent > 90 or memory.percent > 90:
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"System metrics failed: {e}")
        health_status["system"] = {
            "cpu_percent": 0,
            "memory_percent": 0
        }

    return health_status


@router.get("/metal4")
async def get_metal4_stats(request: Request):
    """
    Get Metal 4 GPU performance statistics

    Returns real-time metrics from Metal 4 diagnostics
    """
    # Rate limit: Disabled for lightweight stats endpoint (dev only, local access)
    # Original: 60/min (prod), 300/min (dev) - caused issues with frontend polling
    # This endpoint is read-only, low-cost, and only accessible locally
    # from rate_limiter import is_dev_mode
    # client_ip = get_client_ip(request)
    # max_per_min = 300 if is_dev_mode(request) else 60
    # if not rate_limiter.check_rate_limit(
    #     f"monitoring:metal4:{client_ip}", max_requests=max_per_min, window_seconds=60
    # ):
    #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Max {max_per_min} requests per minute.")

    try:
        from metal4_diagnostics import get_diagnostics

        diagnostics = get_diagnostics()

        if not diagnostics:
            raise HTTPException(
                status_code=503,
                detail="Metal 4 diagnostics not available - GPU may not be initialized"
            )

        stats = diagnostics.get_realtime_stats()

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metal4 stats failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Metal 4 stats: {str(e)}"
        )


@router.get("/metal4/bottlenecks")
async def detect_bottlenecks():
    """
    Detect performance bottlenecks in Metal 4 pipeline

    Returns list of detected issues and recommendations
    """
    try:
        from metal4_diagnostics import get_diagnostics

        diagnostics = get_diagnostics()

        if not diagnostics:
            raise HTTPException(
                status_code=503,
                detail="Metal 4 diagnostics not available"
            )

        issues = diagnostics.detect_bottlenecks()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "issues": issues,
            "has_bottlenecks": any("✅" not in issue for issue in issues)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bottleneck detection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect bottlenecks: {str(e)}"
        )


@router.get("/services/status")
async def get_services_status():
    """
    Quick status check for all services

    Returns simple up/down status for each service
    """
    status = {}

    # Check all services
    services_to_check = [
        ("database", lambda: __import__('data_engine').get_data_engine()),
        ("ollama", lambda: __import__('chat_service').ollama_client),
        ("embeddings", lambda: __import__('unified_embedder').get_unified_embedder()),
        ("p2p", lambda: __import__('offline_data_sync').get_sync_service()),
        ("vault", lambda: __import__('vault_service').get_vault_service()),
    ]

    for service_name, check_fn in services_to_check:
        try:
            service = check_fn()
            status[service_name] = "up" if service else "down"
        except Exception:
            status[service_name] = "down"

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status
    }


@router.get("/system/resources")
async def get_system_resources():
    """
    Get system resource utilization

    Returns CPU, memory, and disk usage
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "cpu": {
                "percent": round(cpu_percent, 2),
                "count": psutil.cpu_count()
            },
            "memory": {
                "percent": round(memory.percent, 2),
                "used_mb": round(memory.used / (1024**2), 2),
                "total_mb": round(memory.total / (1024**2), 2),
                "available_mb": round(memory.available / (1024**2), 2)
            },
            "disk": {
                "percent": round(disk.percent, 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2)
            }
        }
    except Exception as e:
        logger.error(f"System resources failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system resources: {str(e)}"
        )
