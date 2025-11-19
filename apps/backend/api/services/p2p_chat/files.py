"""
P2P Chat Service - File Transfer Operations

File transfer management over P2P:
- File transfer metadata
- Progress tracking
- Chunked file transfers (TODO: implementation pending)
"""

import logging
from pathlib import Path
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .service import P2PChatService

from . import storage

logger = logging.getLogger(__name__)


async def initiate_file_transfer(service: 'P2PChatService',
                                 file_name: str,
                                 file_size: int,
                                 mime_type: str,
                                 channel_id: str,
                                 recipient_ids: list) -> Dict:
    """
    Initiate a file transfer.

    Args:
        service: P2PChatService instance
        file_name: Name of the file
        file_size: File size in bytes
        mime_type: MIME type of the file
        channel_id: Target channel
        recipient_ids: List of recipient peer IDs

    Returns:
        Dict with transfer_id and metadata
    """
    import uuid
    transfer_id = str(uuid.uuid4())

    # Calculate chunks (1MB per chunk)
    chunk_size = 1024 * 1024  # 1MB
    chunks_total = (file_size + chunk_size - 1) // chunk_size

    # Store transfer metadata
    storage.save_file_transfer(
        service.db_path,
        transfer_id,
        file_name,
        file_size,
        mime_type,
        service.peer_id,
        channel_id,
        recipient_ids,
        chunks_total
    )

    logger.info(f"Initiated file transfer: {file_name} ({file_size} bytes, {chunks_total} chunks)")

    return {
        "transfer_id": transfer_id,
        "file_name": file_name,
        "file_size": file_size,
        "chunks_total": chunks_total,
        "status": "initiated"
    }


async def update_transfer_progress(service: 'P2PChatService',
                                   transfer_id: str,
                                   chunks_received: int,
                                   progress_percent: float) -> None:
    """
    Update file transfer progress.

    Args:
        service: P2PChatService instance
        transfer_id: Transfer identifier
        chunks_received: Number of chunks received
        progress_percent: Progress percentage (0-100)
    """
    status = "completed" if progress_percent >= 100.0 else "active"

    storage.update_file_transfer_progress(
        service.db_path,
        transfer_id,
        chunks_received,
        progress_percent,
        status
    )

    logger.debug(f"File transfer {transfer_id[:8]}: {progress_percent:.1f}% ({chunks_received} chunks)")


async def get_transfer_status(service: 'P2PChatService', transfer_id: str) -> Optional[Dict]:
    """
    Get file transfer status.

    Args:
        service: P2PChatService instance
        transfer_id: Transfer identifier

    Returns:
        Transfer metadata dict or None if not found
    """
    return storage.get_file_transfer(service.db_path, transfer_id)
