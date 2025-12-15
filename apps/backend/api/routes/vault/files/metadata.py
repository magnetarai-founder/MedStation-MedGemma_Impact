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

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

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

@router.post(
    "/files/{file_id}/tags",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_add_tag",
    summary="Add tag to file",
    description="Add a tag with custom color to a file for organization"
)
async def add_file_tag(
    file_id: str,
    tag_name: str = Form(...),
    tag_color: str = Form("#3B82F6"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Add a tag to a file.

    Returns:
        SuccessResponse containing tag details
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_tag_to_file(user_id, vault_type, file_id, tag_name, tag_color)
        return SuccessResponse(data=result, message="Tag added to file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tag to file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to add tag to file"
            ).model_dump()
        )


@router.delete(
    "/files/{file_id}/tags/{tag_name}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_remove_tag",
    summary="Remove tag from file",
    description="Remove a specific tag from a file"
)
async def remove_file_tag(
    file_id: str,
    tag_name: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Remove a tag from a file.

    Returns:
        SuccessResponse confirming tag removal
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_tag_from_file(user_id, vault_type, file_id, tag_name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Tag '{tag_name}' not found on file"
                ).model_dump()
            )
        return SuccessResponse(data={"success": True}, message="Tag removed from file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag from file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove tag from file"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/tags",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_tags",
    summary="Get file tags",
    description="Get all tags associated with a file"
)
async def get_file_tags(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get all tags for a file.

    Returns:
        SuccessResponse containing list of tags
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        tags = service.get_file_tags(user_id, vault_type, file_id)
        return SuccessResponse(data={"tags": tags}, message="File tags retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tags for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file tags"
            ).model_dump()
        )


# ===== Favorites Endpoints =====

@router.post(
    "/files/{file_id}/favorite",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_add_favorite",
    summary="Add file to favorites",
    description="Mark a file as favorite for quick access"
)
async def add_favorite_file(
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Add file to favorites.

    Returns:
        SuccessResponse confirming favorite added
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_favorite(user_id, vault_type, file_id)
        return SuccessResponse(data=result, message="File added to favorites successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add favorite for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to add file to favorites"
            ).model_dump()
        )


@router.delete(
    "/files/{file_id}/favorite",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_remove_favorite",
    summary="Remove file from favorites",
    description="Remove a file from user's favorites list"
)
async def remove_favorite_file(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Remove file from favorites.

    Returns:
        SuccessResponse confirming favorite removed
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_favorite(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Favorite not found"
                ).model_dump()
            )
        return SuccessResponse(data={"success": True}, message="File removed from favorites successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove file from favorites"
            ).model_dump()
        )


@router.get(
    "/favorites",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_favorites",
    summary="Get favorite files",
    description="Get list of user's favorite file IDs"
)
async def get_favorite_files(
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get list of favorite file IDs.

    Returns:
        SuccessResponse containing list of favorite file IDs
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        favorites = service.get_favorites(user_id, vault_type)
        return SuccessResponse(data={"favorites": favorites}, message="Favorite files retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get favorites for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get favorite files"
            ).model_dump()
        )


# ===== Recent Files Endpoints =====

@router.post(
    "/files/{file_id}/log-access",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_log_access",
    summary="Log file access",
    description="Log file access for recent files tracking"
)
async def log_file_access_endpoint(
    file_id: str,
    access_type: str = Form("view"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Log file access (for recent files tracking).

    Returns:
        SuccessResponse confirming access logged
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        service.log_file_access(user_id, vault_type, file_id, access_type)
        return SuccessResponse(data={"success": True}, message="File access logged successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to log file access for file {file_id}", exc_info=True)
        # Return success=False for non-critical logging failures
        return SuccessResponse(data={"success": False}, message="Failed to log file access")


@router.get(
    "/recent-files",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_recent",
    summary="Get recent files",
    description="Get recently accessed files with optional limit"
)
async def get_recent_files_endpoint(
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get recently accessed files.

    Returns:
        SuccessResponse containing list of recent files
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        recent = service.get_recent_files(user_id, vault_type, limit)
        return SuccessResponse(data={"recent_files": recent}, message="Recent files retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent files for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get recent files"
            ).model_dump()
        )


# ===== Storage Statistics Endpoint =====

@router.get(
    "/storage-stats",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_storage_stats",
    summary="Get storage statistics",
    description="Get storage statistics and analytics for vault"
)
async def get_storage_statistics(
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get storage statistics and analytics.

    Returns:
        SuccessResponse containing storage statistics
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        stats = service.get_storage_stats(user_id, vault_type)
        return SuccessResponse(data=stats, message="Storage statistics retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get storage stats for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get storage statistics"
            ).model_dump()
        )


# ===== Secure Deletion Endpoint =====

@router.delete(
    "/files/{file_id}/secure",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_secure_delete",
    summary="Securely delete file",
    description="Securely delete a file (overwrites with random data before deletion)"
)
async def secure_delete_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Securely delete a file (overwrites with random data before deletion).

    Returns:
        SuccessResponse confirming secure deletion
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.secure_delete_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )
        return SuccessResponse(data={"success": True}, message="File securely deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely delete file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to securely delete file"
            ).model_dump()
        )


