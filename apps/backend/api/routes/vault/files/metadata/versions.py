"""
Vault Files Versions Routes

Handles file versioning operations:
- Get file version history with pagination
- Restore file to a previous version
- Delete specific file versions

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


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
    key = f"vault:versions:list:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.versions.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    key = f"vault:version:restore:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.version.restored"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
    key = f"vault:version:delete:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.version.deleted"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

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
