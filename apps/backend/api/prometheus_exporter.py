"""
Prometheus Metrics Exporter

Exports metrics in Prometheus format for monitoring and alerting.

Metrics exported:
- HTTP request counter by endpoint, method, status
- Request duration histogram
- Circuit breaker states
- Cache hit/miss rates
- Database query performance
- System health status
"""

import time


class PrometheusMetrics:
    """
    Generates Prometheus-compatible metrics

    Prometheus format:
    # HELP metric_name Description
    # TYPE metric_name type
    metric_name{label="value"} value timestamp
    """

    def __init__(self):
        self.start_time = time.time()

    def generate_metrics(self) -> str:
        """
        Generate all metrics in Prometheus format

        Returns:
            String in Prometheus exposition format
        """
        metrics = []

        # Add all metric types
        metrics.extend(self._http_metrics())
        metrics.extend(self._cache_metrics())
        metrics.extend(self._circuit_breaker_metrics())
        metrics.extend(self._business_metrics())
        metrics.extend(self._system_metrics())

        return "\n".join(metrics)

    def _http_metrics(self) -> list[str]:
        """Generate HTTP request metrics"""
        from .middleware.logging import get_performance_metrics

        metrics = []
        perf_metrics = get_performance_metrics()

        # HTTP request counter
        metrics.append("# HELP http_requests_total Total HTTP requests")
        metrics.append("# TYPE http_requests_total counter")

        for endpoint, data in perf_metrics.items():
            # Parse endpoint (e.g., "POST /api/v1/chat/stream")
            parts = endpoint.split(" ", 1)
            method = parts[0] if len(parts) > 1 else "GET"
            path = parts[1] if len(parts) > 1 else endpoint

            # Total requests
            metrics.append(
                f'http_requests_total{{method="{method}",path="{path}"}} {data["request_count"]}'
            )

            # Requests by status code
            for status, count in data.get("status_codes", {}).items():
                metrics.append(
                    f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )

        # HTTP request duration
        metrics.append("")
        metrics.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
        metrics.append("# TYPE http_request_duration_ms histogram")

        for endpoint, data in perf_metrics.items():
            parts = endpoint.split(" ", 1)
            method = parts[0] if len(parts) > 1 else "GET"
            path = parts[1] if len(parts) > 1 else endpoint

            # Create histogram buckets
            metrics.append(
                f'http_request_duration_ms_sum{{method="{method}",path="{path}"}} {data["request_count"] * data["avg_duration_ms"]}'
            )
            metrics.append(
                f'http_request_duration_ms_count{{method="{method}",path="{path}"}} {data["request_count"]}'
            )

        # HTTP errors
        metrics.append("")
        metrics.append("# HELP http_errors_total Total HTTP errors")
        metrics.append("# TYPE http_errors_total counter")

        for endpoint, data in perf_metrics.items():
            if data.get("error_count", 0) > 0:
                parts = endpoint.split(" ", 1)
                method = parts[0] if len(parts) > 1 else "GET"
                path = parts[1] if len(parts) > 1 else endpoint

                metrics.append(
                    f'http_errors_total{{method="{method}",path="{path}"}} {data["error_count"]}'
                )

        return metrics

    def _cache_metrics(self) -> list[str]:
        """Generate cache performance metrics"""
        from .utils.cache import get_cache

        metrics = []
        cache = get_cache()
        cache_metrics = cache.get_metrics()

        # Cache hits
        metrics.append("")
        metrics.append("# HELP cache_hits_total Total cache hits")
        metrics.append("# TYPE cache_hits_total counter")
        metrics.append(f'cache_hits_total {cache_metrics["hits"]}')

        # Cache misses
        metrics.append("")
        metrics.append("# HELP cache_misses_total Total cache misses")
        metrics.append("# TYPE cache_misses_total counter")
        metrics.append(f'cache_misses_total {cache_metrics["misses"]}')

        # Cache hit rate
        metrics.append("")
        metrics.append("# HELP cache_hit_rate Cache hit rate percentage")
        metrics.append("# TYPE cache_hit_rate gauge")
        metrics.append(f'cache_hit_rate {cache_metrics["hit_rate"]}')

        # Cache size
        metrics.append("")
        metrics.append("# HELP cache_size_items Number of items in cache")
        metrics.append("# TYPE cache_size_items gauge")
        metrics.append(f'cache_size_items {cache_metrics["size"]}')

        # Cache evictions
        metrics.append("")
        metrics.append("# HELP cache_evictions_total Total cache evictions")
        metrics.append("# TYPE cache_evictions_total counter")
        metrics.append(f'cache_evictions_total {cache_metrics["evictions"]}')

        return metrics

    def _circuit_breaker_metrics(self) -> list[str]:
        """Generate circuit breaker metrics"""
        from .utils.circuit_breaker import get_all_circuit_breakers

        metrics = []
        breakers = get_all_circuit_breakers()

        # Circuit breaker state
        metrics.append("")
        metrics.append(
            "# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half_open)"
        )
        metrics.append("# TYPE circuit_breaker_state gauge")

        state_values = {"closed": 0, "open": 1, "half_open": 2}

        for name, cb in breakers.items():
            cb_metrics = cb.get_metrics()
            state_value = state_values.get(cb_metrics["state"], 0)
            metrics.append(f'circuit_breaker_state{{service="{name}"}} {state_value}')

        # Circuit breaker failures
        metrics.append("")
        metrics.append("# HELP circuit_breaker_failures_total Total failures")
        metrics.append("# TYPE circuit_breaker_failures_total counter")

        for name, cb in breakers.items():
            cb_metrics = cb.get_metrics()
            metrics.append(
                f'circuit_breaker_failures_total{{service="{name}"}} {cb_metrics["total_failures"]}'
            )

        # Circuit breaker failure rate
        metrics.append("")
        metrics.append("# HELP circuit_breaker_failure_rate Failure rate percentage")
        metrics.append("# TYPE circuit_breaker_failure_rate gauge")

        for name, cb in breakers.items():
            cb_metrics = cb.get_metrics()
            metrics.append(
                f'circuit_breaker_failure_rate{{service="{name}"}} {cb_metrics["failure_rate"]}'
            )

        return metrics

    def _business_metrics(self) -> list[str]:
        """Generate business-specific metrics"""
        import sqlite3
        from pathlib import Path

        metrics = []

        try:
            # Connect to chat memory database
            db_path = Path("data/chat_memory.db")
            if not db_path.exists():
                return metrics

            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()

            # Total chat sessions
            metrics.append("")
            metrics.append("# HELP chat_sessions_total Total number of chat sessions")
            metrics.append("# TYPE chat_sessions_total gauge")

            cur.execute("SELECT COUNT(*) FROM chat_sessions")
            total_sessions = cur.fetchone()[0]
            metrics.append(f"chat_sessions_total {total_sessions}")

            # Active chat sessions (last 24 hours)
            metrics.append("")
            metrics.append(
                "# HELP chat_sessions_active_24h Chat sessions active in last 24 hours"
            )
            metrics.append("# TYPE chat_sessions_active_24h gauge")

            cur.execute(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM chat_messages
                WHERE timestamp > datetime('now', '-24 hours')
            """
            )
            active_sessions = cur.fetchone()[0]
            metrics.append(f"chat_sessions_active_24h {active_sessions}")

            # Total messages
            metrics.append("")
            metrics.append("# HELP chat_messages_total Total chat messages")
            metrics.append("# TYPE chat_messages_total counter")

            cur.execute("SELECT COUNT(*) FROM chat_messages")
            total_messages = cur.fetchone()[0]
            metrics.append(f"chat_messages_total {total_messages}")

            # Messages by role
            metrics.append("")
            metrics.append("# HELP chat_messages_by_role_total Messages by role")
            metrics.append("# TYPE chat_messages_by_role_total counter")

            cur.execute("SELECT role, COUNT(*) FROM chat_messages GROUP BY role")
            for role, count in cur.fetchall():
                metrics.append(f'chat_messages_by_role_total{{role="{role}"}} {count}')

            # Messages in last hour
            metrics.append("")
            metrics.append("# HELP chat_messages_last_hour Messages sent in last hour")
            metrics.append("# TYPE chat_messages_last_hour gauge")

            cur.execute(
                """
                SELECT COUNT(*)
                FROM chat_messages
                WHERE timestamp > datetime('now', '-1 hour')
            """
            )
            recent_messages = cur.fetchone()[0]
            metrics.append(f"chat_messages_last_hour {recent_messages}")

            # Average session length
            metrics.append("")
            metrics.append("# HELP chat_session_avg_messages Average messages per session")
            metrics.append("# TYPE chat_session_avg_messages gauge")

            if total_sessions > 0:
                avg_messages = total_messages / total_sessions
                metrics.append(f"chat_session_avg_messages {avg_messages:.2f}")

            # Embeddings indexed
            metrics.append("")
            metrics.append("# HELP chat_embeddings_total Total message embeddings indexed")
            metrics.append("# TYPE chat_embeddings_total gauge")

            cur.execute("SELECT COUNT(*) FROM message_embeddings")
            total_embeddings = cur.fetchone()[0]
            metrics.append(f"chat_embeddings_total {total_embeddings}")

            # Embedding coverage
            metrics.append("")
            metrics.append("# HELP chat_embedding_coverage Percentage of messages with embeddings")
            metrics.append("# TYPE chat_embedding_coverage gauge")

            if total_messages > 0:
                embedding_coverage = (total_embeddings / total_messages) * 100
                metrics.append(f"chat_embedding_coverage {embedding_coverage:.2f}")

            conn.close()

        except Exception as e:
            # Log error but don't fail metrics export
            import logging

            logging.error(f"Error collecting business metrics: {e}")

        return metrics

    def _system_metrics(self) -> list[str]:
        """Generate system-level metrics"""
        metrics = []

        # Uptime
        metrics.append("")
        metrics.append("# HELP process_uptime_seconds Process uptime in seconds")
        metrics.append("# TYPE process_uptime_seconds counter")
        uptime = time.time() - self.start_time
        metrics.append(f"process_uptime_seconds {int(uptime)}")

        # Memory usage (if psutil available)
        try:
            import psutil

            process = psutil.Process()
            mem_info = process.memory_info()

            metrics.append("")
            metrics.append("# HELP process_memory_bytes Process memory usage in bytes")
            metrics.append("# TYPE process_memory_bytes gauge")
            metrics.append(f'process_memory_bytes{{type="rss"}} {mem_info.rss}')
            metrics.append(f'process_memory_bytes{{type="vms"}} {mem_info.vms}')

        except ImportError:
            pass

        # CPU usage (if psutil available)
        try:
            import psutil

            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)

            metrics.append("")
            metrics.append("# HELP process_cpu_percent Process CPU usage percentage")
            metrics.append("# TYPE process_cpu_percent gauge")
            metrics.append(f"process_cpu_percent {cpu_percent}")

        except ImportError:
            pass

        return metrics


# Global metrics instance
_prometheus_metrics = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get or create global Prometheus metrics instance"""
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics


def export_metrics() -> str:
    """
    Export all metrics in Prometheus format

    Returns:
        String in Prometheus exposition format
    """
    metrics = get_prometheus_metrics()
    return metrics.generate_metrics()
