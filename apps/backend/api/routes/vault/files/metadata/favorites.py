"""
Vault Files Favorites Routes

Handles favorite and pinned file operations:
- Add files to favorites
- Remove files from favorites
- Get list of favorite files
- Pin files for quick access
- Unpin files
- Get list of pinned files

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_404, http_500

from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    user_id = get_user_id(current_user)

    try:
        result = service.add_favorite(user_id, vault_type, file_id)
        return SuccessResponse(data=result, message="File added to favorites successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add favorite for file {file_id}", exc_info=True)
        raise http_500("Failed to add file to favorites")


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
    user_id = get_user_id(current_user)

    try:
        success = service.remove_favorite(user_id, vault_type, file_id)
        if not success:
            raise http_404("Favorite not found", resource="favorite")
        return SuccessResponse(data={"success": True}, message="File removed from favorites successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite for file {file_id}", exc_info=True)
        raise http_500("Failed to remove file from favorites")


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
    user_id = get_user_id(current_user)

    try:
        favorites = service.get_favorites(user_id, vault_type)
        return SuccessResponse(data={"favorites": favorites}, message="Favorite files retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get favorites for user {user_id}", exc_info=True)
        raise http_500("Failed to get favorite files")


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
    user_id = get_user_id(current_user)

    try:
        result = service.pin_file(user_id, vault_type, file_id, pin_order)
        return SuccessResponse(data=result, message="File pinned successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pin file {file_id}", exc_info=True)
        raise http_500("Failed to pin file")


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
    user_id = get_user_id(current_user)

    try:
        success = service.unpin_file(user_id, vault_type, file_id)
        if not success:
            raise http_404("File not pinned", resource="pin")
        return SuccessResponse(data={"success": True}, message="File unpinned")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unpin file {file_id}", exc_info=True)
        raise http_500("Failed to unpin file")


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
    user_id = get_user_id(current_user)

    try:
        pinned = service.get_pinned_files(user_id, vault_type)
        return SuccessResponse(data={"pinned_files": pinned}, message="Pinned files retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pinned files for user {user_id}", exc_info=True)
        raise http_500("Failed to get pinned files")
