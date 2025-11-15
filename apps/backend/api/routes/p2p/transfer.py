"""
P2P Chunked File Transfer Endpoints.

Provides resumable file transfer between P2P peers:
- Chunked upload (4-8 MB chunks)
- Per-chunk SHA-256 verification
- Resume capability (track uploaded chunks)
- Final integrity verification

Endpoints:
- POST /api/v1/p2p/transfer/init - Initialize transfer
- POST /api/v1/p2p/transfer/upload-chunk - Upload single chunk
- POST /api/v1/p2p/transfer/commit - Finalize transfer
- GET  /api/v1/p2p/transfer/status/{transfer_id} - Get progress

Notes:
- Temp chunks stored under PATHS.shared_files_dir / "temp" / {transfer_id}
- Metadata stored in {transfer_id}/metadata.json
- All endpoints require authentication
"""

from __future__ import annotations

import json
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user, User
from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)
PATHS = get_config_paths()


router = APIRouter(prefix="/api/v1/p2p/transfer", tags=["p2p-transfer"], dependencies=[Depends(get_current_user)])

# Configuration
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB limit
TEMP_DIR = PATHS.cache_dir / "p2p_transfers"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ===== Helper Functions =====

def _get_transfer_dir(transfer_id: str) -> Path:
    """Get transfer directory path"""
    return TEMP_DIR / transfer_id


def _get_metadata_path(transfer_id: str) -> Path:
    """Get metadata JSON path"""
    return _get_transfer_dir(transfer_id) / "metadata.json"


def _load_metadata(transfer_id: str) -> Optional[Dict]:
    """Load transfer metadata"""
    metadata_path = _get_metadata_path(transfer_id)
    if not metadata_path.exists():
        return None

    with open(metadata_path, 'r') as f:
        return json.load(f)


def _save_metadata(transfer_id: str, metadata: Dict):
    """Save transfer metadata"""
    metadata_path = _get_metadata_path(transfer_id)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


# ===== Request/Response Models =====

class InitRequest(BaseModel):
    filename: str
    size_bytes: int = Field(ge=0)
    mime_type: Optional[str] = None


class InitResponse(BaseModel):
    transfer_id: str
    chunk_size: int


@router.post("/init", response_model=InitResponse)
async def init_transfer(
    body: InitRequest,
    current_user: User = Depends(get_current_user)
):
    """Initialize a new transfer and allocate a temp directory.

    Creates transfer ID, temp directory, and metadata file for tracking.

    Returns:
        InitResponse with transfer_id and chunk_size
    """
    # Validate file size
    if body.size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed ({MAX_FILE_SIZE / (1024**3):.1f} GB)"
        )

    # Generate transfer ID
    transfer_id = secrets.token_urlsafe(16)

    # Create transfer directory
    transfer_dir = _get_transfer_dir(transfer_id)
    transfer_dir.mkdir(parents=True, exist_ok=True)

    # Calculate total chunks
    total_chunks = (body.size_bytes + CHUNK_SIZE - 1) // CHUNK_SIZE

    # Create metadata
    metadata = {
        "transfer_id": transfer_id,
        "filename": body.filename,
        "size_bytes": body.size_bytes,
        "mime_type": body.mime_type,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "uploaded_chunks": [],
        "user_id": current_user.user_id,
        "created_at": datetime.now().isoformat(),
        "status": "initialized"
    }

    _save_metadata(transfer_id, metadata)

    logger.info(
        f"Transfer initialized: {transfer_id}",
        extra={
            "transfer_id": transfer_id,
            "filename": body.filename,
            "size_bytes": body.size_bytes,
            "total_chunks": total_chunks,
            "user_id": current_user.user_id
        }
    )

    return InitResponse(transfer_id=transfer_id, chunk_size=CHUNK_SIZE)


