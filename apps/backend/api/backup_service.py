"""Backward Compatibility Shim - use api.backup instead."""

from api.backup.service import (
    BackupService,
    BACKUP_DIR,
    BACKUP_RETENTION_DAYS,
    BACKUP_EXTENSION,
    VERSION,
    logger,
)

__all__ = [
    "BackupService",
    "BACKUP_DIR",
    "BACKUP_RETENTION_DAYS",
    "BACKUP_EXTENSION",
    "VERSION",
    "logger",
]
