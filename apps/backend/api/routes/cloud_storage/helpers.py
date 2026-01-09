"""
Cloud Storage - Helper Functions

Utility functions for upload/download operations.
"""

from __future__ import annotations

import json
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict

from api.config_paths import get_config_paths
from api.config import get_settings

logger = logging.getLogger(__name__)

PATHS = get_config_paths()

# Temp directory for uploads
TEMP_DIR = PATHS.cache_dir / "cloud_uploads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def get_s3_service():
    """
    Get S3 service if enabled, otherwise None.

    Lazily imports to avoid boto3 import errors if not installed.
    """
    settings = get_settings()
    if settings.cloud_storage_enabled and settings.cloud_storage_provider == "s3":
        try:
            from api.services.cloud_storage_s3 import get_s3_service as _get_s3_service
            service = _get_s3_service()
            if service.is_enabled:
                return service
        except ImportError:
            logger.warning("S3 storage enabled but boto3 not installed")
        except Exception as e:
            logger.error(f"Failed to initialize S3 service: {e}")
    return None


def get_upload_dir(upload_id: str) -> Path:
    """Get upload directory path."""
    return TEMP_DIR / upload_id


def get_metadata_path(upload_id: str) -> Path:
    """Get metadata JSON path."""
    return get_upload_dir(upload_id) / "metadata.json"


def load_metadata(upload_id: str) -> Optional[Dict]:
    """Load upload metadata."""
    metadata_path = get_metadata_path(upload_id)
    if not metadata_path.exists():
        return None

    with open(metadata_path, 'r') as f:
        return json.load(f)


def save_metadata(upload_id: str, metadata: Dict) -> None:
    """Save upload metadata."""
    metadata_path = get_metadata_path(upload_id)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def compute_chunk_hash(data: bytes) -> str:
    """Compute SHA-256 hash of chunk."""
    return hashlib.sha256(data).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of assembled file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_upload_id() -> str:
    """Generate secure upload ID."""
    return f"csu_{secrets.token_urlsafe(24)}"


def generate_file_id() -> str:
    """Generate cloud file ID."""
    return f"csf_{secrets.token_urlsafe(24)}"


def get_cloud_files_dir() -> Path:
    """Get cloud files directory."""
    cloud_files_dir = PATHS.cache_dir / "cloud_files"
    cloud_files_dir.mkdir(parents=True, exist_ok=True)
    return cloud_files_dir
