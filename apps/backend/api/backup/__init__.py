"""
Backup Package

Provides encrypted backup and restore functionality for ElohimOS:
- BackupService: Core backup creation, verification, and restoration
- Router: RESTful API endpoints for backup operations
- Types: Pydantic request/response models
"""

from api.backup.service import BackupService
from api.backup.types import (
    BackupCreateRequest,
    BackupCreateResponse,
    BackupVerifyRequest,
    BackupRestoreRequest,
    BackupCleanupRequest,
)
from api.backup.router import router

__all__ = [
    # Core class
    "BackupService",
    # Router
    "router",
    # Types
    "BackupCreateRequest",
    "BackupCreateResponse",
    "BackupVerifyRequest",
    "BackupRestoreRequest",
    "BackupCleanupRequest",
]
