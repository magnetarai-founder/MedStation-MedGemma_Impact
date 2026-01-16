"""Backward Compatibility Shim - use api.backup instead."""

from api.backup.router import router, get_backup_service, logger

# Re-export types for backward compatibility
from api.backup.types import (
    BackupCreateRequest,
    BackupCreateResponse,
    BackupVerifyRequest,
    BackupRestoreRequest,
    BackupCleanupRequest,
)

__all__ = [
    "router",
    "get_backup_service",
    "logger",
    "BackupCreateRequest",
    "BackupCreateResponse",
    "BackupVerifyRequest",
    "BackupRestoreRequest",
    "BackupCleanupRequest",
]
