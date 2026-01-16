"""
Backup Types - Request/response models for backup operations

Extracted from backup_router.py during P2 decomposition.
Contains:
- BackupCreateRequest, BackupCreateResponse (backup creation)
- BackupVerifyRequest (integrity verification)
- BackupRestoreRequest (backup restoration)
- BackupCleanupRequest (old backup cleanup)
"""

from pydantic import BaseModel


class BackupCreateRequest(BaseModel):
    """Request to create a new backup"""
    passphrase: str


class BackupCreateResponse(BaseModel):
    """Response from backup creation"""
    success: bool
    backup_path: str | None = None
    backup_name: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    verified: bool = False  # HIGH-08: Auto-verification status
    error: str | None = None


class BackupVerifyRequest(BaseModel):
    """Request to verify a backup's integrity"""
    backup_path: str | None = None
    backup_name: str | None = None
    passphrase: str


class BackupRestoreRequest(BaseModel):
    """Request to restore a backup"""
    backup_path: str | None = None
    backup_name: str | None = None
    passphrase: str


class BackupCleanupRequest(BaseModel):
    """Request to cleanup old backups"""
    passphrase: str | None = None  # Optional for cleanup


__all__ = [
    "BackupCreateRequest",
    "BackupCreateResponse",
    "BackupVerifyRequest",
    "BackupRestoreRequest",
    "BackupCleanupRequest",
]
