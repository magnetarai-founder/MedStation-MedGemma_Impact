"""
Vault Files Tags Routes

Handles tag management operations for vault files:
- Add tags to files with custom colors
- Remove tags from files
- Get all tags for a file

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Form, Depends, status
from api.routes.schemas import SuccessResponse

from api.auth_middleware import get_current_user
from api.errors import http_404, http_500
from api.utils import get_user_id
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    user_id = get_user_id(current_user)

    try:
        result = service.add_tag_to_file(user_id, vault_type, file_id, tag_name, tag_color)
        return SuccessResponse(data=result, message="Tag added to file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tag to file {file_id}", exc_info=True)
        raise http_500("Failed to add tag to file")


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
    user_id = get_user_id(current_user)

    try:
        success = service.remove_tag_from_file(user_id, vault_type, file_id, tag_name)
        if not success:
            raise http_404(f"Tag '{tag_name}' not found on file", resource="tag")
        return SuccessResponse(data={"success": True}, message="Tag removed from file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag from file {file_id}", exc_info=True)
        raise http_500("Failed to remove tag from file")


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
    user_id = get_user_id(current_user)

    try:
        tags = service.get_file_tags(user_id, vault_type, file_id)
        return SuccessResponse(data={"tags": tags}, message="File tags retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tags for file {file_id}", exc_info=True)
        raise http_500("Failed to get file tags")
