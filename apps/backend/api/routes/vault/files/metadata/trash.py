"""
Vault Files Trash Routes

Handles trash/recycle bin operations:
- Move files to trash (soft delete)
- Restore files from trash
- Get trash contents with pagination
- Empty trash (permanent deletion)
- Secure file deletion

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


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
    key = f"vault:file:trash:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.file.trashed"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    key = f"vault:file:restore:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.file.restored"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    key = f"vault:trash:list:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.trash.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    key = f"vault:trash:empty:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.trash.emptied"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    user_id = get_user_id(current_user)

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
