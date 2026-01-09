"""
Cloud Storage Package

Chunked file upload/download for MagnetarCloud.

Components:
- models.py: Pydantic models and enums
- helpers.py: Utility functions
- upload_routes.py: Chunked upload endpoints
- download_routes.py: Download and presigned URL endpoints
- files_routes.py: File listing and deletion

Security:
- All endpoints require authentication
- Files encrypted before cloud upload (AES-256-GCM)
- Chunk hashes verified on both client and server
- Air-gap mode blocks all cloud operations (503)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_middleware import get_current_user
from api.config import is_airgap_mode

# Import sub-routers
from api.routes.cloud_storage.upload_routes import router as upload_router
from api.routes.cloud_storage.download_routes import router as download_router
from api.routes.cloud_storage.files_routes import router as files_router

# Import models for re-export
from api.routes.cloud_storage.models import (
    CHUNK_SIZE,
    MAX_FILE_SIZE,
    UPLOAD_EXPIRY_HOURS,
    UploadStatus,
    StorageClass,
    InitUploadRequest,
    InitUploadResponse,
    ChunkUploadResponse,
    UploadStatusResponse,
    CommitUploadResponse,
    InitDownloadRequest,
    InitDownloadResponse,
    FileListResponse,
)

# Import helpers for re-export
from api.routes.cloud_storage.helpers import (
    get_s3_service,
    get_upload_dir,
    get_metadata_path,
    load_metadata,
    save_metadata,
    compute_chunk_hash,
    compute_file_hash,
    generate_upload_id,
    generate_file_id,
    get_cloud_files_dir,
    TEMP_DIR,
    PATHS,
)

# Import endpoint functions for re-export
from api.routes.cloud_storage.upload_routes import (
    init_upload,
    upload_chunk,
    commit_upload,
    get_upload_status,
)
from api.routes.cloud_storage.download_routes import (
    init_download,
    download_file,
)
from api.routes.cloud_storage.files_routes import (
    list_files,
    delete_file,
)


# Dependency to check cloud availability
async def check_cloud_available():
    """Block cloud operations in air-gap mode."""
    if is_airgap_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "cloud_unavailable",
                "message": "Cloud storage is disabled in air-gap mode",
                "code": "AIRGAP_MODE_ENABLED"
            }
        )


# Create main router that includes all sub-routers
router = APIRouter(
    prefix="/api/v1/cloud/storage",
    tags=["cloud-storage"],
    dependencies=[Depends(get_current_user), Depends(check_cloud_available)]
)
router.include_router(upload_router)
router.include_router(download_router)
router.include_router(files_router)


__all__ = [
    # Main router
    "router",
    # Dependency
    "check_cloud_available",
    # Constants
    "CHUNK_SIZE",
    "MAX_FILE_SIZE",
    "UPLOAD_EXPIRY_HOURS",
    "TEMP_DIR",
    "PATHS",
    # Enums
    "UploadStatus",
    "StorageClass",
    # Models
    "InitUploadRequest",
    "InitUploadResponse",
    "ChunkUploadResponse",
    "UploadStatusResponse",
    "CommitUploadResponse",
    "InitDownloadRequest",
    "InitDownloadResponse",
    "FileListResponse",
    # Helpers
    "get_s3_service",
    "get_upload_dir",
    "get_metadata_path",
    "load_metadata",
    "save_metadata",
    "compute_chunk_hash",
    "compute_file_hash",
    "generate_upload_id",
    "generate_file_id",
    "get_cloud_files_dir",
    # Upload endpoints
    "init_upload",
    "upload_chunk",
    "commit_upload",
    "get_upload_status",
    # Download endpoints
    "init_download",
    "download_file",
    # File management endpoints
    "list_files",
    "delete_file",
]
