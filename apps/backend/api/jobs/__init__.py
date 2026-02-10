"""
Jobs Package

Background job management for MedStation:
- BackgroundJobManager: Scheduled cleanup and maintenance tasks
- Analytics aggregation jobs (hourly/daily)
"""

from api.jobs.manager import (
    JobConfig,
    BackgroundJobManager,
    get_job_manager,
    register_analytics_jobs,
    aggregate_analytics_hourly,
    aggregate_analytics_daily,
)

__all__ = [
    "JobConfig",
    "BackgroundJobManager",
    "get_job_manager",
    "register_analytics_jobs",
    "aggregate_analytics_hourly",
    "aggregate_analytics_daily",
]
