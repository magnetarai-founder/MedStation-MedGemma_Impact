"""
Offline Mesh - File Sharing Routes

P2P file sharing endpoints for mesh network.
"""

from fastapi import APIRouter, HTTPException, Request
from api.errors import http_404
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from api.offline_file_share import get_file_share
from api.offline_mesh.models import (
    ShareFileRequest,
    DownloadFileRequest,
    FileShareResponse,
)
from api.core.exceptions import handle_exceptions

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/files/share", response_model=FileShareResponse)
@handle_exceptions("share file", resource_type="File")
async def share_file(request: Request, body: ShareFileRequest) -> FileShareResponse:
    """
    Share a file on the local mesh network

    Makes a local file available for direct P2P transfer to discovered peers.
    No central server required - files transfer directly between devices.

    Flow:
    1. Validates file exists and is readable
    2. Calculates SHA256 hash for integrity verification
    3. Announces file availability to mesh network
    4. Peers can discover via GET /files/shared
    5. Download initiated with POST /files/download

    Security:
        - File path must be absolute and accessible to backend process
        - Hash verification ensures transfer integrity
        - Auth required (JWT) - only authenticated users can share

    Args:
        file_path: Absolute path to file on local filesystem
        shared_by_peer_id: UUID of sharing peer (from /discovery/start)
        shared_by_name: Display name of sharer
        description: Optional human-readable description
        tags: Optional categorization tags

    Returns:
        file_id: Unique identifier for this shared file
        sha256_hash: Integrity verification hash
        size_bytes: File size
    """
    file_share = get_file_share()

    file_path = Path(body.file_path)
    if not file_path.exists():
        raise http_404("File not found", resource="file")

    shared_file = await file_share.share_file(
        file_path=file_path,
        shared_by_peer_id=body.shared_by_peer_id,
        shared_by_name=body.shared_by_name,
        description=body.description,
        tags=body.tags
    )

    return {
        "file_id": shared_file.file_id,
        "filename": shared_file.filename,
        "size_bytes": shared_file.size_bytes,
        "sha256_hash": shared_file.sha256_hash,
        "shared_at": shared_file.shared_at
    }


@router.get("/files/list")
@handle_exceptions("list shared files")
async def list_shared_files(tags: Optional[str] = None) -> Dict[str, Any]:
    """Get list of shared files (optionally filtered by tags)"""
    file_share = get_file_share()

    tag_list = tags.split(',') if tags else None
    files = file_share.get_shared_files(tags=tag_list)

    return {
        "count": len(files),
        "files": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "size_bytes": f.size_bytes,
                "size_mb": f.size_bytes / (1024 * 1024),
                "mime_type": f.mime_type,
                "shared_by_name": f.shared_by_name,
                "shared_at": f.shared_at,
                "description": f.description,
                "tags": f.tags
            }
            for f in files
        ]
    }


@router.post("/files/download")
@handle_exceptions("download file", resource_type="File")
async def download_file(request: Request, body: DownloadFileRequest) -> Dict[str, Any]:
    """Download file from peer"""
    file_share = get_file_share()

    destination = Path(body.destination_path)

    downloaded_path = await file_share.download_file(
        file_id=body.file_id,
        peer_ip=body.peer_ip,
        peer_port=body.peer_port,
        destination=destination
    )

    return {
        "status": "completed",
        "file_path": str(downloaded_path)
    }


@router.get("/files/transfers")
@handle_exceptions("get active transfers")
async def get_active_transfers() -> Dict[str, Any]:
    """Get active file transfers"""
    file_share = get_file_share()
    transfers = file_share.get_active_transfers()

    return {
        "count": len(transfers),
        "transfers": [
            {
                "file_id": t.file_id,
                "filename": t.filename,
                "bytes_transferred": t.bytes_transferred,
                "total_bytes": t.total_bytes,
                "progress_percent": (t.bytes_transferred / t.total_bytes * 100) if t.total_bytes > 0 else 0,
                "speed_mbps": t.speed_mbps,
                "eta_seconds": t.eta_seconds,
                "status": t.status
            }
            for t in transfers
        ]
    }


@router.delete("/files/{file_id}")
@handle_exceptions("delete shared file", resource_type="File")
async def delete_shared_file(request: Request, file_id: str) -> Dict[str, str]:
    """Remove file from sharing"""
    file_share = get_file_share()

    success = await file_share.delete_shared_file(file_id)

    if not success:
        raise http_404("File not found", resource="file")

    return {"status": "deleted", "file_id": file_id}


@router.get("/files/stats")
@handle_exceptions("get file sharing stats")
async def get_file_sharing_stats() -> Dict[str, Any]:
    """Get file sharing statistics"""
    file_share = get_file_share()
    return file_share.get_stats()
