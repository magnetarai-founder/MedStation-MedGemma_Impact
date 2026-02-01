"""
HuggingFace GGUF Model Downloader

Downloads GGUF model files from HuggingFace Hub with:
- Progress streaming via async generators
- Resumable downloads
- Authentication support
- Concurrent download management
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Progress update for a download"""
    job_id: str
    status: str  # "starting", "downloading", "verifying", "completed", "failed", "canceled"
    progress: float  # 0-100
    downloaded_bytes: int
    total_bytes: int
    speed_bps: int  # bytes per second
    eta_seconds: Optional[int]
    message: str
    error: Optional[str] = None


@dataclass
class ActiveDownload:
    """Tracks an active download"""
    job_id: str
    repo_id: str
    filename: str
    started_at: datetime
    task: Optional[asyncio.Task] = field(default=None, repr=False)
    canceled: bool = False
    paused: bool = False
    downloaded_bytes: int = 0
    total_bytes: int = 0


class HuggingFaceDownloader:
    """
    Manages GGUF downloads from HuggingFace Hub

    Features:
    - Async streaming progress updates
    - Resumable downloads with Range requests
    - Concurrent download limit
    - Authentication via HF_TOKEN environment variable
    """

    MAX_CONCURRENT_DOWNLOADS = 2
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for progress updates

    def __init__(self):
        self._active_downloads: Dict[str, ActiveDownload] = {}
        self._download_lock = asyncio.Lock()
        self._hf_token: Optional[str] = None

        # Try to get HF token from environment
        import os
        self._hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HuggingFace API requests"""
        headers = {
            "User-Agent": "MagnetarStudio/1.0 (GGUF Downloader)",
        }
        if self._hf_token:
            headers["Authorization"] = f"Bearer {self._hf_token}"
        return headers

    async def download_model(
        self,
        repo_id: str,
        filename: str,
        revision: str = "main"
    ) -> AsyncGenerator[DownloadProgress, None]:
        """
        Download a GGUF model from HuggingFace Hub

        Args:
            repo_id: HuggingFace repository ID (e.g., 'google/medgemma-1.5-4b-it-GGUF')
            filename: GGUF filename to download (e.g., 'medgemma-1.5-4b-it-Q4_K_M.gguf')
            revision: Git revision/branch (default: 'main')

        Yields:
            DownloadProgress updates during download
        """
        from .storage import get_huggingface_storage

        storage = get_huggingface_storage()
        job_id = str(uuid.uuid4())[:8]

        # Check if already downloaded
        if storage.is_model_downloaded(repo_id, filename):
            yield DownloadProgress(
                job_id=job_id,
                status="completed",
                progress=100.0,
                downloaded_bytes=0,
                total_bytes=0,
                speed_bps=0,
                eta_seconds=None,
                message=f"Model already downloaded: {filename}"
            )
            return

        # Check concurrent download limit
        async with self._download_lock:
            if len(self._active_downloads) >= self.MAX_CONCURRENT_DOWNLOADS:
                yield DownloadProgress(
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    downloaded_bytes=0,
                    total_bytes=0,
                    speed_bps=0,
                    eta_seconds=None,
                    message="Too many concurrent downloads",
                    error="Maximum concurrent downloads reached. Please wait."
                )
                return

            # Register active download
            self._active_downloads[job_id] = ActiveDownload(
                job_id=job_id,
                repo_id=repo_id,
                filename=filename,
                started_at=datetime.utcnow()
            )

        try:
            yield DownloadProgress(
                job_id=job_id,
                status="starting",
                progress=0,
                downloaded_bytes=0,
                total_bytes=0,
                speed_bps=0,
                eta_seconds=None,
                message=f"Starting download: {filename}"
            )

            # Build download URL
            # HuggingFace Hub URL format: https://huggingface.co/{repo_id}/resolve/{revision}/{filename}
            download_url = f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"

            # Prepare paths
            model_dir = storage.get_model_directory(repo_id)
            model_dir.mkdir(parents=True, exist_ok=True)
            final_path = storage.get_model_path(repo_id, filename)
            partial_path = storage.get_partial_path(repo_id, filename)

            # Check for existing partial download
            resume_from = 0
            if partial_path.exists():
                resume_from = partial_path.stat().st_size
                logger.info(f"Resuming download from byte {resume_from}")

            # Perform download
            import httpx

            headers = self._get_headers()
            if resume_from > 0:
                headers["Range"] = f"bytes={resume_from}-"

            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=None), follow_redirects=True) as client:
                async with client.stream("GET", download_url, headers=headers) as response:
                    # Handle response codes
                    if response.status_code == 416:
                        # Range not satisfiable - file might be complete
                        if partial_path.exists():
                            partial_path.rename(final_path)
                            yield DownloadProgress(
                                job_id=job_id,
                                status="completed",
                                progress=100.0,
                                downloaded_bytes=resume_from,
                                total_bytes=resume_from,
                                speed_bps=0,
                                eta_seconds=None,
                                message=f"Download already complete: {filename}"
                            )
                            return

                    if response.status_code not in (200, 206):
                        yield DownloadProgress(
                            job_id=job_id,
                            status="failed",
                            progress=0,
                            downloaded_bytes=0,
                            total_bytes=0,
                            speed_bps=0,
                            eta_seconds=None,
                            message=f"Download failed: HTTP {response.status_code}",
                            error=f"Server returned status {response.status_code}"
                        )
                        return

                    # Parse content length
                    content_length = int(response.headers.get("content-length", 0))
                    total_bytes = content_length + resume_from

                    if total_bytes == 0:
                        yield DownloadProgress(
                            job_id=job_id,
                            status="failed",
                            progress=0,
                            downloaded_bytes=0,
                            total_bytes=0,
                            speed_bps=0,
                            eta_seconds=None,
                            message="Could not determine file size",
                            error="Content-Length header missing"
                        )
                        return

                    logger.info(f"Downloading {filename}: {total_bytes / (1024**3):.2f} GB")

                    # Download with progress tracking
                    downloaded = resume_from
                    start_time = time.time()
                    last_update_time = start_time
                    last_downloaded = downloaded
                    update_interval = 0.5  # Update every 500ms

                    mode = "ab" if resume_from > 0 else "wb"

                    async with asyncio.TaskGroup() as tg:
                        async def write_chunks():
                            nonlocal downloaded, last_update_time, last_downloaded

                            with open(partial_path, mode) as f:
                                async for chunk in response.aiter_bytes(self.CHUNK_SIZE):
                                    # Check for cancellation
                                    if self._active_downloads.get(job_id, ActiveDownload(job_id, "", "", datetime.utcnow())).canceled:
                                        raise asyncio.CancelledError("Download canceled by user")

                                    f.write(chunk)
                                    downloaded += len(chunk)

                        # Start download task
                        download_task = tg.create_task(write_chunks())

                        # Progress reporting loop
                        while not download_task.done():
                            await asyncio.sleep(update_interval)

                            current_time = time.time()
                            elapsed = current_time - last_update_time

                            if elapsed >= update_interval:
                                # Calculate speed
                                bytes_since_last = downloaded - last_downloaded
                                speed_bps = int(bytes_since_last / elapsed) if elapsed > 0 else 0

                                # Calculate ETA
                                remaining_bytes = total_bytes - downloaded
                                eta_seconds = int(remaining_bytes / speed_bps) if speed_bps > 0 else None

                                # Calculate progress
                                progress = (downloaded / total_bytes) * 100 if total_bytes > 0 else 0

                                yield DownloadProgress(
                                    job_id=job_id,
                                    status="downloading",
                                    progress=progress,
                                    downloaded_bytes=downloaded,
                                    total_bytes=total_bytes,
                                    speed_bps=speed_bps,
                                    eta_seconds=eta_seconds,
                                    message=f"Downloading {filename}"
                                )

                                last_update_time = current_time
                                last_downloaded = downloaded

            # Verify and finalize
            yield DownloadProgress(
                job_id=job_id,
                status="verifying",
                progress=99.0,
                downloaded_bytes=downloaded,
                total_bytes=total_bytes,
                speed_bps=0,
                eta_seconds=None,
                message="Verifying download..."
            )

            # Check file size
            actual_size = partial_path.stat().st_size
            if actual_size != total_bytes:
                yield DownloadProgress(
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    downloaded_bytes=actual_size,
                    total_bytes=total_bytes,
                    speed_bps=0,
                    eta_seconds=None,
                    message="Download incomplete",
                    error=f"Expected {total_bytes} bytes, got {actual_size}"
                )
                return

            # Move partial to final
            partial_path.rename(final_path)

            # Register in storage
            storage.register_model(
                repo_id=repo_id,
                filename=filename,
                size_bytes=total_bytes,
                quantization=self._extract_quantization(filename),
                metadata={"revision": revision, "download_url": download_url}
            )

            total_time = time.time() - start_time
            avg_speed = total_bytes / total_time if total_time > 0 else 0

            yield DownloadProgress(
                job_id=job_id,
                status="completed",
                progress=100.0,
                downloaded_bytes=total_bytes,
                total_bytes=total_bytes,
                speed_bps=int(avg_speed),
                eta_seconds=None,
                message=f"Downloaded {filename} ({total_bytes / (1024**3):.2f} GB)"
            )

            logger.info(f"Download completed: {filename} in {total_time:.1f}s")

        except asyncio.CancelledError:
            yield DownloadProgress(
                job_id=job_id,
                status="canceled",
                progress=0,
                downloaded_bytes=0,
                total_bytes=0,
                speed_bps=0,
                eta_seconds=None,
                message="Download canceled",
                error="Canceled by user"
            )

        except Exception as e:
            logger.error(f"Download failed for {filename}: {e}")
            yield DownloadProgress(
                job_id=job_id,
                status="failed",
                progress=0,
                downloaded_bytes=0,
                total_bytes=0,
                speed_bps=0,
                eta_seconds=None,
                message=f"Download failed: {str(e)}",
                error=str(e)
            )

        finally:
            # Clean up active download tracking
            async with self._download_lock:
                self._active_downloads.pop(job_id, None)

    def _extract_quantization(self, filename: str) -> Optional[str]:
        """Extract quantization level from filename"""
        # Common patterns: Q4_K_M, Q5_K_M, Q8_0, etc.
        import re
        match = re.search(r'(Q\d+_K_[MSL]|Q\d+_\d+|F16|F32)', filename, re.IGNORECASE)
        return match.group(1).upper() if match else None

    async def cancel_download(self, job_id: str) -> bool:
        """
        Cancel an active download

        Args:
            job_id: Job ID to cancel

        Returns:
            True if download was found and canceled
        """
        async with self._download_lock:
            if job_id in self._active_downloads:
                self._active_downloads[job_id].canceled = True
                if self._active_downloads[job_id].task:
                    self._active_downloads[job_id].task.cancel()
                logger.info(f"Canceled download: {job_id}")
                return True
        return False

    async def pause_download(self, job_id: str) -> bool:
        """
        Pause an active download

        The partial file is preserved for resumption.

        Args:
            job_id: Job ID to pause

        Returns:
            True if download was found and paused
        """
        async with self._download_lock:
            if job_id in self._active_downloads:
                download = self._active_downloads[job_id]
                if not download.paused and not download.canceled:
                    download.paused = True
                    if download.task:
                        download.task.cancel()
                    logger.info(f"Paused download: {job_id}")
                    return True
        return False

    async def resume_download(self, job_id: str) -> Optional[str]:
        """
        Resume a paused download

        Args:
            job_id: Job ID to resume

        Returns:
            New job ID if resumed successfully, None otherwise
        """
        async with self._download_lock:
            if job_id in self._active_downloads:
                download = self._active_downloads[job_id]
                if download.paused:
                    # Remove old entry - a new download will be started
                    repo_id = download.repo_id
                    filename = download.filename
                    self._active_downloads.pop(job_id, None)
                    logger.info(f"Resuming download for {filename} (was job {job_id})")
                    # Return info needed to restart - caller will initiate new download
                    return f"{repo_id}:{filename}"
        return None

    def get_paused_downloads(self) -> Dict[str, Dict[str, Any]]:
        """Get info about paused downloads"""
        return {
            job_id: {
                "job_id": download.job_id,
                "repo_id": download.repo_id,
                "filename": download.filename,
                "started_at": download.started_at.isoformat(),
                "downloaded_bytes": download.downloaded_bytes,
                "total_bytes": download.total_bytes,
            }
            for job_id, download in self._active_downloads.items()
            if download.paused
        }

    def get_active_downloads(self) -> Dict[str, Dict[str, Any]]:
        """Get info about all active downloads"""
        return {
            job_id: {
                "job_id": download.job_id,
                "repo_id": download.repo_id,
                "filename": download.filename,
                "started_at": download.started_at.isoformat(),
            }
            for job_id, download in self._active_downloads.items()
        }


# Singleton instance
_downloader_instance: Optional[HuggingFaceDownloader] = None


def get_huggingface_downloader() -> HuggingFaceDownloader:
    """Get the singleton downloader instance"""
    global _downloader_instance
    if _downloader_instance is None:
        _downloader_instance = HuggingFaceDownloader()
    return _downloader_instance


__all__ = [
    "HuggingFaceDownloader",
    "DownloadProgress",
    "get_huggingface_downloader",
]
