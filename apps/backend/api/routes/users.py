"""
Users API - User profile management

Provides endpoints for managing user profiles and settings.
Follows MedStation API standards (see API_STANDARDS.md).
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from api.auth_middleware import get_current_user, User
from api.permissions import require_perm
from api.routes.schemas import SuccessResponse
from api.schemas.user_models import UserProfile, UserProfileUpdate
from api.errors import http_500

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]  # All endpoints require auth
)


@router.get(
    "/me",
    response_model=SuccessResponse[UserProfile],
    name="users_get_me",
    summary="Get current user profile",
    description="Get or create the current user's profile information"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserProfile]:
    """
    Get or create the current user profile.

    Returns:
        User profile with settings and preferences
    """
    from api.services import users

    try:
        profile = await users.get_or_create_user_profile()
        return SuccessResponse(
            data=profile,
            message="User profile retrieved successfully"
        )

    except HTTPException:
        raise  # Re-raise FastAPI exceptions

    except Exception as e:
        logger.error(f"Failed to get user profile", exc_info=True)
        raise http_500("Failed to retrieve user profile")


@router.put(
    "/me",
    response_model=SuccessResponse[UserProfile],
    name="users_update_me",
    summary="Update current user profile",
    description="Update the current user's profile settings and preferences"
)
async def update_current_user_profile(
    updates: UserProfileUpdate,  # Automatic Pydantic validation
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserProfile]:
    """
    Update the current user profile.

    Args:
        updates: Profile fields to update (only provided fields are updated)

    Returns:
        Updated user profile
    """
    from api.services import users

    try:
        profile = await users.update_user_profile(updates.dict(exclude_unset=True))
        return SuccessResponse(
            data=profile,
            message="User profile updated successfully"
        )

    except HTTPException:
        raise  # Re-raise FastAPI exceptions

    except Exception as e:
        logger.error(f"Failed to update user profile", exc_info=True)
        raise http_500("Failed to update user profile")


@router.post(
    "/reset",
    response_model=SuccessResponse[dict],
    name="users_reset",
    summary="Reset user profile",
    description="Reset user profile to defaults (requires system.manage_settings permission)"
)
@require_perm("system.manage_settings")
async def reset_user_profile(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[dict]:
    """
    Reset user profile (for testing/dev).

    WARNING: This clears all user profile data.
    Requires system.manage_settings permission.

    Returns:
        Reset confirmation
    """
    from api.services import users

    try:
        result = await users.reset_user_profile()
        return SuccessResponse(
            data=result,
            message="User profile reset successfully"
        )

    except HTTPException:
        raise  # Re-raise FastAPI exceptions

    except Exception as e:
        logger.error(f"Failed to reset user profile", exc_info=True)
        raise http_500("Failed to reset user profile")
