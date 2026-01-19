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

Follows MagnetarStudio API standards (see API_STANDARDS.md).
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
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.utils import get_user_id

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


def _save_metadata(transfer_id: str, metadata: Dict) -> None:
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


class UploadProgress(BaseModel):
    uploaded_chunks: int
    total_chunks: int
    percentage: float


class UploadChunkResponse(BaseModel):
    success: bool
    message: str
    resumed: bool
    progress: Optional[UploadProgress] = None


class CommitResponse(BaseModel):
    success: bool
    message: str
    filename: str
    final_path: str
    sha256: str
    size_bytes: int


class TransferStatusResponse(BaseModel):
    transfer_id: str
    filename: str
    size_bytes: int
    status: str
    chunk_size: int
    total_chunks: int
    uploaded_chunks: int
    missing_chunks: int
    progress_percentage: float
    next_missing_chunk: Optional[int]
    missing_chunk_indices: List[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]
    is_complete: bool


@router.post(
    "/init",
    response_model=SuccessResponse[InitResponse],
    status_code=status.HTTP_201_CREATED,
    name="p2p_init_transfer",
    summary="Initialize transfer",
    description="Initialize a new P2P file transfer with chunked upload support"
)
async def init_transfer(
    body: InitRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[InitResponse]:
    """
    Initialize a new transfer and allocate a temp directory

    Creates transfer ID, temp directory, and metadata file for tracking.

    Args:
        body: Transfer initialization request with filename and size

    Returns:
        Transfer ID and chunk size for upload
    """
    try:
        # Validate file size
        if body.size_bytes > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"File size exceeds maximum allowed ({MAX_FILE_SIZE / (1024**3):.1f} GB)"
                ).model_dump()
            )

        # Generate transfer ID
        transfer_id = secrets.token_urlsafe(16)

        # Create transfer directory
        transfer_dir = _get_transfer_dir(transfer_id)
        transfer_dir.mkdir(parents=True, exist_ok=True)

        # Calculate total chunks
        total_chunks = (body.size_bytes + CHUNK_SIZE - 1) // CHUNK_SIZE

        # Extract user_id from dict (get_current_user returns Dict, not User object)
        user_id = get_user_id(current_user)

        # Create metadata
        metadata = {
            "transfer_id": transfer_id,
            "filename": body.filename,
            "size_bytes": body.size_bytes,
            "mime_type": body.mime_type,
            "chunk_size": CHUNK_SIZE,
            "total_chunks": total_chunks,
            "uploaded_chunks": [],
            "user_id": user_id,
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
                "user_id": user_id
            }
        )

        return SuccessResponse(
            data=InitResponse(transfer_id=transfer_id, chunk_size=CHUNK_SIZE),
            message=f"Transfer initialized for '{body.filename}' ({total_chunks} chunks)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to initialize transfer", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to initialize transfer"
            ).model_dump()
        )


@router.post(
    "/upload-chunk",
    response_model=SuccessResponse[UploadChunkResponse],
    status_code=status.HTTP_200_OK,
    name="p2p_upload_chunk",
    summary="Upload chunk",
    description="Upload a single chunk with SHA-256 verification (supports resume)"
)
async def upload_chunk(
    transfer_id: str = Form(...),
    index: int = Form(...),
    checksum: str = Form(...),
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UploadChunkResponse]:
    """
    Upload a chunk for a given transfer

    Writes chunk to disk, verifies SHA-256 checksum, and updates metadata.
    Supports resume - if chunk already uploaded, returns success.

    Args:
        transfer_id: Transfer ID from init
        index: Chunk index (0-based)
        checksum: Expected SHA-256 hash of chunk data
        chunk: Chunk file data

    Returns:
        Upload progress and status
    """
    try:
        # Extract user_id from dict (get_current_user returns Dict, not User object)
        user_id = get_user_id(current_user)

        # Load metadata
        metadata = _load_metadata(transfer_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Transfer not found"
                ).model_dump()
            )

        # Verify ownership
        if metadata["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Transfer belongs to another user"
                ).model_dump()
            )

        # Validate chunk index
        if index < 0 or index >= metadata["total_chunks"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid chunk index (expected 0-{metadata['total_chunks']-1})"
                ).model_dump()
            )

        # Check if chunk already uploaded (resume support)
        if index in metadata["uploaded_chunks"]:
            logger.info(f"Chunk {index} already uploaded for transfer {transfer_id}")
            return SuccessResponse(
                data=UploadChunkResponse(
                    success=True,
                    message="Chunk already uploaded",
                    resumed=True,
                    progress=None
                ),
                message="Chunk already uploaded (resumed)"
            )

        # Write chunk to disk
        chunk_path = _get_transfer_dir(transfer_id) / f"chunk_{index:06d}"

        # Read and write chunk data
        chunk_data = await chunk.read()

        # Verify checksum
        actual_checksum = hashlib.sha256(chunk_data).hexdigest()
        if actual_checksum != checksum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Checksum mismatch (expected: {checksum}, got: {actual_checksum})"
                ).model_dump()
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

        progress = UploadProgress(
            uploaded_chunks=len(metadata["uploaded_chunks"]),
            total_chunks=metadata["total_chunks"],
            percentage=round((len(metadata["uploaded_chunks"]) / metadata["total_chunks"]) * 100, 2)
        )

        return SuccessResponse(
            data=UploadChunkResponse(
                success=True,
                message="Chunk uploaded successfully",
                resumed=False,
                progress=progress
            ),
            message=f"Chunk {index + 1}/{metadata['total_chunks']} uploaded ({progress.percentage}%)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Chunk upload failed for transfer {transfer_id}", exc_info=True)
        # Clean up partial chunk
        chunk_path = _get_transfer_dir(transfer_id) / f"chunk_{index:06d}"
        if chunk_path.exists():
            chunk_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Chunk upload failed"
            ).model_dump()
        )


