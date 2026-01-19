"""
Cloud Storage - File Management Routes

List and delete cloud files.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_middleware import get_current_user
from api.routes.schemas import SuccessResponse
from api.errors import http_403, http_404
from api.utils import get_user_id

from api.routes.cloud_storage.models import FileListResponse
from api.routes.cloud_storage.helpers import (
    get_s3_service,
    get_cloud_files_dir,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/files", response_model=FileListResponse)
async def list_files(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
) -> FileListResponse:
    """List user's cloud files."""
    cloud_files_dir = get_cloud_files_dir()

    files: List[Dict[str, Any]] = []
    if cloud_files_dir.exists():
        for meta_file in cloud_files_dir.glob("csf_*.json"):
            if not meta_file.name.startswith("download_"):
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    if metadata.get("user_id") == get_user_id(current_user):
                        files.append({
                            "file_id": metadata["file_id"],
                            "filename": metadata["filename"],
                            "size_bytes": metadata["size_bytes"],
                            "content_type": metadata["content_type"],
                            "storage_class": metadata["storage_class"],
                            "storage_backend": metadata.get("storage_backend", "local"),
                            "uploaded_at": metadata["uploaded_at"]
                        })

    # Sort by upload date, newest first
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)
    total = len(files)

    return FileListResponse(
        files=files[offset:offset + limit],
        total=total
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a cloud file."""
    cloud_files_dir = get_cloud_files_dir()
    file_meta_path = cloud_files_dir / f"{file_id}.json"

    if not file_meta_path.exists():
        raise http_404("File not found", resource="file")

    with open(file_meta_path, 'r') as f:
        file_metadata = json.load(f)

    # Verify ownership
    if file_metadata["user_id"] != get_user_id(current_user):
        raise http_403("Not authorized to delete this file")

    # Delete from S3 if applicable
    if file_metadata.get("storage_backend") == "s3" and file_metadata.get("s3_key"):
        s3_service = get_s3_service()
        if s3_service:
            try:
                s3_service.delete_file(file_metadata["s3_key"])
                logger.info(f"Deleted from S3: {file_metadata['s3_key']}")
            except Exception as e:
                logger.error(f"Failed to delete from S3 (continuing with local cleanup): {e}")

    # Delete local file and metadata
    file_path = cloud_files_dir / file_id
    if file_path.exists():
        file_path.unlink()
    file_meta_path.unlink()

    logger.info(f"Deleted cloud file {file_id}")

    return SuccessResponse(data={"file_id": file_id, "deleted": True}, message="File deleted successfully")
