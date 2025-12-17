"""
Vault Files Activity Routes

Handles file access logging and activity tracking:
- Log file access for recent files tracking
- Get recently accessed files
- Get storage statistics and analytics
- Get audit logs with filters

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