class CommitRequest(BaseModel):
    transfer_id: str
    expected_sha256: Optional[str] = None


@router.post(
    "/commit",
    response_model=SuccessResponse[CommitResponse],
    status_code=status.HTTP_200_OK,
    name="p2p_commit_transfer",
    summary="Commit transfer",
    description="Finalize transfer by merging chunks and verifying integrity"
)
async def commit_transfer(
    body: CommitRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[CommitResponse]:
    """
    Commit a transfer: verify all chunks, merge, and compute final hash

    Merges all chunks into final file and verifies integrity.

    Args:
        body: CommitRequest with transfer_id and optional expected_sha256

    Returns:
        Final file path and SHA-256 hash
    """
    try:
        # Extract user_id from dict (get_current_user returns Dict, not User object)
        user_id = get_user_id(current_user)

        # Load metadata
        metadata = _load_metadata(body.transfer_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Transfer not found"
                ).model_dump()
            )

        # Verify ownership
        if metadata["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Transfer belongs to another user"
                ).model_dump()
            )

        # Verify all chunks uploaded
        if len(metadata["uploaded_chunks"]) != metadata["total_chunks"]:
            missing_chunks = set(range(metadata["total_chunks"])) - set(metadata["uploaded_chunks"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Transfer incomplete: {len(missing_chunks)} chunks missing"
                ).model_dump()
            )

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
                        detail=ErrorResponse(
                            error_code=ErrorCode.INTERNAL_ERROR,
                            message=f"Chunk {chunk_index} missing from disk"
                        ).model_dump()
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
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Final hash mismatch (expected: {body.expected_sha256}, got: {final_hash})"
                ).model_dump()
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
                "user_id": user_id
            }
        )

        # Clean up chunks (keep metadata for auditing)
        for chunk_index in range(metadata["total_chunks"]):
            chunk_path = transfer_dir / f"chunk_{chunk_index:06d}"
            if chunk_path.exists():
                chunk_path.unlink()

        return SuccessResponse(
            data=CommitResponse(
                success=True,
                message="Transfer completed successfully",
                filename=metadata["filename"],
                final_path=str(final_file_path),
                sha256=final_hash,
                size_bytes=metadata["size_bytes"]
            ),
            message=f"Transfer completed: {metadata['filename']} ({metadata['size_bytes']} bytes)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Transfer commit failed for {body.transfer_id}", exc_info=True)
        # Update metadata to failed status
        try:
            metadata = _load_metadata(body.transfer_id)
            if metadata:
                metadata["status"] = "failed"
                metadata["error"] = str(e)
                metadata["failed_at"] = datetime.now().isoformat()
                _save_metadata(body.transfer_id, metadata)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Transfer commit failed"
            ).model_dump()
        )


@router.get(
    "/status/{transfer_id}",
    response_model=SuccessResponse[TransferStatusResponse],
    status_code=status.HTTP_200_OK,
    name="p2p_get_transfer_status",
    summary="Get transfer status",
    description="Get transfer progress, uploaded/missing chunks, and completion status"
)
async def get_status(
    transfer_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[TransferStatusResponse]:
    """
    Return transfer status and missing chunks list

    Returns current transfer progress, uploaded chunks, and next missing chunks.

    Args:
        transfer_id: Transfer ID from init

    Returns:
        Transfer status with progress and missing chunks
    """
    try:
        # Extract user_id from dict (get_current_user returns Dict, not User object)
        user_id = get_user_id(current_user)

        # Load metadata
        metadata = _load_metadata(transfer_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Transfer not found"
                ).model_dump()
            )

        # Verify ownership
        if metadata["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Transfer belongs to another user"
                ).model_dump()
            )

        # Calculate missing chunks
        all_chunks = set(range(metadata["total_chunks"]))
        uploaded_chunks = set(metadata["uploaded_chunks"])
        missing_chunks = sorted(list(all_chunks - uploaded_chunks))

        # Get next missing chunk (for sequential upload)
        next_missing_chunk = missing_chunks[0] if missing_chunks else None

        # Calculate progress
        progress_percentage = round((len(uploaded_chunks) / metadata["total_chunks"]) * 100, 2) if metadata["total_chunks"] > 0 else 100.0

        status_data = TransferStatusResponse(
            transfer_id=transfer_id,
            filename=metadata["filename"],
            size_bytes=metadata["size_bytes"],
            status=metadata["status"],
            chunk_size=metadata["chunk_size"],
            total_chunks=metadata["total_chunks"],
            uploaded_chunks=len(uploaded_chunks),
            missing_chunks=len(missing_chunks),
            progress_percentage=progress_percentage,
            next_missing_chunk=next_missing_chunk,
            missing_chunk_indices=missing_chunks[:10],  # First 10 missing chunks
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("updated_at"),
            completed_at=metadata.get("completed_at"),
            is_complete=len(missing_chunks) == 0
        )

        return SuccessResponse(
            data=status_data,
            message=f"Transfer {progress_percentage}% complete ({len(uploaded_chunks)}/{metadata['total_chunks']} chunks)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get transfer status for {transfer_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve transfer status"
            ).model_dump()
        )

