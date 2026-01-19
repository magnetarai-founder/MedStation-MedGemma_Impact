"""
Cloud Storage - Upload Routes

Chunked upload endpoints with SHA-256 verification.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

from api.auth_middleware import get_current_user
from api.errors import http_400, http_403, http_404, http_500
from api.utils import file_lock, get_user_id

from api.routes.cloud_storage.models import (
    CHUNK_SIZE,
    UPLOAD_EXPIRY_HOURS,
    UploadStatus,
    InitUploadRequest,
    InitUploadResponse,
    ChunkUploadResponse,
    UploadStatusResponse,
    CommitUploadResponse,
    StorageClass,
)
from api.routes.cloud_storage.helpers import (
    get_s3_service,
    get_upload_dir,
    load_metadata,
    save_metadata,
    compute_chunk_hash,
    compute_file_hash,
    generate_upload_id,
    generate_file_id,
    get_cloud_files_dir,
    PATHS,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload/init", response_model=InitUploadResponse)
async def init_upload(
    request: InitUploadRequest,
    current_user: dict = Depends(get_current_user)
) -> InitUploadResponse:
    """
    Initialize a chunked upload session.

    Returns upload_id and chunk configuration. Client should then
    upload chunks sequentially using /upload/chunk endpoint.
    """
    upload_id = generate_upload_id()
    upload_dir = get_upload_dir(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    total_chunks = (request.size_bytes + CHUNK_SIZE - 1) // CHUNK_SIZE
    expires_at = datetime.now(UTC) + timedelta(hours=UPLOAD_EXPIRY_HOURS)

    metadata = {
        "upload_id": upload_id,
        "user_id": get_user_id(current_user),
        "filename": request.filename,
        "size_bytes": request.size_bytes,
        "content_type": request.content_type,
        "storage_class": request.storage_class.value,
        "encrypt": request.encrypt,
        "custom_metadata": request.metadata or {},
        "total_chunks": total_chunks,
        "uploaded_chunks": [],
        "chunk_hashes": {},
        "status": UploadStatus.PENDING.value,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expires_at.isoformat()
    }

    save_metadata(upload_id, metadata)

    logger.info(f"Initialized cloud upload {upload_id} for {request.filename} ({request.size_bytes} bytes)")

    return InitUploadResponse(
        upload_id=upload_id,
        chunk_size=CHUNK_SIZE,
        total_chunks=total_chunks,
        expires_at=expires_at.isoformat(),
        storage_class=request.storage_class
    )


@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(..., ge=0, le=10000),  # SECURITY: Upper bound prevents DoS
    chunk_hash: str = Form(..., min_length=64, max_length=64),
    chunk_data: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
) -> ChunkUploadResponse:
    """
    Upload a single chunk of a file.

    Client provides SHA-256 hash for verification. Server verifies
    hash matches received data.
    """
    metadata = load_metadata(upload_id)
    if not metadata:
        raise http_404("Upload session not found or expired", resource="upload")

    # Verify ownership
    if metadata["user_id"] != get_user_id(current_user):
        raise http_403("Not authorized for this upload")

    # Check expiry
    expires_at = datetime.fromisoformat(metadata["expires_at"])
    if datetime.now(UTC) > expires_at:
        metadata["status"] = UploadStatus.EXPIRED.value
        save_metadata(upload_id, metadata)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "upload_expired", "message": "Upload session has expired"}
        )

    # Validate chunk index
    if chunk_index >= metadata["total_chunks"]:
        raise http_400(f"Chunk index {chunk_index} exceeds total chunks")

    # Read and verify chunk
    chunk_bytes = await chunk_data.read()
    computed_hash = compute_chunk_hash(chunk_bytes)

    if computed_hash != chunk_hash.lower():
        raise http_400(f"Chunk hash verification failed: expected {chunk_hash.lower()}, got {computed_hash}")

    # SECURITY: Use file lock to prevent TOCTOU race conditions
    # This ensures concurrent chunk uploads don't corrupt the upload state
    upload_dir = get_upload_dir(upload_id)
    with file_lock(upload_dir, ".upload.lock"):
        # Re-load metadata inside lock to get latest state
        metadata = load_metadata(upload_id)
        if not metadata:
            raise http_404("Upload session not found", resource="upload")

        # Save chunk
        chunk_path = upload_dir / f"chunk_{chunk_index:06d}"
        with open(chunk_path, 'wb') as f:
            f.write(chunk_bytes)

        # Update metadata
        if chunk_index not in metadata["uploaded_chunks"]:
            metadata["uploaded_chunks"].append(chunk_index)
        metadata["chunk_hashes"][str(chunk_index)] = computed_hash
        metadata["status"] = UploadStatus.UPLOADING.value
        save_metadata(upload_id, metadata)

    chunks_uploaded = len(metadata["uploaded_chunks"])
    total_chunks = metadata["total_chunks"]
    progress = (chunks_uploaded / total_chunks) * 100

    logger.debug(f"Upload {upload_id}: chunk {chunk_index}/{total_chunks} ({progress:.1f}%)")

    return ChunkUploadResponse(
        chunk_index=chunk_index,
        chunk_hash=computed_hash,
        verified=True,
        chunks_uploaded=chunks_uploaded,
        total_chunks=total_chunks,
        progress_percent=round(progress, 2)
    )


@router.post("/upload/commit", response_model=CommitUploadResponse)
async def commit_upload(
    upload_id: str = Form(...),
    final_hash: str = Form(..., min_length=64, max_length=64),
    current_user: dict = Depends(get_current_user)
) -> CommitUploadResponse:
    """
    Finalize upload after all chunks are uploaded.

    Assembles chunks, verifies final hash, encrypts if requested,
    and uploads to cloud storage.
    """
    import json

    metadata = load_metadata(upload_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "upload_not_found", "message": "Upload session not found"}
        )

    # Verify ownership
    if metadata["user_id"] != get_user_id(current_user):
        raise http_403("Not authorized for this upload")

    # Verify all chunks uploaded
    uploaded = set(metadata["uploaded_chunks"])
    expected = set(range(metadata["total_chunks"]))
    missing = expected - uploaded

    if missing:
        raise http_400(f"Missing chunks: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")

    # SECURITY: Use file lock to prevent concurrent commit attempts
    upload_dir = get_upload_dir(upload_id)

    with file_lock(upload_dir, ".upload.lock"):
        # Re-load metadata inside lock
        metadata = load_metadata(upload_id)
        if not metadata:
            raise http_404("Upload session not found", resource="upload")

        # Check if already committed
        if metadata["status"] == UploadStatus.COMPLETED.value:
            raise http_400("Upload already committed")

        metadata["status"] = UploadStatus.PROCESSING.value
        save_metadata(upload_id, metadata)

        # Assemble chunks
        assembled_path = upload_dir / "assembled"

        try:
            with open(assembled_path, 'wb') as outfile:
                for i in range(metadata["total_chunks"]):
                    chunk_path = upload_dir / f"chunk_{i:06d}"
                    with open(chunk_path, 'rb') as chunk_file:
                        outfile.write(chunk_file.read())

            # Verify final hash
            computed_hash = compute_file_hash(assembled_path)
            if computed_hash != final_hash.lower():
                raise http_400(f"Final file hash verification failed: expected {final_hash.lower()}, got {computed_hash}")

            file_id = generate_file_id()
            cloud_files_dir = get_cloud_files_dir()

            # Check if S3 storage is enabled
            s3_service = get_s3_service()
            s3_key = None
            s3_result = None

            if s3_service:
                # Upload to S3
                s3_key = f"uploads/{metadata['user_id']}/{file_id}/{metadata['filename']}"

                try:
                    s3_result = s3_service.upload_file(
                        file_path=assembled_path,
                        s3_key=s3_key,
                        content_type=metadata["content_type"],
                        storage_class=metadata["storage_class"],
                        metadata={
                            "original_filename": metadata["filename"],
                            "user_id": metadata["user_id"],
                            "file_id": file_id,
                        },
                        encrypt=metadata["encrypt"]
                    )
                    logger.info(f"Uploaded to S3: {s3_key}")

                    # Remove local assembled file after S3 upload
                    assembled_path.unlink()

                except Exception as e:
                    logger.error(f"S3 upload failed, falling back to local: {e}")
                    s3_service = None  # Fall back to local storage

            if not s3_service:
                # Store locally (fallback or when S3 disabled)
                final_path = cloud_files_dir / file_id
                assembled_path.rename(final_path)

            # Store file metadata
            file_metadata = {
                "file_id": file_id,
                "filename": metadata["filename"],
                "size_bytes": metadata["size_bytes"],
                "content_type": metadata["content_type"],
                "storage_class": metadata["storage_class"],
                "sha256": computed_hash,
                "user_id": metadata["user_id"],
                "custom_metadata": metadata["custom_metadata"],
                "encrypted": metadata["encrypt"],
                "uploaded_at": datetime.now(UTC).isoformat(),
                # S3-specific fields
                "storage_backend": "s3" if s3_result else "local",
                "s3_key": s3_key,
                "s3_bucket": s3_result.get("bucket") if s3_result else None,
                "s3_etag": s3_result.get("etag") if s3_result else None,
                "s3_version_id": s3_result.get("version_id") if s3_result else None,
            }

            file_meta_path = cloud_files_dir / f"{file_id}.json"
            with open(file_meta_path, 'w') as f:
                json.dump(file_metadata, f, indent=2)

            # Update upload metadata
            metadata["status"] = UploadStatus.COMPLETED.value
            metadata["file_id"] = file_id
            save_metadata(upload_id, metadata)

            # Cleanup chunk files
            for i in range(metadata["total_chunks"]):
                chunk_path = upload_dir / f"chunk_{i:06d}"
                if chunk_path.exists():
                    chunk_path.unlink()

            logger.info(f"Cloud upload {upload_id} completed: {file_id}")

            return CommitUploadResponse(
                file_id=file_id,
                filename=metadata["filename"],
                size_bytes=metadata["size_bytes"],
                content_type=metadata["content_type"],
                storage_class=StorageClass(metadata["storage_class"]),
                sha256=computed_hash,
                uploaded_at=datetime.now(UTC).isoformat()
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to commit upload {upload_id}: {e}")
            metadata["status"] = UploadStatus.FAILED.value
            save_metadata(upload_id, metadata)
            raise http_500(f"Upload commit failed: {str(e)}")


@router.get("/upload/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    current_user: dict = Depends(get_current_user)
) -> UploadStatusResponse:
    """Get current status of an upload session."""
    metadata = load_metadata(upload_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "upload_not_found", "message": "Upload session not found"}
        )

    # Verify ownership
    if metadata["user_id"] != get_user_id(current_user):
        raise http_403("Not authorized for this upload")

    chunks_uploaded = len(metadata["uploaded_chunks"])
    total_chunks = metadata["total_chunks"]
    progress = (chunks_uploaded / total_chunks) * 100 if total_chunks > 0 else 0

    return UploadStatusResponse(
        upload_id=upload_id,
        status=UploadStatus(metadata["status"]),
        filename=metadata["filename"],
        size_bytes=metadata["size_bytes"],
        chunks_uploaded=chunks_uploaded,
        total_chunks=total_chunks,
        progress_percent=round(progress, 2),
        created_at=metadata["created_at"],
        expires_at=metadata["expires_at"],
        file_id=metadata.get("file_id")
    )
