"""
Model Download Queue Service

Manages concurrent model downloads with FIFO queue.
Sprint 5 Theme B: Download Queue Management
"""

import asyncio
import logging
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DownloadStatus(str, Enum):
    """Download status states"""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class DownloadJob:
    """Represents a model download job"""
    model_name: str
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    speed: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    position: Optional[int] = None  # Queue position (1-indexed)
    task: Optional[asyncio.Task] = field(default=None, repr=False)  # Internal task reference


class ModelDownloadQueue:
    """
    In-memory download queue with max concurrent limit

    Features:
    - FIFO queue with max 2 concurrent downloads
    - State machine: queued → downloading → completed/failed/canceled
    - Cancel support for active and queued jobs
    - Thread-safe operations
    """

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.jobs: Dict[str, DownloadJob] = {}  # model_name → job
        self.queue: List[str] = []  # Ordered list of queued model names
        self.active: List[str] = []  # Currently downloading models
        self._lock = asyncio.Lock()

    async def enqueue(self, model_name: str) -> bool:
        """
        Add model to download queue

        Args:
            model_name: Model to download

        Returns:
            True if enqueued, False if already queued/downloading
        """
        async with self._lock:
            # Skip if already exists
            if model_name in self.jobs:
                job = self.jobs[model_name]
                if job.status in [DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING]:
                    logger.info(f"Model {model_name} already in queue/downloading")
                    return False

            # Create new job
            job = DownloadJob(model_name=model_name)
            self.jobs[model_name] = job
            self.queue.append(model_name)

            # Update queue positions
            self._update_positions()

            logger.info(f"Enqueued model {model_name}")

            # Try to start downloads
            await self._start_next_downloads()

            return True

    async def cancel(self, model_name: str) -> bool:
        """
        Cancel a download (active or queued)

        Args:
            model_name: Model to cancel

        Returns:
            True if canceled, False if not found/already completed
        """
        async with self._lock:
            if model_name not in self.jobs:
                return False

            job = self.jobs[model_name]

            # Can't cancel completed/failed jobs
            if job.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELED]:
                return False

            # Cancel active download
            if job.status == DownloadStatus.DOWNLOADING and job.task:
                job.task.cancel()
                if model_name in self.active:
                    self.active.remove(model_name)

            # Remove from queue
            if model_name in self.queue:
                self.queue.remove(model_name)

            # Update status
            job.status = DownloadStatus.CANCELED
            job.completed_at = datetime.utcnow()

            logger.info(f"Canceled download for {model_name}")

            # Update positions and start next
            self._update_positions()
            await self._start_next_downloads()

            return True

    async def get_status(self) -> List[Dict]:
        """
        Get status of all downloads

        Returns:
            List of download job dicts
        """
        async with self._lock:
            return [
                {
                    "name": job.model_name,
                    "status": job.status.value,
                    "progress": job.progress,
                    "speed": job.speed,
                    "error": job.error,
                    "position": job.position,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
                for job in self.jobs.values()
            ]

    async def get_job(self, model_name: str) -> Optional[DownloadJob]:
        """Get specific job by model name"""
        async with self._lock:
            return self.jobs.get(model_name)

    async def update_progress(self, model_name: str, progress: float, speed: Optional[str] = None):
        """
        Update download progress (called by download task)

        Args:
            model_name: Model being downloaded
            progress: Progress percentage (0-100)
            speed: Download speed string (e.g., "5.2 MB/s")
        """
        async with self._lock:
            if model_name in self.jobs:
                job = self.jobs[model_name]
                job.progress = progress
                if speed:
                    job.speed = speed

    async def mark_completed(self, model_name: str, success: bool = True, error: Optional[str] = None):
        """
        Mark download as completed or failed

        Args:
            model_name: Model that finished
            success: Whether download succeeded
            error: Error message if failed
        """
        async with self._lock:
            if model_name not in self.jobs:
                return

            job = self.jobs[model_name]
            job.status = DownloadStatus.COMPLETED if success else DownloadStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.progress = 100.0 if success else job.progress
            if error:
                job.error = error

            # Remove from active
            if model_name in self.active:
                self.active.remove(model_name)

            logger.info(f"Download {'completed' if success else 'failed'} for {model_name}")

            # Update positions and start next
            self._update_positions()
            await self._start_next_downloads()

    def _update_positions(self):
        """Update queue positions for all queued jobs"""
        for idx, model_name in enumerate(self.queue):
            if model_name in self.jobs:
                self.jobs[model_name].position = idx + 1

    async def _start_next_downloads(self):
        """Start downloads up to max_concurrent limit"""
        while len(self.active) < self.max_concurrent and self.queue:
            model_name = self.queue.pop(0)
            if model_name not in self.jobs:
                continue

            job = self.jobs[model_name]
            job.status = DownloadStatus.DOWNLOADING
            job.started_at = datetime.utcnow()
            job.position = None  # Clear position when starting

            self.active.append(model_name)

            logger.info(f"Starting download for {model_name} ({len(self.active)}/{self.max_concurrent} active)")

            # Note: Actual download task would be started here by the caller
            # This queue manages state; actual downloads happen elsewhere

    async def clear_completed(self):
        """Remove completed/failed/canceled jobs from history"""
        async with self._lock:
            to_remove = [
                name for name, job in self.jobs.items()
                if job.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELED]
            ]
            for name in to_remove:
                del self.jobs[name]
            logger.info(f"Cleared {len(to_remove)} completed jobs")


# Global queue instance
_queue: Optional[ModelDownloadQueue] = None


def get_download_queue() -> ModelDownloadQueue:
    """
    Get or create global download queue instance

    Returns:
        ModelDownloadQueue instance
    """
    global _queue

    if _queue is None:
        _queue = ModelDownloadQueue(max_concurrent=2)

    return _queue
