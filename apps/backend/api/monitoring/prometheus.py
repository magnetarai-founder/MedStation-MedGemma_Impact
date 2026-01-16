#!/usr/bin/env python3
"""
Prometheus Metrics Exporter

"The Lord is my strength and my song" - Exodus 15:2

Implements Phase 5.2 of Security Hardening Roadmap:
- GPU acceleration metrics (Metal 4)
- System performance metrics
- Application health metrics
- API endpoint for /metrics

Exports metrics in Prometheus format for monitoring and alerting.

Architecture:
- Custom metrics collectors for Metal 4 GPU
- System resource monitoring
- Application-specific metrics
- Standard Prometheus text format
- Auto-refresh on each scrape

Performance Target: < 100ms metric collection time
"""

import logging
import time
import psutil
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from pathlib import Path

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter:
    """
    Prometheus metrics exporter for ElohimOS

    Exports metrics in Prometheus text format:
    - Metal 4 GPU metrics (utilization, memory, temperature)
    - System metrics (CPU, RAM, disk, network)
    - Application metrics (requests, users, workflows)
    - Health status

    Metrics are collected on-demand during each scrape.
    """

    def __init__(self):
        """Initialize Prometheus metrics exporter"""
        self.start_time = time.time()
        self._initialized = False

        # Metal 4 components (optional)
        self.metal4_engine = None
        self.metal4_sql_engine = None
        self.tensor_ops = None
        self.metalfx_renderer = None

        # Initialize
        self._initialize()

    def _initialize(self) -> None:
        """Initialize metrics exporter"""
        logger.info("Initializing Prometheus metrics exporter...")

        # Try to load Metal 4 components
        try:
            from metal4_engine import get_metal4_engine
            self.metal4_engine = get_metal4_engine()
            logger.info("✅ Metal 4 engine loaded for metrics")
        except Exception as e:
            logger.warning(f"Metal 4 engine not available for metrics: {e}")

        try:
            from metal4_sql_engine import get_metal4_sql_engine
            self.metal4_sql_engine = get_metal4_sql_engine()
            logger.info("✅ Metal 4 SQL engine loaded for metrics")
        except Exception as e:
            logger.warning(f"Metal 4 SQL engine not available for metrics: {e}")

        try:
            from metal4_tensor_ops import get_tensor_ops
            self.tensor_ops = get_tensor_ops()
            logger.info("✅ Metal 4 tensor ops loaded for metrics")
        except Exception as e:
            logger.warning(f"Metal 4 tensor ops not available for metrics: {e}")

        try:
            from metal4_metalfx_renderer import get_metalfx_renderer
            self.metalfx_renderer = get_metalfx_renderer()
            logger.info("✅ MetalFX renderer loaded for metrics")
        except Exception as e:
            logger.warning(f"MetalFX renderer not available for metrics: {e}")

        self._initialized = True
        logger.info("✅ Prometheus metrics exporter initialized")

    # ========================================================================
    # Metric Collection
    # ========================================================================

    def collect_metrics(self) -> str:
        """
        Collect all metrics and format as Prometheus text

        Returns:
            Prometheus-formatted metrics string
        """
        metrics = []

        # Add header
        metrics.append("# Prometheus metrics for ElohimOS")
        metrics.append(f"# Collected at: {datetime.now(UTC).isoformat()}")
        metrics.append("")

        # System metrics
        metrics.extend(self._collect_system_metrics())
        metrics.append("")

        # Metal 4 GPU metrics
        metrics.extend(self._collect_metal4_metrics())
        metrics.append("")

        # Application metrics
        metrics.extend(self._collect_application_metrics())
        metrics.append("")

        # Health metrics
        metrics.extend(self._collect_health_metrics())

        return "\n".join(metrics)

    def _collect_system_metrics(self) -> List[str]:
        """Collect system resource metrics"""
        metrics = []

        metrics.append("# HELP elohimos_system_cpu_percent System CPU usage percentage")
        metrics.append("# TYPE elohimos_system_cpu_percent gauge")
        metrics.append(f"elohimos_system_cpu_percent {psutil.cpu_percent(interval=0.1)}")

        metrics.append("# HELP elohimos_system_memory_percent System memory usage percentage")
        metrics.append("# TYPE elohimos_system_memory_percent gauge")
        mem = psutil.virtual_memory()
        metrics.append(f"elohimos_system_memory_percent {mem.percent}")

        metrics.append("# HELP elohimos_system_memory_used_bytes System memory used in bytes")
        metrics.append("# TYPE elohimos_system_memory_used_bytes gauge")
        metrics.append(f"elohimos_system_memory_used_bytes {mem.used}")

        metrics.append("# HELP elohimos_system_memory_available_bytes System memory available in bytes")
        metrics.append("# TYPE elohimos_system_memory_available_bytes gauge")
        metrics.append(f"elohimos_system_memory_available_bytes {mem.available}")

        metrics.append("# HELP elohimos_system_disk_usage_percent Disk usage percentage")
        metrics.append("# TYPE elohimos_system_disk_usage_percent gauge")
        disk = psutil.disk_usage('/')
        metrics.append(f"elohimos_system_disk_usage_percent {disk.percent}")

        metrics.append("# HELP elohimos_system_disk_used_bytes Disk used in bytes")
        metrics.append("# TYPE elohimos_system_disk_used_bytes gauge")
        metrics.append(f"elohimos_system_disk_used_bytes {disk.used}")

        metrics.append("# HELP elohimos_system_disk_free_bytes Disk free in bytes")
        metrics.append("# TYPE elohimos_system_disk_free_bytes gauge")
        metrics.append(f"elohimos_system_disk_free_bytes {disk.free}")

        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            metrics.append("# HELP elohimos_system_network_bytes_sent_total Total network bytes sent")
            metrics.append("# TYPE elohimos_system_network_bytes_sent_total counter")
            metrics.append(f"elohimos_system_network_bytes_sent_total {net_io.bytes_sent}")

            metrics.append("# HELP elohimos_system_network_bytes_recv_total Total network bytes received")
            metrics.append("# TYPE elohimos_system_network_bytes_recv_total counter")
            metrics.append(f"elohimos_system_network_bytes_recv_total {net_io.bytes_recv}")
        except Exception as e:
            logger.warning(f"Failed to collect network metrics: {e}")

        return metrics

    def _collect_metal4_metrics(self) -> List[str]:
        """Collect Metal 4 GPU acceleration metrics"""
        metrics = []

        if not self.metal4_engine:
            metrics.append("# Metal 4 metrics unavailable (GPU not initialized)")
            return metrics

        # Metal 4 availability
        metrics.append("# HELP elohimos_metal4_available Metal 4 GPU availability (1 = available, 0 = unavailable)")
        metrics.append("# TYPE elohimos_metal4_available gauge")
        metrics.append(f"elohimos_metal4_available {1 if self.metal4_engine.is_available() else 0}")

        # Metal version
        try:
            capabilities = self.metal4_engine.capabilities
            metrics.append("# HELP elohimos_metal4_version Metal version (3 or 4)")
            metrics.append("# TYPE elohimos_metal4_version gauge")
            metrics.append(f"elohimos_metal4_version {capabilities.version.value}")

            # Unified memory support
            metrics.append("# HELP elohimos_metal4_unified_memory Unified memory support (1 = yes, 0 = no)")
            metrics.append("# TYPE elohimos_metal4_unified_memory gauge")
            metrics.append(f"elohimos_metal4_unified_memory {1 if capabilities.supports_unified_memory else 0}")

            # Recommended heap size
            metrics.append("# HELP elohimos_metal4_heap_size_mb Recommended Metal heap size in MB")
            metrics.append("# TYPE elohimos_metal4_heap_size_mb gauge")
            metrics.append(f"elohimos_metal4_heap_size_mb {capabilities.recommended_heap_size_mb}")
        except Exception as e:
            logger.warning(f"Failed to collect Metal 4 capabilities: {e}")

        # Metal 4 SQL Engine stats
        if self.metal4_sql_engine:
            try:
                stats = self.metal4_sql_engine.get_stats()

                metrics.append("# HELP elohimos_metal4_sql_operations_total Total SQL operations executed")
                metrics.append("# TYPE elohimos_metal4_sql_operations_total counter")
                metrics.append(f"elohimos_metal4_sql_operations_total {stats.get('total_operations', 0)}")

                metrics.append("# HELP elohimos_metal4_sql_gpu_operations_total GPU-accelerated SQL operations")
                metrics.append("# TYPE elohimos_metal4_sql_gpu_operations_total counter")
                metrics.append(f"elohimos_metal4_sql_gpu_operations_total {stats.get('gpu_operations', 0)}")

                metrics.append("# HELP elohimos_metal4_sql_cpu_operations_total CPU fallback SQL operations")
                metrics.append("# TYPE elohimos_metal4_sql_cpu_operations_total counter")
                metrics.append(f"elohimos_metal4_sql_cpu_operations_total {stats.get('cpu_operations', 0)}")

                if stats.get('total_operations', 0) > 0:
                    gpu_ratio = stats.get('gpu_operations', 0) / stats['total_operations']
                    metrics.append("# HELP elohimos_metal4_sql_gpu_ratio GPU operation ratio (0.0 to 1.0)")
                    metrics.append("# TYPE elohimos_metal4_sql_gpu_ratio gauge")
                    metrics.append(f"elohimos_metal4_sql_gpu_ratio {gpu_ratio:.4f}")
            except Exception as e:
                logger.warning(f"Failed to collect Metal 4 SQL stats: {e}")

        # Tensor operations stats
        if self.tensor_ops:
            try:
                stats = self.tensor_ops.get_stats()

                metrics.append("# HELP elohimos_metal4_tensor_operations_total Total tensor operations")
                metrics.append("# TYPE elohimos_metal4_tensor_operations_total counter")
                metrics.append(f"elohimos_metal4_tensor_operations_total {stats.get('operations_executed', 0)}")

                metrics.append("# HELP elohimos_metal4_tensor_zero_copy_ops Zero-copy tensor operations")
                metrics.append("# TYPE elohimos_metal4_tensor_zero_copy_ops counter")
                metrics.append(f"elohimos_metal4_tensor_zero_copy_ops {stats.get('zero_copy_ops', 0)}")

                metrics.append("# HELP elohimos_metal4_tensor_zero_copy_ratio Zero-copy operation ratio")
                metrics.append("# TYPE elohimos_metal4_tensor_zero_copy_ratio gauge")
                metrics.append(f"elohimos_metal4_tensor_zero_copy_ratio {stats.get('zero_copy_ratio', 0):.4f}")
            except Exception as e:
                logger.warning(f"Failed to collect tensor ops stats: {e}")

        # MetalFX renderer stats
        if self.metalfx_renderer:
            try:
                stats = self.metalfx_renderer.get_stats()

                metrics.append("# HELP elohimos_metalfx_frames_total Total frames rendered")
                metrics.append("# TYPE elohimos_metalfx_frames_total counter")
                metrics.append(f"elohimos_metalfx_frames_total {stats.get('frame_count', 0)}")

                metrics.append("# HELP elohimos_metalfx_interpolated_frames_total Interpolated frames")
                metrics.append("# TYPE elohimos_metalfx_interpolated_frames_total counter")
                metrics.append(f"elohimos_metalfx_interpolated_frames_total {stats.get('interpolated_frames', 0)}")

                metrics.append("# HELP elohimos_metalfx_current_fps Current frames per second")
                metrics.append("# TYPE elohimos_metalfx_current_fps gauge")
                metrics.append(f"elohimos_metalfx_current_fps {stats.get('current_fps', 0):.1f}")

                metrics.append("# HELP elohimos_metalfx_avg_frame_time_ms Average frame time in milliseconds")
                metrics.append("# TYPE elohimos_metalfx_avg_frame_time_ms gauge")
                metrics.append(f"elohimos_metalfx_avg_frame_time_ms {stats.get('avg_frame_time_ms', 0):.2f}")
            except Exception as e:
                logger.warning(f"Failed to collect MetalFX stats: {e}")

        return metrics

    def _collect_application_metrics(self) -> List[str]:
        """Collect application-specific metrics"""
        metrics = []

        # Uptime
        uptime_seconds = time.time() - self.start_time
        metrics.append("# HELP elohimos_app_uptime_seconds Application uptime in seconds")
        metrics.append("# TYPE elohimos_app_uptime_seconds counter")
        metrics.append(f"elohimos_app_uptime_seconds {uptime_seconds:.0f}")

        # Database metrics (if available)
        try:
            from auth_middleware import auth_service
            import sqlite3

            conn = sqlite3.connect(str(auth_service.db_path))
            cur = conn.cursor()

            # User count
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            metrics.append("# HELP elohimos_app_users_total Total registered users")
            metrics.append("# TYPE elohimos_app_users_total gauge")
            metrics.append(f"elohimos_app_users_total {user_count}")

            # Workflow count
            try:
                cur.execute("SELECT COUNT(*) FROM workflows")
                workflow_count = cur.fetchone()[0]
                metrics.append("# HELP elohimos_app_workflows_total Total workflows")
                metrics.append("# TYPE elohimos_app_workflows_total gauge")
                metrics.append(f"elohimos_app_workflows_total {workflow_count}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

            # Vault items count
            try:
                cur.execute("SELECT COUNT(*) FROM vault_items")
                vault_count = cur.fetchone()[0]
                metrics.append("# HELP elohimos_app_vault_items_total Total vault items")
                metrics.append("# TYPE elohimos_app_vault_items_total gauge")
                metrics.append(f"elohimos_app_vault_items_total {vault_count}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

            conn.close()

        except Exception as e:
            logger.warning(f"Failed to collect application metrics: {e}")

        return metrics

    def _collect_health_metrics(self) -> List[str]:
        """Collect health status metrics"""
        metrics = []

        # Overall health (1 = healthy, 0 = unhealthy)
        metrics.append("# HELP elohimos_health_status Overall health status (1 = healthy, 0 = unhealthy)")
        metrics.append("# TYPE elohimos_health_status gauge")

        # Check critical components
        healthy = True

        # Database health
        try:
            from auth_middleware import auth_service
            import sqlite3
            conn = sqlite3.connect(str(auth_service.db_path))
            conn.execute("SELECT 1")
            conn.close()
            db_healthy = 1
        except Exception:
            db_healthy = 0
            healthy = False

        metrics.append("# HELP elohimos_health_database Database health (1 = healthy, 0 = unhealthy)")
        metrics.append("# TYPE elohimos_health_database gauge")
        metrics.append(f"elohimos_health_database {db_healthy}")

        # Metal 4 health (optional, doesn't affect overall health)
        metal4_healthy = 1 if (self.metal4_engine and self.metal4_engine.is_available()) else 0
        metrics.append("# HELP elohimos_health_metal4 Metal 4 GPU health (1 = available, 0 = unavailable)")
        metrics.append("# TYPE elohimos_health_metal4 gauge")
        metrics.append(f"elohimos_health_metal4 {metal4_healthy}")

        # Overall health
        metrics.append(f"elohimos_health_status {1 if healthy else 0}")

        return metrics

    def is_available(self) -> bool:
        """Check if metrics exporter is initialized"""
        return self._initialized


# ===== Singleton Instance =====

_prometheus_exporter: Optional[PrometheusMetricsExporter] = None


def get_prometheus_exporter() -> PrometheusMetricsExporter:
    """Get singleton Prometheus exporter instance"""
    global _prometheus_exporter
    if _prometheus_exporter is None:
        _prometheus_exporter = PrometheusMetricsExporter()
    return _prometheus_exporter


# Export
__all__ = [
    'PrometheusMetricsExporter',
    'get_prometheus_exporter'
]
