"""
Model Download Types - Enum and dataclass for download queue

Extracted from model_download_queue.py during P2 decomposition.
Contains:
- DownloadStatus (status enum)
- DownloadJob (job dataclass)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


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


__all__ = [
    "DownloadStatus",
    "DownloadJob",
]
