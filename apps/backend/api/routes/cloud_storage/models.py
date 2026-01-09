"""
Cloud Storage - Models

Enums and Pydantic models for cloud storage operations.
"""

from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


# Configuration constants
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB limit for cloud
UPLOAD_EXPIRY_HOURS = 24


class UploadStatus(str, Enum):
    """Upload status states."""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class StorageClass(str, Enum):
    """Cloud storage classes."""
    STANDARD = "standard"
    ARCHIVE = "archive"
    COLD = "cold"


# ===== Upload Models =====

class InitUploadRequest(BaseModel):
    """Request to initialize a chunked upload."""
    filename: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1, le=MAX_FILE_SIZE)
    content_type: str = Field(default="application/octet-stream")
    storage_class: StorageClass = Field(default=StorageClass.STANDARD)
    encrypt: bool = Field(default=True, description="Encrypt file before cloud upload")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Custom metadata")


class InitUploadResponse(BaseModel):
    """Response with upload session details."""
    upload_id: str
    chunk_size: int
    total_chunks: int
    expires_at: str
    storage_class: StorageClass


class ChunkUploadResponse(BaseModel):
    """Response after chunk upload."""
    chunk_index: int
    chunk_hash: str
    verified: bool
    chunks_uploaded: int
    total_chunks: int
    progress_percent: float


class UploadStatusResponse(BaseModel):
    """Current upload status."""
    upload_id: str
    status: UploadStatus
    filename: str
    size_bytes: int
    chunks_uploaded: int
    total_chunks: int
    progress_percent: float
    created_at: str
    expires_at: str
    file_id: Optional[str] = None


class CommitUploadResponse(BaseModel):
    """Response after successful upload commit."""
    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    storage_class: StorageClass
    sha256: str
    uploaded_at: str
    download_url: Optional[str] = None


# ===== Download Models =====

class InitDownloadRequest(BaseModel):
    """Request to initialize download."""
    file_id: str
    expires_minutes: int = Field(default=60, ge=5, le=1440)


class InitDownloadResponse(BaseModel):
    """Response with download details."""
    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    download_url: str
    expires_at: str


# ===== File Management Models =====

class FileListResponse(BaseModel):
    """List of user's cloud files."""
    files: List[Dict[str, Any]]
    total: int
