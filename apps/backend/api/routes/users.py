"""
Users router for ElohimOS - User profile management.

Thin router that delegates to api/services/users.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.

AUTH-P4: Sensitive operations protected with @require_perm decorators.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from api.permissions import require_perm

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"]
)


# Helper to get current user without importing at module level
def get_current_user_dep():
    """Lazy import of get_current_user dependency"""
    from api.auth_middleware import get_current_user
    return get_current_user


@router.get("/me", name="users_get_me")
async def get_current_user_endpoint(request: Request):
    """Get or create the current user profile"""
    from api.services import users
    from api.schemas.user_models import UserProfile

    try:
        return await users.get_or_create_user_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.put("/me", name="users_update_me")
async def update_current_user_endpoint(request: Request):
    """Update the current user profile"""
    from api.services import users
    from api.schemas.user_models import UserProfileUpdate

    try:
        # Parse request body
        body = await request.json()
        updates = UserProfileUpdate(**body)
        return await users.update_user_profile(updates.dict(exclude_unset=True))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")


# AUTH-P4: Tightened per AUTH-P4 - reset requires system.manage_settings permission
@router.post("/reset", name="users_reset")
@require_perm("system.manage_settings")
async def reset_user_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Reset user profile (for testing/dev) - Phase 0: only clears profiles, not auth"""
    from api.services import users

    try:
        return await users.reset_user_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset user profile: {str(e)}")