# ===== File Versioning Endpoints =====

@router.get(
    "/files/{file_id}/versions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_versions",
    summary="Get file versions",
    description="Get file versions with pagination"
)
async def get_file_versions_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get file versions with pagination.

    Returns:
        SuccessResponse containing paginated file versions
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:versions:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.versions.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_versions = service.get_file_versions(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_versions)
        versions = all_versions[offset:offset + limit]
        has_more = (offset + limit) < total

        return SuccessResponse(
            data={
                "versions": versions,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            },
            message="File versions retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file versions for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file versions"
            ).model_dump()
        )


@router.post(
    "/files/{file_id}/versions/{version_id}/restore",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_restore_version",
    summary="Restore file version",
    description="Restore a file to a previous version"
)
async def restore_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Restore a file to a previous version.

    Returns:
        SuccessResponse confirming version restored
    """
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.version.restored"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message="File version restored successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore file version for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to restore file version"
            ).model_dump()
        )


@router.delete(
    "/files/{file_id}/versions/{version_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_delete_version",
    summary="Delete file version",
    description="Delete a specific file version"
)
async def delete_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Delete a specific file version.

    Returns:
        SuccessResponse confirming version deleted
    """
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.version.deleted"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_version(user_id, vault_type, version_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Version not found"
                ).model_dump()
            )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.version.deleted",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "version_id": version_id}
        )

        return SuccessResponse(data={"success": True}, message="Version deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file version {version_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete file version"
            ).model_dump()
        )


# ===== Trash/Recycle Bin Endpoints =====

@router.post(
    "/files/{file_id}/trash",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_move_to_trash",
    summary="Move file to trash",
    description="Move a file to trash (soft delete)"
)
async def move_to_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Move a file to trash (soft delete).

    Returns:
        SuccessResponse confirming file moved to trash
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:trash:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.file.trashed"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message="File moved to trash successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to move file {file_id} to trash", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to move file to trash"
            ).model_dump()
        )


@router.post(
    "/files/{file_id}/restore",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_restore_from_trash",
    summary="Restore file from trash",
    description="Restore a file from trash"
)
async def restore_from_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Restore a file from trash.

    Returns:
        SuccessResponse confirming file restored
    """
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.file.restored"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message="File restored from trash successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore file {file_id} from trash", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to restore file from trash"
            ).model_dump()
        )


@router.get(
    "/trash",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_trash",
    summary="Get trash files",
    description="Get trash files with pagination"
)
async def get_trash_files_endpoint(
    request: Request,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get trash files with pagination.

    Returns:
        SuccessResponse containing paginated trash files
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:trash:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.trash.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_trash_files = service.get_trash_files(user_id, vault_type)
        # Apply pagination
        total = len(all_trash_files)
        trash_files = all_trash_files[offset:offset + limit]
        has_more = (offset + limit) < total

        return SuccessResponse(
            data={
                "trash_files": trash_files,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            },
            message="Trash files retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trash files for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get trash files"
            ).model_dump()
        )


@router.delete(
    "/trash/empty",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_empty_trash",
    summary="Empty trash",
    description="Permanently delete all files in trash"
)
async def empty_trash_endpoint(
    request: Request,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Permanently delete all files in trash.

    Returns:
        SuccessResponse containing count of deleted files
    """
    # Rate limiting: 5 requests per minute per user (destructive operation)
    ip = get_client_ip(request)
    key = f"vault:trash:empty:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.trash.emptied"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message=f"Trash emptied successfully ({deleted_count} files deleted)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to empty trash for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to empty trash"
            ).model_dump()
        )


# ===== Audit Logs Endpoints =====

