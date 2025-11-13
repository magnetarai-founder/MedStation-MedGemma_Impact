"""
Centralized Background Jobs for ElohimOS
Manages scheduled cleanup tasks and maintenance operations
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JobConfig:
    """Configuration for a background job"""
    name: str
    interval_seconds: int
    task: Callable
    description: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class BackgroundJobManager:
    """
    Centralized manager for background maintenance jobs

    Usage:
        manager = BackgroundJobManager()
        manager.register_job(
            name="cleanup_temp",
            interval_seconds=3600,
            task=cleanup_temp_files,
            description="Clean up temp files older than 24h"
        )
        await manager.start()
    """

    def __init__(self):
        self.jobs: Dict[str, JobConfig] = {}
        self.running = False
        self._tasks: List[asyncio.Task] = []

    def register_job(
        self,
        name: str,
        interval_seconds: int,
        task: Callable,
        description: str,
        enabled: bool = True
    ):
        """Register a background job"""
        if name in self.jobs:
            logger.warning(f"Job '{name}' already registered, overwriting")

        self.jobs[name] = JobConfig(
            name=name,
            interval_seconds=interval_seconds,
            task=task,
            description=description,
            enabled=enabled
        )
        logger.info(f"📋 Registered background job: {name} (every {interval_seconds}s)")

    async def _run_job_loop(self, job_config: JobConfig):
        """Run a job on its scheduled interval"""
        while self.running:
            try:
                if job_config.enabled:
                    logger.debug(f"Running background job: {job_config.name}")

                    # Run the job
                    if asyncio.iscoroutinefunction(job_config.task):
                        await job_config.task()
                    else:
                        # Run sync functions in thread pool
                        await asyncio.to_thread(job_config.task)

                    # Update stats
                    job_config.last_run = datetime.utcnow()
                    job_config.run_count += 1

                    logger.debug(f"✅ Completed: {job_config.name} (run #{job_config.run_count})")

            except Exception as e:
                job_config.error_count += 1
                logger.error(f"❌ Background job '{job_config.name}' failed: {e}")

            # Wait for next run
            await asyncio.sleep(job_config.interval_seconds)

    async def start(self):
        """Start all enabled background jobs"""
        if self.running:
            logger.warning("Background jobs already running")
            return

        self.running = True
        logger.info(f"🚀 Starting {len([j for j in self.jobs.values() if j.enabled])} background jobs")

        # Start a task for each enabled job
        for job_config in self.jobs.values():
            if job_config.enabled:
                task = asyncio.create_task(self._run_job_loop(job_config))
                self._tasks.append(task)
                logger.info(f"▶️  Started: {job_config.name}")

    async def stop(self):
        """Stop all background jobs"""
        if not self.running:
            return

        self.running = False
        logger.info("⏹️  Stopping background jobs...")

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("✅ All background jobs stopped")

    def get_status(self) -> Dict:
        """Get status of all jobs"""
        return {
            "running": self.running,
            "total_jobs": len(self.jobs),
            "enabled_jobs": len([j for j in self.jobs.values() if j.enabled]),
            "jobs": [
                {
                    "name": job.name,
                    "description": job.description,
                    "enabled": job.enabled,
                    "interval_seconds": job.interval_seconds,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "run_count": job.run_count,
                    "error_count": job.error_count
                }
                for job in self.jobs.values()
            ]
        }

    def enable_job(self, name: str):
        """Enable a job"""
        if name in self.jobs:
            self.jobs[name].enabled = True
            logger.info(f"Enabled job: {name}")

    def disable_job(self, name: str):
        """Disable a job"""
        if name in self.jobs:
            self.jobs[name].enabled = False
            logger.info(f"Disabled job: {name}")


# Singleton instance
_job_manager: Optional[BackgroundJobManager] = None


def get_job_manager() -> BackgroundJobManager:
    """Get the global background job manager"""
    global _job_manager
    if _job_manager is None:
        _job_manager = BackgroundJobManager()
    return _job_manager


# ============================================================================
# COMMON CLEANUP JOBS
# ============================================================================

async def cleanup_temp_files(max_age_hours: int = 24):
    """
    Clean up temporary files older than max_age_hours

    This function is async-compatible and can be registered directly.
    """
    from pathlib import Path
    from datetime import datetime, timedelta

    # Determine API directory
    try:
        api_dir = Path(__file__).parent
    except:
        logger.error("Could not determine API directory for cleanup")
        return

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cleaned_count = 0

    for temp_dir_name in ["temp_uploads", "temp_exports"]:
        temp_dir = api_dir / temp_dir_name

        if temp_dir.exists():
            for file_path in temp_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.debug(f"Cleaned up: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to clean {file_path}: {e}")

    if cleaned_count > 0:
        logger.info(f"🧹 Cleaned {cleaned_count} temp files older than {max_age_hours}h")


def cleanup_expired_sessions(session_storage: Dict, max_age_hours: int = 24):
    """
    Clean up expired sessions from session storage

    Args:
        session_storage: Dict of sessions (from main.py)
        max_age_hours: Maximum session age
    """
    from datetime import datetime, timedelta

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    expired_sessions = []

    for session_id, session_data in session_storage.items():
        created_at = session_data.get('created_at')
        if created_at and created_at < cutoff_time:
            expired_sessions.append(session_id)

    # Remove expired sessions
    for session_id in expired_sessions:
        try:
            # Close engine if present
            if 'engine' in session_storage[session_id]:
                session_storage[session_id]['engine'].close()

            del session_storage[session_id]
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")

    if expired_sessions:
        logger.info(f"🧹 Cleaned {len(expired_sessions)} expired sessions")


async def cleanup_audit_logs(max_age_days: int = 90):
    """
    Clean up old audit logs

    Args:
        max_age_days: Keep logs newer than this many days
    """
    try:
        from audit_logger import get_audit_logger

        audit = get_audit_logger()
        deleted_count = audit.cleanup_old_logs(max_age_days)

        if deleted_count > 0:
            logger.info(f"🧹 Cleaned {deleted_count} audit logs older than {max_age_days} days")

    except ImportError:
        logger.debug("Audit logger not available for cleanup")
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")


# ============================================================================
# ANALYTICS AGGREGATION JOBS (Sprint 6 Theme A)
# ============================================================================

async def aggregate_analytics_hourly():
    """
    Aggregate analytics data hourly

    Re-aggregates today's data (idempotent) to keep dashboard current
    """
    try:
        from api.services.analytics import get_analytics_service
        from datetime import datetime

        analytics = get_analytics_service()
        today = datetime.utcnow().date().strftime('%Y-%m-%d')

        # Re-aggregate today (idempotent)
        await asyncio.to_thread(analytics.aggregate_daily, today)

        logger.info(f"📊 Analytics aggregation complete for {today}")

    except Exception as e:
        logger.error(f"Failed to aggregate analytics: {e}", exc_info=True)


async def aggregate_analytics_daily():
    """
    Aggregate analytics data daily

    Runs aggregation for yesterday and today to catch any missed events
    """
    try:
        from api.services.analytics import get_analytics_service
        from datetime import datetime, timedelta

        analytics = get_analytics_service()

        # Aggregate yesterday and today
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        await asyncio.to_thread(analytics.aggregate_daily, yesterday.strftime('%Y-%m-%d'))
        await asyncio.to_thread(analytics.aggregate_daily, today.strftime('%Y-%m-%d'))

        logger.info(f"📊 Daily analytics aggregation complete")

    except Exception as e:
        logger.error(f"Failed to run daily analytics aggregation: {e}", exc_info=True)


def register_analytics_jobs(manager: Optional[BackgroundJobManager] = None):
    """
    Register analytics aggregation jobs with the background job manager

    Call this from main.py after job manager is initialized
    """
    if manager is None:
        manager = get_job_manager()

    # Hourly aggregation (keeps dashboard current throughout the day)
    manager.register_job(
        name="analytics_hourly",
        interval_seconds=3600,  # Every hour
        task=aggregate_analytics_hourly,
        description="Aggregate analytics data hourly for real-time dashboard updates"
    )

    # Daily aggregation (comprehensive daily rollup)
    manager.register_job(
        name="analytics_daily",
        interval_seconds=86400,  # Every 24 hours
        task=aggregate_analytics_daily,
        description="Aggregate analytics data daily (yesterday + today)"
    )

    logger.info("✅ Analytics aggregation jobs registered")
