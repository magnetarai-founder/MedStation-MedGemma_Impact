"""
Startup health checks.

Runs health checks and registers analytics jobs on application startup.
"""

import logging

logger = logging.getLogger(__name__)


async def run_health_checks() -> None:
    """
    Run any startup health checks (optional).

    Currently includes:
    - Analytics aggregation job registration (Sprint 6 Theme A)

    Note: Failures are logged but do not prevent startup.
    """
    # Register analytics aggregation jobs (Sprint 6 Theme A)
    try:
        from api.background_jobs import register_analytics_jobs, get_job_manager

        register_analytics_jobs()

        # Start the background job manager
        job_manager = get_job_manager()
        await job_manager.start()

        logger.info("✓ Analytics aggregation jobs started")
    except Exception as e:
        logger.warning(f"Failed to start analytics jobs: {e}")
        # Not fatal - app can run without analytics jobs
