"""
Cloud Storage - Download Routes

Presigned URL generation and file download endpoints.
"""

from __future__ import annotations

import json
import secrets
import logging
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_middleware import get_current_user
from api.errors import http_400, http_401, http_403, http_404
from api.utils import get_user_id

from api.routes.cloud_storage.models import (
    InitDownloadRequest,
    InitDownloadResponse,
)
from api.routes.cloud_storage.helpers import (
    get_s3_service,
    get_cloud_files_dir,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/download/init", response_model=InitDownloadResponse)
async def init_download(
    request: InitDownloadRequest,
    current_user: dict = Depends(get_current_user)
) -> InitDownloadResponse:
    """
    Initialize download for a cloud file.

    Returns presigned download URL valid for specified duration.
    """
    cloud_files_dir = get_cloud_files_dir()
    file_meta_path = cloud_files_dir / f"{request.file_id}.json"

    if not file_meta_path.exists():
        raise http_404("File not found", resource="file")

    with open(file_meta_path, 'r') as f:
        file_metadata = json.load(f)

    # Verify ownership (or implement sharing logic)
    if file_metadata["user_id"] != get_user_id(current_user):
        raise http_403("Not authorized to access this file")

    expires_at = datetime.now(UTC) + timedelta(minutes=request.expires_minutes)
    expires_seconds = request.expires_minutes * 60

    # Check if file is stored in S3
    if file_metadata.get("storage_backend") == "s3" and file_metadata.get("s3_key"):
        s3_service = get_s3_service()
        if s3_service:
            try:
                # Generate S3 presigned URL
                download_url = s3_service.generate_presigned_url(
                    s3_key=file_metadata["s3_key"],
                    expires_in=expires_seconds,
                    response_content_type=file_metadata.get("content_type"),
                    response_content_disposition=f'attachment; filename="{file_metadata["filename"]}"'
                )

                logger.info(f"Generated S3 presigned URL for {file_metadata['s3_key']}")

                return InitDownloadResponse(
                    file_id=request.file_id,
                    filename=file_metadata["filename"],
                    size_bytes=file_metadata["size_bytes"],
                    content_type=file_metadata["content_type"],
                    download_url=download_url,
                    expires_at=expires_at.isoformat()
                )

            except Exception as e:
                logger.error(f"Failed to generate S3 presigned URL: {e}")
                # Fall through to local download

    # Local storage: create download token
    download_token = secrets.token_urlsafe(32)

    # Store download token with expiry
    download_meta = {
        "file_id": request.file_id,
        "user_id": get_user_id(current_user),
        "expires_at": expires_at.isoformat()
    }
    download_token_path = cloud_files_dir / f"download_{download_token}.json"
    with open(download_token_path, 'w') as f:
        json.dump(download_meta, f)

    download_url = f"/api/v1/cloud/storage/download/{request.file_id}?token={download_token}"

    return InitDownloadResponse(
        file_id=request.file_id,
        filename=file_metadata["filename"],
        size_bytes=file_metadata["size_bytes"],
        content_type=file_metadata["content_type"],
        download_url=download_url,
        expires_at=expires_at.isoformat()
    )


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    token: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Download a cloud file.

    Requires valid download token from /download/init.
    """
    from fastapi.responses import FileResponse

    cloud_files_dir = get_cloud_files_dir()

    # Validate token
    download_token_path = cloud_files_dir / f"download_{token}.json"
    if not download_token_path.exists():
        raise http_401("Invalid or expired download token")

    with open(download_token_path, 'r') as f:
        download_meta = json.load(f)

    # Check expiry
    expires_at = datetime.fromisoformat(download_meta["expires_at"])
    if datetime.now(UTC) > expires_at:
        download_token_path.unlink()  # Cleanup expired token
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "token_expired", "message": "Download token has expired"}
        )

    # Verify file ID matches
    if download_meta["file_id"] != file_id:
        raise http_400("Token does not match file")

    # Get file metadata
    file_meta_path = cloud_files_dir / f"{file_id}.json"
    if not file_meta_path.exists():
        raise http_404("File not found", resource="file")

    with open(file_meta_path, 'r') as f:
        file_metadata = json.load(f)

    file_path = cloud_files_dir / file_id
    if not file_path.exists():
        raise http_404("File data not found", resource="file")

    # Cleanup token (single use)
    download_token_path.unlink()

    return FileResponse(
        path=str(file_path),
        filename=file_metadata["filename"],
        media_type=file_metadata["content_type"]
    )
