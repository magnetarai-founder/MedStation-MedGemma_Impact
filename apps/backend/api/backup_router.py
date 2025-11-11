"""
Backup Router for ElohimOS

Provides RESTful API endpoints for backup operations.
Requires backups.use permission.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from .audit_logger import AuditAction, get_audit_logger
    from .auth_middleware import get_current_user
    from .backup_service import BackupService
    from .permission_engine import require_perm
except ImportError:
    from audit_logger import AuditAction, get_audit_logger
    from auth_middleware import get_current_user
    from backup_service import BackupService
    from permission_engine import require_perm

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])


class BackupCreateRequest(BaseModel):
    passphrase: str


class BackupCreateResponse(BaseModel):
    success: bool
    backup_path: str | None = None
    backup_name: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    verified: bool = False  # HIGH-08: Auto-verification status
    error: str | None = None


class BackupVerifyRequest(BaseModel):
    backup_path: str | None = None
    backup_name: str | None = None
    passphrase: str


class BackupRestoreRequest(BaseModel):
    backup_path: str | None = None
    backup_name: str | None = None
    passphrase: str


class BackupCleanupRequest(BaseModel):
    passphrase: str | None = None  # Optional for cleanup


def get_backup_service(passphrase: str) -> BackupService:
    """
    Get BackupService instance with user-provided passphrase

    Args:
        passphrase: Encryption passphrase for backup operations

    Returns:
        BackupService instance configured with the passphrase
    """
    if not passphrase:
        raise HTTPException(status_code=400, detail="Passphrase is required for backup operations")

    return BackupService(passphrase)


@router.post("/create", response_model=BackupCreateResponse)
@require_perm("backups.use")
async def create_backup(
    request: Request,
    payload: BackupCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new backup

    Creates an encrypted backup of all ElohimOS databases.
    Requires backups.use permission.

    Body:
        - passphrase: Encryption passphrase for the backup

    Returns:
        Backup summary with path, name, size, and timestamp
    """
    try:
        # Get backup service with user-provided passphrase
        backup_service = get_backup_service(payload.passphrase)

        # Create backup
        backup_path = backup_service.create_backup()

        if not backup_path:
            raise HTTPException(status_code=500, detail="Failed to create backup")

        # Get backup info
        stat = backup_path.stat()

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action=AuditAction.BACKUP_CREATED,
            resource="backup",
            resource_id=backup_path.name,
            ip_address=request.client.host if request.client else None,
            details={
                "backup_path": str(backup_path),
                "size_bytes": stat.st_size
            }
        )

        logger.info(f"User {current_user['user_id']} created backup: {backup_path.name}")

        return BackupCreateResponse(
            success=True,
            backup_path=str(backup_path),
            backup_name=backup_path.name,
            size_bytes=stat.st_size,
            created_at=backup_path.stat().st_ctime.__str__(),
            verified=True  # HIGH-08: Verified during creation
        )

    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return BackupCreateResponse(
            success=False,
            error=str(e)
        )


