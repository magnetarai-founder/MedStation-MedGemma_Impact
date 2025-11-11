#!/usr/bin/env python3
"""
Comprehensive Health Check and Diagnostics

"He gives strength to the weary" - Isaiah 40:29

Implements Phase 5.4 of Security Hardening Roadmap:
- System health monitoring
- Component availability checks
- Database connectivity validation
- GPU acceleration status
- Performance diagnostics
- Dependency validation

Features:
- Quick health check (/health) - < 100ms response time
- Detailed diagnostics (/diagnostics) - comprehensive system status
- Component-level health status
- Ready for monitoring systems (Kubernetes, Docker, etc.)

Architecture:
- Lightweight health checks for liveness probes
- Detailed diagnostics for troubleshooting
- JSON responses with structured data
- Graceful degradation when components unavailable
"""

import logging
import time
import platform
import sys
import sqlite3
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthDiagnostics:
    """
    Comprehensive health check and diagnostics system

    Provides two levels of health monitoring:
    1. Quick health check - minimal latency for liveness probes
    2. Detailed diagnostics - comprehensive system analysis

    Components checked:
    - Database connectivity
    - Metal 4 GPU availability
    - System resources (CPU, RAM, disk)
    - Python environment
    - Critical dependencies
    """

    def __init__(self):
        """Initialize health diagnostics"""
        self.start_time = time.time()
        self._initialized = False
        self._cached_diagnostics = None
        self._cache_timestamp = 0
        self._cache_ttl = 60  # Cache diagnostics for 60 seconds

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize diagnostics system"""
        logger.info("Initializing health diagnostics...")
        self._initialized = True
        logger.info("✅ Health diagnostics initialized")

    # ========================================================================
    # Quick Health Check (Liveness Probe)
    # ========================================================================

    def check_health(self) -> Dict[str, Any]:
        """
        Quick health check for liveness probes

        Checks only critical components:
        - Database connectivity
        - Basic system resources

        Target: < 100ms response time

        Returns:
            Dict with health status
        """
        start_time = time.time()

        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "checks": {}
        }

        # Check database
        db_healthy = self._check_database()
        health["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "available": db_healthy
        }

        # Check system resources
        mem = psutil.virtual_memory()
        health["checks"]["memory"] = {
            "status": "healthy" if mem.percent < 90 else "degraded",
            "usage_percent": mem.percent
        }

        disk = psutil.disk_usage('/')
        health["checks"]["disk"] = {
            "status": "healthy" if disk.percent < 90 else "degraded",
            "usage_percent": disk.percent
        }

        # Overall status
        if not db_healthy:
            health["status"] = "unhealthy"
        elif mem.percent >= 90 or disk.percent >= 90:
            health["status"] = "degraded"

        # Response time
        elapsed_ms = (time.time() - start_time) * 1000
        health["response_time_ms"] = round(elapsed_ms, 2)

        return health

    # ========================================================================
    # Detailed Diagnostics
    # ========================================================================

    def get_diagnostics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Comprehensive system diagnostics

        Checks all components and provides detailed status.
        Results are cached for 60 seconds to avoid overhead.

        Args:
            force_refresh: Force fresh diagnostics (bypass cache)

        Returns:
            Dict with comprehensive diagnostics
        """
        # Check cache
        now = time.time()
        if not force_refresh and self._cached_diagnostics:
            age = now - self._cache_timestamp
            if age < self._cache_ttl:
                # Return cached diagnostics
                cached = self._cached_diagnostics.copy()
                cached["cached"] = True
                cached["cache_age_seconds"] = int(age)
                return cached

        # Generate fresh diagnostics
        start_time = time.time()

        diagnostics = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "cached": False,
            "components": {},
            "system": {},
            "metal4": {},
            "dependencies": {},
            "performance": {}
        }

        # Component health checks
        diagnostics["components"]["database"] = self._diagnose_database()
        diagnostics["components"]["metal4_engine"] = self._diagnose_metal4()
        diagnostics["components"]["metal4_sql"] = self._diagnose_metal4_sql()
        diagnostics["components"]["tensor_ops"] = self._diagnose_tensor_ops()
        diagnostics["components"]["metalfx_renderer"] = self._diagnose_metalfx()

        # System diagnostics
        diagnostics["system"] = self._diagnose_system()

        # Metal 4 detailed status
        diagnostics["metal4"] = self._diagnose_metal4_detailed()

        # Dependencies
        diagnostics["dependencies"] = self._diagnose_dependencies()

        # Performance metrics
        diagnostics["performance"] = self._diagnose_performance()

        # Overall status
        unhealthy_components = [
            name for name, comp in diagnostics["components"].items()
            if comp["status"] == "unhealthy"
        ]

        if unhealthy_components:
            diagnostics["status"] = "unhealthy"
            diagnostics["unhealthy_components"] = unhealthy_components
        else:
            degraded_components = [
                name for name, comp in diagnostics["components"].items()
                if comp["status"] == "degraded"
            ]
            if degraded_components:
                diagnostics["status"] = "degraded"
                diagnostics["degraded_components"] = degraded_components

        # Response time
        elapsed_ms = (time.time() - start_time) * 1000
        diagnostics["response_time_ms"] = round(elapsed_ms, 2)

        # Cache diagnostics
        self._cached_diagnostics = diagnostics.copy()
        self._cache_timestamp = now

        return diagnostics

    # ========================================================================
    # Component Checks
    # ========================================================================

    def _check_database(self) -> bool:
        """Quick database connectivity check"""
        try:
            from auth_middleware import auth_service
            conn = sqlite3.connect(str(auth_service.db_path), timeout=5.0)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def _diagnose_database(self) -> Dict[str, Any]:
        """Detailed database diagnostics"""
        try:
            from auth_middleware import auth_service

            conn = sqlite3.connect(str(auth_service.db_path), timeout=5.0)

            # Check database file size
            db_size = Path(auth_service.db_path).stat().st_size

            # Count tables
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cur.fetchone()[0]

            # Check WAL mode
            cur.execute("PRAGMA journal_mode")
            journal_mode = cur.fetchone()[0]

            conn.close()

            return {
                "status": "healthy",
                "available": True,
                "db_path": str(auth_service.db_path),
                "db_size_mb": round(db_size / (1024 * 1024), 2),
                "table_count": table_count,
                "journal_mode": journal_mode
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "available": False,
                "error": str(e)
            }

    def _diagnose_metal4(self) -> Dict[str, Any]:
        """Diagnose Metal 4 engine"""
        try:
            from metal4_engine import get_metal4_engine

            engine = get_metal4_engine()

            if not engine.is_available():
                return {
                    "status": "unavailable",
                    "available": False,
                    "message": "Metal 4 not available on this system"
                }

            return {
                "status": "healthy",
                "available": True,
                "initialized": engine._initialized
            }

        except Exception as e:
            return {
                "status": "unavailable",
                "available": False,
                "error": str(e)
            }

    def _diagnose_metal4_sql(self) -> Dict[str, Any]:
        """Diagnose Metal 4 SQL engine"""
        try:
            from metal4_sql_engine import get_metal4_sql_engine

            sql_engine = get_metal4_sql_engine()

            if not sql_engine.is_available():
                return {
                    "status": "unavailable",
                    "available": False
                }

            stats = sql_engine.get_stats()

            return {
                "status": "healthy",
                "available": True,
                "operations_total": stats.get("total_operations", 0),
                "gpu_operations": stats.get("gpu_operations", 0)
            }

        except Exception as e:
            return {
                "status": "unavailable",
                "available": False,
                "error": str(e)
            }

    def _diagnose_tensor_ops(self) -> Dict[str, Any]:
        """Diagnose tensor operations"""
        try:
            from metal4_tensor_ops import get_tensor_ops

            tensor_ops = get_tensor_ops()

            if not tensor_ops.is_available():
                return {
                    "status": "unavailable",
                    "available": False
                }

            stats = tensor_ops.get_stats()

            return {
                "status": "healthy",
                "available": True,
                "metal_enabled": stats.get("metal_enabled", False),
                "operations_total": stats.get("operations_executed", 0)
            }

        except Exception as e:
            return {
                "status": "unavailable",
                "available": False,
                "error": str(e)
            }

    def _diagnose_metalfx(self) -> Dict[str, Any]:
        """Diagnose MetalFX renderer"""
        try:
            from metal4_metalfx_renderer import get_metalfx_renderer

            renderer = get_metalfx_renderer()

            if not renderer.is_available():
                return {
                    "status": "unavailable",
                    "available": False
                }

            stats = renderer.get_stats()

            return {
                "status": "healthy",
                "available": True,
                "metalfx_available": stats.get("metalfx_available", False),
                "current_fps": stats.get("current_fps", 0)
            }

        except Exception as e:
            return {
                "status": "unavailable",
                "available": False,
                "error": str(e)
            }

    def _diagnose_system(self) -> Dict[str, Any]:
        """System diagnostics"""
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version.split()[0],
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": disk.percent
        }

    def _diagnose_metal4_detailed(self) -> Dict[str, Any]:
        """Detailed Metal 4 diagnostics"""
        try:
            from metal4_engine import get_metal4_engine

            engine = get_metal4_engine()

            if not engine.is_available():
                return {"available": False}

            capabilities = engine.capabilities

            return {
                "available": True,
                "version": capabilities.version.value,
                "device_name": engine.device.name() if engine.device else None,
                "supports_unified_memory": capabilities.supports_unified_memory,
                "recommended_heap_size_mb": capabilities.recommended_heap_size_mb,
                "max_threads_per_threadgroup": capabilities.max_threads_per_threadgroup
            }

        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

    def _diagnose_dependencies(self) -> Dict[str, Any]:
        """Check critical dependencies"""
        dependencies = {
            "fastapi": self._check_module("fastapi"),
            "pydantic": self._check_module("pydantic"),
            "psutil": self._check_module("psutil"),
            "pandas": self._check_module("pandas"),
            "numpy": self._check_module("numpy")
        }

        # Optional Metal dependencies
        dependencies["metal_optional"] = {
            "Metal": self._check_module("Metal"),
            "MetalPerformanceShaders": self._check_module("MetalPerformanceShaders")
        }

        return dependencies

    def _check_module(self, module_name: str) -> Dict[str, Any]:
        """Check if module is available"""
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "unknown")
            return {"available": True, "version": version}
        except ImportError:
            return {"available": False}

    def _diagnose_performance(self) -> Dict[str, Any]:
        """Performance diagnostics"""
        return {
            "uptime_seconds": int(time.time() - self.start_time),
            "uptime_hours": round((time.time() - self.start_time) / 3600, 2)
        }


# ===== Singleton Instance =====

_health_diagnostics: Optional[HealthDiagnostics] = None


def get_health_diagnostics() -> HealthDiagnostics:
    """Get singleton health diagnostics instance"""
    global _health_diagnostics
    if _health_diagnostics is None:
        _health_diagnostics = HealthDiagnostics()
    return _health_diagnostics


# Export
__all__ = [
    'HealthDiagnostics',
    'get_health_diagnostics'
]