@router.get(
    "/audit-logs",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_audit_logs",
    summary="Get audit logs",
    description="Get audit logs with pagination and filters"
)
async def get_audit_logs_endpoint(
    vault_type: str = None,
    action: str = None,
    resource_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get audit logs with pagination and filters.

    Returns:
        SuccessResponse containing paginated audit logs
    """
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

        return SuccessResponse(
            data={
                "logs": logs,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            },
            message="Audit logs retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit logs for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get audit logs"
            ).model_dump()
        )


# ===== File Comments Endpoints =====

@router.post(
    "/files/{file_id}/comments",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_add_comment",
    summary="Add comment to file",
    description="Add a comment to a file"
)
async def add_file_comment_endpoint(
    request: Request,
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Add a comment to a file.

    Returns:
        SuccessResponse containing comment details
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:add:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.added"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message="Comment added to file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add comment to file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to add comment"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/comments",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_comments",
    summary="Get file comments",
    description="Get file comments with pagination"
)
async def get_file_comments_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get file comments with pagination.

    Returns:
        SuccessResponse containing paginated comments
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_comments = service.get_file_comments(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_comments)
        comments = all_comments[offset:offset + limit]
        has_more = (offset + limit) < total

        return SuccessResponse(
            data={
                "comments": comments,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            },
            message="File comments retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get comments for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file comments"
            ).model_dump()
        )


@router.put(
    "/comments/{comment_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_update_comment",
    summary="Update comment",
    description="Update a file comment"
)
async def update_file_comment_endpoint(
    request: Request,
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Update a comment.

    Returns:
        SuccessResponse containing updated comment details
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:update:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.updated"
            ).model_dump()
        )

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

        return SuccessResponse(data=result, message="Comment updated successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update comment {comment_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update comment"
            ).model_dump()
        )


@router.delete(
    "/comments/{comment_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_delete_comment",
    summary="Delete comment",
    description="Delete a file comment"
)
async def delete_file_comment_endpoint(
    request: Request,
    comment_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Delete a comment.

    Returns:
        SuccessResponse confirming comment deleted
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.deleted"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Comment not found"
                ).model_dump()
            )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.deleted",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return SuccessResponse(data={"success": True}, message="Comment deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete comment {comment_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete comment"
            ).model_dump()
        )


# ===== File Metadata Endpoints =====

@router.post(
    "/files/{file_id}/metadata",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_set_metadata",
    summary="Set file metadata",
    description="Set custom metadata for a file"
)
async def set_file_metadata_endpoint(
    file_id: str,
    key: str = Form(...),
    value: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Set custom metadata for a file.

    Returns:
        SuccessResponse containing metadata details
    """
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

        return SuccessResponse(data=result, message="File metadata set successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set metadata for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to set file metadata"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/metadata",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_metadata",
    summary="Get file metadata",
    description="Get all metadata for a file"
)
async def get_file_metadata_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get all metadata for a file.

    Returns:
        SuccessResponse containing file metadata
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        metadata = service.get_file_metadata(user_id, vault_type, file_id)
        return SuccessResponse(data={"metadata": metadata}, message="File metadata retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file metadata"
            ).model_dump()
        )


# ===== Organization Features Endpoints =====

@router.post(
    "/files/{file_id}/pin",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_pin_file",
    summary="Pin file",
    description="Pin a file for quick access"
)
async def pin_file_endpoint(
    file_id: str,
    pin_order: int = Form(0),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Pin a file for quick access.

    Returns:
        SuccessResponse containing pin details
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.pin_file(user_id, vault_type, file_id, pin_order)
        return SuccessResponse(data=result, message="File pinned successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pin file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to pin file"
            ).model_dump()
        )


@router.delete(
    "/files/{file_id}/pin",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_unpin_file",
    summary="Unpin file",
    description="Unpin a file"
)
async def unpin_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Unpin a file.

    Returns:
        SuccessResponse confirming file unpinned
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.unpin_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not pinned"
                ).model_dump()
            )
        return SuccessResponse(data={"success": True}, message="File unpinned")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unpin file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unpin file"
            ).model_dump()
        )


@router.get(
    "/pinned-files",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_pinned",
    summary="Get pinned files",
    description="Get all pinned files"
)
async def get_pinned_files_endpoint(
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get all pinned files.

    Returns:
        SuccessResponse containing list of pinned files
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        pinned = service.get_pinned_files(user_id, vault_type)
        return SuccessResponse(data={"pinned_files": pinned}, message="Pinned files retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pinned files for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get pinned files"
            ).model_dump()
        )


# ===== Backup & Export Endpoints =====

@router.get(
    "/export",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_export_data",
    summary="Export vault data",
    description="Export vault metadata for backup"
)
async def export_vault_data_endpoint(
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Export vault metadata for backup.

    Returns:
        SuccessResponse containing exported vault data
    """
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        export_data = service.export_vault_data(user_id, vault_type)
        return SuccessResponse(data=export_data, message="Vault data exported successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export vault data for user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export vault data"
            ).model_dump()
        )