@router.get("/list")
@require_perm("backups.use")
async def list_backups(
    current_user: dict = Depends(get_current_user)
):
    """
    List all available backups

    Note: This endpoint doesn't require passphrase as it only lists metadata.

    Returns:
        List of backup metadata (name, size, created date, checksum)
    """
    try:
        # Use temporary service just for listing (passphrase not needed for metadata)
        backup_service = BackupService("temp_for_list")
        backups = backup_service.list_backups()

        logger.info(f"User {current_user['user_id']} listed {len(backups)} backups")

        return {
            "backups": backups,
            "total": len(backups)
        }

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.post("/verify")
@require_perm("backups.use")
async def verify_backup(
    request: Request,
    payload: BackupVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a backup's integrity

    Body:
        - backup_path: Full path to backup file (optional)
        - backup_name: Name of backup file in ~/.elohimos_backups (optional)
        - passphrase: Decryption passphrase to verify the backup

    Returns:
        Verification result
    """
    try:
        backup_service = get_backup_service(payload.passphrase)

        # Determine backup path
        if payload.backup_path:
            backup_path = Path(payload.backup_path)
        elif payload.backup_name:
            backup_path = backup_service.backup_dir / payload.backup_name
        else:
            raise HTTPException(status_code=400, detail="Must provide backup_path or backup_name")

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        # Verify backup
        is_valid = backup_service.verify_backup(backup_path)

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action="backup.verified",
            resource="backup",
            resource_id=backup_path.name,
            ip_address=request.client.host if request.client else None,
            details={
                "backup_path": str(backup_path),
                "is_valid": is_valid
            }
        )

        logger.info(f"User {current_user['user_id']} verified backup: {backup_path.name} - Valid: {is_valid}")

        return {
            "valid": is_valid,
            "backup_name": backup_path.name,
            "backup_path": str(backup_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify backup: {str(e)}")


@router.post("/restore")
@require_perm("backups.use")
async def restore_backup(
    request: Request,
    payload: BackupRestoreRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Restore a backup

    Body:
        - backup_path: Full path to backup file (optional)
        - backup_name: Name of backup file in ~/.elohimos_backups (optional)
        - passphrase: Decryption passphrase for the backup

    Returns:
        Restore result
    """
    try:
        backup_service = get_backup_service(payload.passphrase)

        # Determine backup path
        if payload.backup_path:
            backup_path = Path(payload.backup_path)
        elif payload.backup_name:
            backup_path = backup_service.backup_dir / payload.backup_name
        else:
            raise HTTPException(status_code=400, detail="Must provide backup_path or backup_name")

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        # Restore backup
        success = backup_service.restore_backup(backup_path)

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action=AuditAction.BACKUP_RESTORED,
            resource="backup",
            resource_id=backup_path.name,
            ip_address=request.client.host if request.client else None,
            details={
                "backup_path": str(backup_path),
                "success": success
            }
        )

        logger.info(f"User {current_user['user_id']} restored backup: {backup_path.name} - Success: {success}")

        return {
            "success": success,
            "backup_name": backup_path.name,
            "backup_path": str(backup_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")


@router.post("/cleanup")
@require_perm("backups.use")
async def cleanup_old_backups(
    request: Request,
    payload: BackupCleanupRequest | None = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Clean up old backups (older than 7 days)

    Body (optional):
        - passphrase: Optional passphrase (cleanup only requires file system access)

    Returns:
        Number of backups deleted
    """
    try:
        # Use temporary service for cleanup (passphrase not needed for file deletion)
        backup_service = BackupService("temp_for_cleanup")
        deleted_count = backup_service.cleanup_old_backups()

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action="backup.cleanup",
            resource="backup",
            ip_address=request.client.host if request.client else None,
            details={
                "deleted_count": deleted_count
            }
        )

        logger.info(f"User {current_user['user_id']} cleaned up {deleted_count} old backups")

        return {
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} old backup(s)"
        }

    except Exception as e:
        logger.error(f"Failed to cleanup backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup backups: {str(e)}")


@router.get("/download")
@require_perm("backups.use")
async def download_backup(
    request: Request,
    backup_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Download an encrypted backup file

    Query params:
        - backup_name: Name of backup file in ~/.elohimos_backups

    Returns:
        FileResponse with encrypted backup file
    """
    try:
        # Strict validation: no path separators allowed
        if '/' in backup_name or '\\' in backup_name or '..' in backup_name:
            raise HTTPException(status_code=400, detail="Invalid backup name - path traversal not allowed")

        # Use temporary service to get backup directory
        backup_service = BackupService("temp_for_download")
        backup_path = backup_service.backup_dir / backup_name

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        if not backup_path.is_file():
            raise HTTPException(status_code=400, detail="Invalid backup file")

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action="backup.downloaded",
            resource="backup",
            resource_id=backup_name,
            ip_address=request.client.host if request.client else None,
            details={
                "backup_path": str(backup_path),
                "size_bytes": backup_path.stat().st_size
            }
        )

        logger.info(f"User {current_user['user_id']} downloading backup: {backup_name}")

        return FileResponse(
            path=str(backup_path),
            filename=backup_name,
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download backup: {str(e)}")


# Export the router
__all__ = ["router"]
