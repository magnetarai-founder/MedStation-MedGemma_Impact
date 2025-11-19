"""
Vault Files Metadata Routes

Handles file metadata and organization features:
- Tags management
- Favorites
- Recent files
- Storage statistics
- Secure deletion
- File versioning
- Trash/recycle bin
- Audit logs
- File comments
- Custom metadata
- Pinned files
- Backup & export
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Form, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


# ===== Tags Endpoints =====

@router.post("/files/{file_id}/tags")
async def add_file_tag(
    file_id: str,
    tag_name: str = Form(...),
    tag_color: str = Form("#3B82F6"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add a tag to a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_tag_to_file(user_id, vault_type, file_id, tag_name, tag_color)
        return result
    except Exception as e:
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/tags/{tag_name}")
async def remove_file_tag(
    file_id: str,
    tag_name: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Remove a tag from a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_tag_from_file(user_id, vault_type, file_id, tag_name)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/tags")
async def get_file_tags(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all tags for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        tags = service.get_file_tags(user_id, vault_type, file_id)
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Favorites Endpoints =====

@router.post("/files/{file_id}/favorite")
async def add_favorite_file(
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add file to favorites"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_favorite(user_id, vault_type, file_id)
        return result
    except Exception as e:
        logger.error(f"Failed to add favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/favorite")
async def remove_favorite_file(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Remove file from favorites"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_favorite(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Favorite not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorite_files(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get list of favorite file IDs"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        favorites = service.get_favorites(user_id, vault_type)
        return {"favorites": favorites}
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Recent Files Endpoints =====

@router.post("/files/{file_id}/log-access")
async def log_file_access_endpoint(
    file_id: str,
    access_type: str = Form("view"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Log file access (for recent files tracking)"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        service.log_file_access(user_id, vault_type, file_id, access_type)
        return {"success": True}
    except Exception as e:
        logger.warning(f"Failed to log file access: {e}")
        return {"success": False}


@router.get("/recent-files")
async def get_recent_files_endpoint(
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """Get recently accessed files"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        recent = service.get_recent_files(user_id, vault_type, limit)
        return {"recent_files": recent}
    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Storage Statistics Endpoint =====

@router.get("/storage-stats")
async def get_storage_statistics(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get storage statistics and analytics"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        stats = service.get_storage_stats(user_id, vault_type)
        return stats
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Secure Deletion Endpoint =====

@router.delete("/files/{file_id}/secure")
async def secure_delete_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Securely delete a file (overwrites with random data before deletion)"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.secure_delete_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        return {"success": True, "message": "File securely deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Versioning Endpoints =====

@router.get("/files/{file_id}/versions")
async def get_file_versions_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get file versions with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:versions:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.versions.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_versions = service.get_file_versions(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_versions)
        versions = all_versions[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "versions": versions,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get file versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/versions/{version_id}/restore")
async def restore_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file to a previous version"""
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.version.restored")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_file_version(user_id, vault_type, file_id, version_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.version.restored",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "version_id": version_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/versions/{version_id}")
async def delete_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific file version"""
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.version.deleted")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_version(user_id, vault_type, version_id)
        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.version.deleted",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "version_id": version_id}
        )

        return {"success": True, "message": "Version deleted"}
    except Exception as e:
        logger.error(f"Failed to delete file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Trash/Recycle Bin Endpoints =====

@router.post("/files/{file_id}/trash")
async def move_to_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Move a file to trash (soft delete)"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:trash:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.file.trashed")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.move_to_trash(user_id, vault_type, file_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.trashed",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to move file to trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/restore")
async def restore_from_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file from trash"""
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.file.restored")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_from_trash(user_id, vault_type, file_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.restored",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file from trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trash")
async def get_trash_files_endpoint(
    request: Request,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get trash files with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:trash:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.trash.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_trash_files = service.get_trash_files(user_id, vault_type)
        # Apply pagination
        total = len(all_trash_files)
        trash_files = all_trash_files[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "trash_files": trash_files,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get trash files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/trash/empty")
async def empty_trash_endpoint(
    request: Request,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Permanently delete all files in trash"""
    # Rate limiting: 5 requests per minute per user (destructive operation)
    ip = get_client_ip(request)
    key = f"vault:trash:empty:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.trash.emptied")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.empty_trash(user_id, vault_type)

        # Audit logging after success
        deleted_count = result.get("deleted_count", 0)
        audit_logger.log(
            user_id=user_id,
            action="vault.trash.emptied",
            resource="vault",
            resource_id=user_id,  # User-level operation
            details={"count": deleted_count}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Audit Logs Endpoints =====

@router.get("/audit-logs")
async def get_audit_logs_endpoint(
    vault_type: str = None,
    action: str = None,
    resource_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get audit logs with pagination and filters"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        # Get all matching logs first (service applies limit internally)
        # We'll need to modify this to handle pagination properly
        all_logs = service.get_audit_logs(
            user_id, vault_type, action, resource_type,
            date_from, date_to, limit + offset  # Get enough to paginate
        )
        # Apply pagination
        total = len(all_logs)
        logs = all_logs[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Comments Endpoints =====

@router.post("/files/{file_id}/comments")
async def add_file_comment_endpoint(
    request: Request,
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add a comment to a file"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:add:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.added")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_file_comment(user_id, vault_type, file_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.added",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "comment_id": result.get("comment_id")}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/comments")
async def get_file_comments_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get file comments with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_comments = service.get_file_comments(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_comments)
        comments = all_comments[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "comments": comments,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_file_comment_endpoint(
    request: Request,
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Update a comment"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:update:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.updated")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.update_file_comment(user_id, vault_type, comment_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.updated",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_file_comment_endpoint(
    request: Request,
    comment_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a comment"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.deleted")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.deleted",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return {"success": True, "message": "Comment deleted"}
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Metadata Endpoints =====

@router.post("/files/{file_id}/metadata")
async def set_file_metadata_endpoint(
    file_id: str,
    key: str = Form(...),
    value: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Set custom metadata for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.set_file_metadata(user_id, vault_type, file_id, key, value)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.metadata.set",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "key": key}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to set metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/metadata")
async def get_file_metadata_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all metadata for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        metadata = service.get_file_metadata(user_id, vault_type, file_id)
        return {"metadata": metadata}
    except Exception as e:
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Organization Features Endpoints =====

@router.post("/files/{file_id}/pin")
async def pin_file_endpoint(
    file_id: str,
    pin_order: int = Form(0),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Pin a file for quick access"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.pin_file(user_id, vault_type, file_id, pin_order)
        return result
    except Exception as e:
        logger.error(f"Failed to pin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/pin")
async def unpin_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Unpin a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.unpin_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not pinned")
        return {"success": True, "message": "File unpinned"}
    except Exception as e:
        logger.error(f"Failed to unpin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned-files")
async def get_pinned_files_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get all pinned files"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        pinned = service.get_pinned_files(user_id, vault_type)
        return {"pinned_files": pinned}
    except Exception as e:
        logger.error(f"Failed to get pinned files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Backup & Export Endpoints =====

@router.get("/export")
async def export_vault_data_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Export vault metadata for backup"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        export_data = service.export_vault_data(user_id, vault_type)
        return export_data
    except Exception as e:
        logger.error(f"Failed to export vault data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