@router.post("/upload-chunk")
async def upload_chunk(
    transfer_id: str = Form(...),
    index: int = Form(...),
    checksum: str = Form(...),
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a chunk for a given transfer.

    Writes chunk to disk, verifies SHA-256 checksum, and updates metadata.
    Supports resume - if chunk already uploaded, returns success.

    Args:
        transfer_id: Transfer ID from init
        index: Chunk index (0-based)
        checksum: Expected SHA-256 hash of chunk data
        chunk: Chunk file data

    Returns:
        JSON with success status
    """
    # Load metadata
    metadata = _load_metadata(transfer_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify ownership
    if metadata["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transfer belongs to another user"
        )

    # Validate chunk index
    if index < 0 or index >= metadata["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chunk index (expected 0-{metadata['total_chunks']-1})"
        )

    # Check if chunk already uploaded (resume support)
    if index in metadata["uploaded_chunks"]:
        logger.info(f"Chunk {index} already uploaded for transfer {transfer_id}")
        return {"success": True, "message": "Chunk already uploaded", "resumed": True}

    # Write chunk to disk
    chunk_path = _get_transfer_dir(transfer_id) / f"chunk_{index:06d}"

    try:
        # Read and write chunk data
        chunk_data = await chunk.read()

        # Verify checksum
        actual_checksum = hashlib.sha256(chunk_data).hexdigest()
        if actual_checksum != checksum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Checksum mismatch (expected: {checksum}, got: {actual_checksum})"
            )

        # Write to disk
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        # Update metadata
        metadata["uploaded_chunks"].append(index)
        metadata["uploaded_chunks"].sort()
        metadata["status"] = "uploading"
        metadata["updated_at"] = datetime.now().isoformat()
        _save_metadata(transfer_id, metadata)

        logger.info(
            f"Chunk uploaded: transfer={transfer_id}, index={index}, size={len(chunk_data)}",
            extra={
                "transfer_id": transfer_id,
                "chunk_index": index,
                "chunk_size": len(chunk_data),
                "progress": f"{len(metadata['uploaded_chunks'])}/{metadata['total_chunks']}"
            }
        )

        return {
            "success": True,
            "message": "Chunk uploaded successfully",
            "resumed": False,
            "progress": {
                "uploaded_chunks": len(metadata["uploaded_chunks"]),
                "total_chunks": metadata["total_chunks"],
                "percentage": round((len(metadata["uploaded_chunks"]) / metadata["total_chunks"]) * 100, 2)
            }
        }

    except Exception as e:
        logger.error(f"Chunk upload failed: {e}", exc_info=True)
        # Clean up partial chunk
        if chunk_path.exists():
            chunk_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunk upload failed: {str(e)}"
        )


class CommitRequest(BaseModel):
    transfer_id: str
    expected_sha256: Optional[str] = None


@router.post("/commit")
async def commit_transfer(
    body: CommitRequest,
    current_user: User = Depends(get_current_user)
):
    """Commit a transfer: verify all chunks, merge, and compute final hash.

    Merges all chunks into final file and verifies integrity.

    Args:
        body: CommitRequest with transfer_id and optional expected_sha256

    Returns:
        JSON with success status, final file path, and SHA-256 hash
    """
    # Load metadata
    metadata = _load_metadata(body.transfer_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify ownership
    if metadata["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transfer belongs to another user"
        )

    # Verify all chunks uploaded
    if len(metadata["uploaded_chunks"]) != metadata["total_chunks"]:
        missing_chunks = set(range(metadata["total_chunks"])) - set(metadata["uploaded_chunks"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer incomplete: {len(missing_chunks)} chunks missing"
        )

    try:
        # Merge chunks into final file
        transfer_dir = _get_transfer_dir(body.transfer_id)
        final_file_path = PATHS.data_dir / "shared_files" / metadata["filename"]
        final_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write merged file
        with open(final_file_path, 'wb') as output:
            for chunk_index in range(metadata["total_chunks"]):
                chunk_path = transfer_dir / f"chunk_{chunk_index:06d}"

                if not chunk_path.exists():
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Chunk {chunk_index} missing from disk"
                    )

                with open(chunk_path, 'rb') as chunk_file:
                    output.write(chunk_file.read())

        # Compute final file hash
        final_hash = _compute_file_hash(final_file_path)

        # Verify expected hash if provided
        if body.expected_sha256 and final_hash != body.expected_sha256:
            # Clean up invalid file
            final_file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Final hash mismatch (expected: {body.expected_sha256}, got: {final_hash})"
            )

        # Update metadata
        metadata["status"] = "completed"
        metadata["completed_at"] = datetime.now().isoformat()
        metadata["final_path"] = str(final_file_path)
        metadata["final_sha256"] = final_hash
        _save_metadata(body.transfer_id, metadata)

        logger.info(
            f"Transfer completed: {body.transfer_id}",
            extra={
                "transfer_id": body.transfer_id,
                "filename": metadata["filename"],
                "size_bytes": metadata["size_bytes"],
                "final_hash": final_hash,
                "user_id": current_user.user_id
            }
        )

        # Clean up chunks (keep metadata for auditing)
        for chunk_index in range(metadata["total_chunks"]):
            chunk_path = transfer_dir / f"chunk_{chunk_index:06d}"
            if chunk_path.exists():
                chunk_path.unlink()

        return {
            "success": True,
            "message": "Transfer completed successfully",
            "filename": metadata["filename"],
            "final_path": str(final_file_path),
            "sha256": final_hash,
            "size_bytes": metadata["size_bytes"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transfer commit failed: {e}", exc_info=True)
        # Update metadata to failed status
        metadata["status"] = "failed"
        metadata["error"] = str(e)
        metadata["failed_at"] = datetime.now().isoformat()
        _save_metadata(body.transfer_id, metadata)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer commit failed: {str(e)}"
        )


@router.get("/status/{transfer_id}")
async def get_status(
    transfer_id: str,
    current_user: User = Depends(get_current_user)
):
    """Return transfer status and missing chunks list.

    Returns current transfer progress, uploaded chunks, and next missing chunks.

    Args:
        transfer_id: Transfer ID from init

    Returns:
        JSON with transfer status, progress, uploaded/missing chunks
    """
    # Load metadata
    metadata = _load_metadata(transfer_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify ownership
    if metadata["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transfer belongs to another user"
        )

    # Calculate missing chunks
    all_chunks = set(range(metadata["total_chunks"]))
    uploaded_chunks = set(metadata["uploaded_chunks"])
    missing_chunks = sorted(list(all_chunks - uploaded_chunks))

    # Get next missing chunk (for sequential upload)
    next_missing_chunk = missing_chunks[0] if missing_chunks else None

    # Calculate progress
    progress_percentage = round((len(uploaded_chunks) / metadata["total_chunks"]) * 100, 2) if metadata["total_chunks"] > 0 else 100.0

    return {
        "transfer_id": transfer_id,
        "filename": metadata["filename"],
        "size_bytes": metadata["size_bytes"],
        "status": metadata["status"],
        "chunk_size": metadata["chunk_size"],
        "total_chunks": metadata["total_chunks"],
        "uploaded_chunks": len(uploaded_chunks),
        "missing_chunks": len(missing_chunks),
        "progress_percentage": progress_percentage,
        "next_missing_chunk": next_missing_chunk,
        "missing_chunk_indices": missing_chunks[:10],  # First 10 missing chunks
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "completed_at": metadata.get("completed_at"),
        "is_complete": len(missing_chunks) == 0
    }

