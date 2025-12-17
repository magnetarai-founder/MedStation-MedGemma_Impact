"""
Vault Files Metadata Operations Routes

Handles custom metadata management for files:
- Set custom metadata key-value pairs
- Get all metadata for a file

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
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


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
