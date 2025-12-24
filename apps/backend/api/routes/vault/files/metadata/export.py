"""
Vault Files Export Routes

Handles vault data export and backup operations:
- Export vault metadata for backup purposes

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
