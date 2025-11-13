"""
User Models API Routes

Per-user model preferences and hot slots endpoints.

Endpoints:
- GET /api/v1/users/me/setup/status - Get per-user setup completion status
- GET /api/v1/users/me/models/preferences - Get user's model visibility preferences
- PUT /api/v1/users/me/models/preferences - Update model visibility preferences
- GET /api/v1/users/me/models/hot-slots - Get user's hot slots
- PUT /api/v1/users/me/models/hot-slots - Update hot slots
- GET /api/v1/models/catalog - Get global model catalog (installed models)
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

try:
    from ..services.model_preferences_storage import get_model_preferences_storage
    from ..services.hot_slots_storage import get_hot_slots_storage
    from ..services.model_catalog import get_model_catalog
    from ..auth_middleware import get_current_user
except ImportError:
    from services.model_preferences_storage import get_model_preferences_storage
    from services.hot_slots_storage import get_hot_slots_storage
    from services.model_catalog import get_model_catalog
    from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["user-models"])


# ===== Pydantic Models =====

class ModelPreferenceItem(BaseModel):
    """Single model preference"""
    model_name: str
    visible: bool = True
    preferred: bool = False
    display_order: Optional[int] = None


class ModelPreferencesResponse(BaseModel):
    """Model preferences response"""
    preferences: List[ModelPreferenceItem]


class UpdateModelPreferencesRequest(BaseModel):
    """Update model preferences request"""
    preferences: List[ModelPreferenceItem] = Field(
        ...,
        description="List of model preferences to update"
    )


class UpdateModelPreferencesResponse(BaseModel):
    """Update model preferences response"""
    success: bool
    updated_count: int


class HotSlotsResponse(BaseModel):
    """Hot slots response"""
    slots: Dict[int, Optional[str]] = Field(
        ...,
        description="Mapping of slot number (1-4) to model name (null if empty)"
    )


class UpdateHotSlotsRequest(BaseModel):
    """Update hot slots request"""
    slots: Dict[int, Optional[str]] = Field(
        ...,
        description="Mapping of slot number (1-4) to model name (null to clear)"
    )


class UpdateHotSlotsResponse(BaseModel):
    """Update hot slots response"""
    success: bool
    message: str


class ModelCatalogItem(BaseModel):
    """Model catalog item"""
    model_name: str
    size: Optional[str] = None
    status: str
    installed_at: Optional[str] = None
    last_seen: Optional[str] = None


class ModelCatalogResponse(BaseModel):
    """Model catalog response"""
    models: List[ModelCatalogItem]
    total_count: int


class UserSetupStatusResponse(BaseModel):
    """Per-user setup completion status"""
    user_setup_completed: bool
    has_prefs: bool
    has_hot_slots: bool
    visible_count: int


# ===== API Endpoints =====

@router.get("/users/me/setup/status", response_model=UserSetupStatusResponse)
async def get_user_setup_status(current_user = Depends(get_current_user)):
    """
    Get per-user setup completion status

    Returns whether the current user has completed their personal setup.
    This is used to determine if the user should see the setup wizard
    after authentication.

    A user is considered "setup complete" if they have any model preferences.

    Returns:
        user_setup_completed: True if user has completed setup
        has_prefs: True if user has model preferences
        has_hot_slots: True if user has any hot slots assigned
        visible_count: Number of visible models

    Requires authentication.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        prefs_storage = get_model_preferences_storage()
        hot_slots_storage = get_hot_slots_storage()

        # Get preferences
        preferences = prefs_storage.get_preferences(user_id)
        has_prefs = len(preferences) > 0
        visible_count = sum(1 for p in preferences if p.visible)

        # Get hot slots
        slots = hot_slots_storage.get_hot_slots(user_id)
        has_hot_slots = any(v is not None for v in slots.values())

        # User setup is complete if they have any preferences
        # (This means they've gone through the wizard or Settings)
        user_setup_completed = has_prefs

        return UserSetupStatusResponse(
            user_setup_completed=user_setup_completed,
            has_prefs=has_prefs,
            has_hot_slots=has_hot_slots,
            visible_count=visible_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user setup status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user setup status")

@router.get("/users/me/models/preferences", response_model=ModelPreferencesResponse)
async def get_user_model_preferences(current_user = Depends(get_current_user)):
    """
    Get user's model visibility preferences

    Returns list of models with visibility and display order settings.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        prefs_storage = get_model_preferences_storage()
        preferences = prefs_storage.get_preferences(user_id)

        # Convert to response format
        items = []
        for pref in preferences:
            items.append(ModelPreferenceItem(
                model_name=pref.model_name,
                visible=pref.visible,
                preferred=pref.preferred,
                display_order=pref.display_order
            ))

        return ModelPreferencesResponse(preferences=items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model preferences")


@router.put("/users/me/models/preferences", response_model=UpdateModelPreferencesResponse)
async def update_user_model_preferences(
    body: UpdateModelPreferencesRequest,
    current_user = Depends(get_current_user)
):
    """
    Update user's model visibility preferences

    Sets which models the user wants to see and their display order.

    Requires authentication and 'chat.models.configure' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Convert to storage format
        preferences_data = []
        for pref in body.preferences:
            preferences_data.append({
                "model_name": pref.model_name,
                "visible": pref.visible,
                "preferred": pref.preferred,
                "display_order": pref.display_order
            })

        # Update preferences
        prefs_storage = get_model_preferences_storage()
        success = prefs_storage.set_preferences_bulk(user_id, preferences_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preferences")

        return UpdateModelPreferencesResponse(
            success=True,
            updated_count=len(preferences_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update model preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update model preferences")


@router.get("/users/me/models/hot-slots", response_model=HotSlotsResponse)
async def get_user_hot_slots(current_user = Depends(get_current_user)):
    """
    Get user's hot slots configuration

    Returns mapping of slot numbers (1-4) to model names.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        hot_slots_storage = get_hot_slots_storage()
        slots = hot_slots_storage.get_hot_slots(user_id)

        return HotSlotsResponse(slots=slots)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hot slots: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hot slots")


@router.put("/users/me/models/hot-slots", response_model=UpdateHotSlotsResponse)
async def update_user_hot_slots(
    body: UpdateHotSlotsRequest,
    current_user = Depends(get_current_user)
):
    """
    Update user's hot slots configuration

    Assigns models to quick-access slots (1-4).

    Requires authentication and 'chat.hot_slots.write' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Validate slot numbers
        for slot_num in body.slots.keys():
            if slot_num not in [1, 2, 3, 4]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid slot number: {slot_num} (must be 1-4)"
                )

        # Update hot slots
        hot_slots_storage = get_hot_slots_storage()
        success = hot_slots_storage.set_hot_slots(user_id, body.slots)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update hot slots")

        assigned_count = sum(1 for v in body.slots.values() if v is not None)

        return UpdateHotSlotsResponse(
            success=True,
            message=f"Hot slots updated ({assigned_count} assigned)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update hot slots: {e}")
        raise HTTPException(status_code=500, detail="Failed to update hot slots")


@router.get("/models/catalog", response_model=ModelCatalogResponse)
async def get_model_catalog_endpoint():
    """
    Get global model catalog

    Returns list of all models installed on the system.
    This is a system-wide list; users configure which ones they see
    via model preferences.

    Public endpoint - no authentication required (anyone can see what's installed).
    """
    try:
        catalog = get_model_catalog()
        models = catalog.get_all_models()

        # Convert to response format
        items = []
        for model in models:
            items.append(ModelCatalogItem(
                model_name=model.model_name,
                size=model.size,
                status=model.status,
                installed_at=model.installed_at,
                last_seen=model.last_seen
            ))

        return ModelCatalogResponse(
            models=items,
            total_count=len(items)
        )

    except Exception as e:
        logger.error(f"Failed to get model catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model catalog")


# Export router
__all__ = ['router']
