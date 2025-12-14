"""
Model Tags API Routes

Provides endpoints for getting and managing model tags (auto-detected + manual).
Supports tag detection from model names and manual tag overrides.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from auth_middleware import get_current_user, User

from api.services.model_tags import detect_tags_from_name, get_all_tags, get_tag_description, get_tag_icon
from api.services.model_tag_overrides import get_manual_tags, set_manual_tags, delete_manual_tags, get_merged_tags
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["model-tags"]
)


# MARK: - Request/Response Models

class ModelTagsResponse(BaseModel):
    """Response with model tags"""
    model_name: str
    tags: List[str]
    auto_detected: List[str]
    manual_override: bool


class UpdateTagsRequest(BaseModel):
    """Request to update model tags"""
    tags: List[str]


class TagDefinition(BaseModel):
    """Tag metadata"""
    id: str
    name: str
    description: str
    icon: str


# MARK: - API Endpoints

@router.get(
    "/tags/available",
    response_model=SuccessResponse[List[TagDefinition]],
    status_code=status.HTTP_200_OK,
    name="get_available_tags",
    summary="Get available tags",
    description="Get all available tag categories with metadata, sorted by priority"
)
async def get_available_tags() -> SuccessResponse[List[TagDefinition]]:
    """
    Get all available tag categories with metadata

    Returns list of tag definitions sorted by priority
    """
    try:
        tags = get_all_tags()
        tag_list = [TagDefinition(**tag) for tag in tags]

        return SuccessResponse(
            data=tag_list,
            message=f"Retrieved {len(tag_list)} available tag(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get available tags", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve available tags"
            ).model_dump()
        )


@router.get(
    "/models/{model_name}/tags",
    response_model=SuccessResponse[ModelTagsResponse],
    status_code=status.HTTP_200_OK,
    name="get_model_tags",
    summary="Get model tags",
    description="Get tags for a specific model (auto-detected + manual overrides)"
)
async def get_model_tags(
    model_name: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[ModelTagsResponse]:
    """
    Get tags for a specific model (auto-detected + manual override)

    Args:
        model_name: Model name (e.g., "qwen2.5-coder:3b")

    Returns:
        ModelTagsResponse with final tags, auto-detected tags, and override status
    """
    try:
        # Auto-detect tags from model name
        auto_tags = detect_tags_from_name(model_name)

        # Get manual overrides if they exist
        manual_tags = get_manual_tags(model_name)

        # Merge tags (manual completely replaces auto if it exists)
        final_tags = get_merged_tags(model_name, auto_tags)

        return SuccessResponse(
            data=ModelTagsResponse(
                model_name=model_name,
                tags=sorted(final_tags),
                auto_detected=sorted(auto_tags),
                manual_override=manual_tags is not None
            ),
            message=f"Retrieved tags for model '{model_name}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get tags for model {model_name}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to retrieve tags for model"
            ).model_dump()
        )


@router.put(
    "/models/{model_name}/tags",
    response_model=SuccessResponse[ModelTagsResponse],
    status_code=status.HTTP_200_OK,
    name="update_model_tags",
    summary="Update model tags",
    description="Set manual tag overrides for a model (replaces auto-detected tags)"
)
async def update_model_tags(
    model_name: str,
    request: UpdateTagsRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[ModelTagsResponse]:
    """
    Update manual tag overrides for a model

    This completely replaces auto-detected tags with user-specified tags.

    Args:
        model_name: Model name
        request: UpdateTagsRequest with list of tag IDs

    Returns:
        Updated ModelTagsResponse
    """
    try:
        # Validate tags exist
        available_tag_ids = {tag["id"] for tag in get_all_tags()}
        invalid_tags = [tag for tag in request.tags if tag not in available_tag_ids]

        if invalid_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid tags: {', '.join(invalid_tags)}",
                    details={"invalid_tags": invalid_tags}
                ).model_dump()
            )

        # Save manual overrides
        set_manual_tags(model_name, request.tags)

        # Return updated tags
        return await get_model_tags(model_name, current_user)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update tags for model {model_name}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update model tags"
            ).model_dump()
        )


@router.delete(
    "/models/{model_name}/tags",
    response_model=SuccessResponse[ModelTagsResponse],
    status_code=status.HTTP_200_OK,
    name="delete_model_tag_overrides",
    summary="Delete tag overrides",
    description="Delete manual tag overrides for a model (revert to auto-detection)"
)
async def delete_model_tag_overrides(
    model_name: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[ModelTagsResponse]:
    """
    Delete manual tag overrides for a model (revert to auto-detection)

    Args:
        model_name: Model name

    Returns:
        ModelTagsResponse with auto-detected tags restored
    """
    try:
        # Delete manual overrides
        deleted = delete_manual_tags(model_name)

        if not deleted:
            logger.warning(f"No manual tag overrides found for {model_name}")

        # Return auto-detected tags
        return await get_model_tags(model_name, current_user)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete tag overrides for model {model_name}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete tag overrides"
            ).model_dump()
        )
