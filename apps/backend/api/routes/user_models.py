"""
User Models API Routes

Per-user model preferences and hot slots endpoints.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

try:
    from ..services.model_preferences_storage import get_model_preferences_storage
    from ..services.hot_slots_storage import get_hot_slots_storage
    from ..services.model_catalog import get_model_catalog
    from ..auth_middleware import get_current_user
    from ..permission_engine import require_perm
except ImportError:
    from api.services.model_preferences_storage import get_model_preferences_storage
    from api.services.hot_slots_storage import get_hot_slots_storage
    from api.services.model_catalog import get_model_catalog
    from api.auth_middleware import get_current_user
    from api.permission_engine import require_perm

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from datetime import UTC

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

@router.get(
    "/users/me/setup/status",
    response_model=SuccessResponse[UserSetupStatusResponse],
    status_code=status.HTTP_200_OK,
    name="users_get_setup_status",
    summary="Get user setup status",
    description="Get per-user setup completion status (requires chat.use permission)"
)
@require_perm("chat.use")
async def get_user_setup_status(current_user = Depends(get_current_user)) -> SuccessResponse[UserSetupStatusResponse]:
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

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="User ID not found in token"
                ).model_dump()
            )

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

        status_data = UserSetupStatusResponse(
            user_setup_completed=user_setup_completed,
            has_prefs=has_prefs,
            has_hot_slots=has_hot_slots,
            visible_count=visible_count
        )

        return SuccessResponse(
            data=status_data,
            message="User setup status retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get user setup status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve user setup status"
            ).model_dump()
        )

@router.get(
    "/users/me/models/preferences",
    response_model=SuccessResponse[ModelPreferencesResponse],
    status_code=status.HTTP_200_OK,
    name="users_get_model_preferences",
    summary="Get model preferences",
    description="Get user's model visibility preferences (requires chat.use permission)"
)
@require_perm("chat.use")
async def get_user_model_preferences(current_user = Depends(get_current_user)) -> SuccessResponse[ModelPreferencesResponse]:
    """
    Get user's model visibility preferences

    Returns list of models with visibility and display order settings.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="User ID not found in token"
                ).model_dump()
            )

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

        prefs_data = ModelPreferencesResponse(preferences=items)

        return SuccessResponse(
            data=prefs_data,
            message=f"Retrieved {len(items)} model preference{'s' if len(items) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get model preferences", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve model preferences"
            ).model_dump()
        )


@router.put(
    "/users/me/models/preferences",
    response_model=SuccessResponse[UpdateModelPreferencesResponse],
    status_code=status.HTTP_200_OK,
    name="users_update_model_preferences",
    summary="Update model preferences",
    description="Update user's model visibility preferences (requires chat.use permission)"
)
@require_perm("chat.use")
async def update_user_model_preferences(
    body: UpdateModelPreferencesRequest,
    current_user = Depends(get_current_user)
) -> SuccessResponse[UpdateModelPreferencesResponse]:
    """
    Update user's model visibility preferences

    Sets which models the user wants to see and their display order.
    Automatically clears hot slots for any models being hidden.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="User ID not found in token"
                ).model_dump()
            )

        # Find models being hidden
        hidden_models = [pref.model_name for pref in body.preferences if not pref.visible]

        # Atomic transaction: Update preferences + clear hot slots for hidden models
        import sqlite3
        from pathlib import Path

        db_path = Path.home() / ".elohim" / "app_db.sqlite3"
        conn = sqlite3.connect(str(db_path))

        try:
            cursor = conn.cursor()

            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")

            # 1. Clear hot slots for models being hidden
            if hidden_models:
                placeholders = ','.join('?' * len(hidden_models))
                cursor.execute(f"""
                    DELETE FROM user_hot_slots
                    WHERE user_id = ? AND model_name IN ({placeholders})
                """, (user_id, *hidden_models))

                cleared_slots = cursor.rowcount
                if cleared_slots > 0:
                    logger.info(f"Cleared {cleared_slots} hot slot(s) for hidden models: {hidden_models}")

            # 2. Update preferences
            from datetime import datetime
            now = datetime.now(UTC).isoformat()

            for pref in body.preferences:
                # Upsert preference
                cursor.execute("""
                    INSERT INTO user_model_preferences
                    (user_id, model_name, visible, preferred, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, model_name) DO UPDATE SET
                        visible = excluded.visible,
                        preferred = excluded.preferred,
                        display_order = excluded.display_order,
                        updated_at = excluded.updated_at
                """, (
                    user_id,
                    pref.model_name,
                    1 if pref.visible else 0,
                    1 if pref.preferred else 0,
                    pref.display_order,
                    now,
                    now
                ))

            # Commit transaction
            conn.commit()

            update_data = UpdateModelPreferencesResponse(
                success=True,
                updated_count=len(body.preferences)
            )

            return SuccessResponse(
                data=update_data,
                message=f"Updated {len(body.preferences)} model preference{'s' if len(body.preferences) != 1 else ''}"
            )

        except Exception as e:
            # Rollback on any error
            conn.rollback()
            logger.error(f"Transaction failed, rolled back", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Failed to update preferences"
                ).model_dump()
            )
        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update model preferences", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update model preferences"
            ).model_dump()
        )


@router.get(
    "/users/me/models/hot-slots",
    response_model=SuccessResponse[HotSlotsResponse],
    status_code=status.HTTP_200_OK,
    name="users_get_hot_slots",
    summary="Get hot slots",
    description="Get user's hot slots configuration (requires chat.use permission)"
)
@require_perm("chat.use")
async def get_user_hot_slots(current_user = Depends(get_current_user)) -> SuccessResponse[HotSlotsResponse]:
    """
    Get user's hot slots configuration

    Returns mapping of slot numbers (1-4) to model names.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="User ID not found in token"
                ).model_dump()
            )

        hot_slots_storage = get_hot_slots_storage()
        slots = hot_slots_storage.get_hot_slots(user_id)

        slots_data = HotSlotsResponse(slots=slots)

        assigned_count = sum(1 for v in slots.values() if v is not None)

        return SuccessResponse(
            data=slots_data,
            message=f"Hot slots retrieved ({assigned_count} assigned)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get hot slots", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve hot slots"
            ).model_dump()
        )


@router.put(
    "/users/me/models/hot-slots",
    response_model=SuccessResponse[UpdateHotSlotsResponse],
    status_code=status.HTTP_200_OK,
    name="users_update_hot_slots",
    summary="Update hot slots",
    description="Update user's hot slots configuration (requires chat.use permission)"
)
@require_perm("chat.use")
async def update_user_hot_slots(
    body: UpdateHotSlotsRequest,
    current_user = Depends(get_current_user)
) -> SuccessResponse[UpdateHotSlotsResponse]:
    """
    Update user's hot slots configuration

    Assigns models to quick-access slots (1-4).
    Validates that assigned models are installed in Ollama.

    Requires authentication and 'chat.use' permission.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="User ID not found in token"
                ).model_dump()
            )

        # Validate slot numbers
        for slot_num in body.slots.keys():
            if slot_num not in [1, 2, 3, 4]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message=f"Invalid slot number: {slot_num} (must be 1-4)"
                    ).model_dump()
                )

        # Validate that assigned models are installed
        catalog = get_model_catalog()
        catalog_models = catalog.get_all_models()
        installed_models = {m.model_name for m in catalog_models if m.status == 'installed'}

        for slot_num, model_name in body.slots.items():
            if model_name and model_name not in installed_models:
                # Model not installed - reject with machine-readable error
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "model_not_installed",
                        "model": model_name,
                        "slot": slot_num,
                        "suggestion": "install_or_choose_other",
                        "message": f"Model '{model_name}' is not installed. Please install it from Ollama or choose another model."
                    }
                )

        # Update hot slots
        hot_slots_storage = get_hot_slots_storage()
        success = hot_slots_storage.set_hot_slots(user_id, body.slots)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Failed to update hot slots"
                ).model_dump()
            )

        assigned_count = sum(1 for v in body.slots.values() if v is not None)

        update_data = UpdateHotSlotsResponse(
            success=True,
            message=f"Hot slots updated ({assigned_count} assigned)"
        )

        return SuccessResponse(
            data=update_data,
            message=f"Hot slots updated ({assigned_count} assigned)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update hot slots", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update hot slots"
            ).model_dump()
        )


@router.get(
    "/models/catalog",
    response_model=SuccessResponse[ModelCatalogResponse],
    status_code=status.HTTP_200_OK,
    name="models_get_catalog",
    summary="Get model catalog",
    description="Get global model catalog (public endpoint - no authentication required)"
)
async def get_model_catalog_endpoint() -> SuccessResponse[ModelCatalogResponse]:
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

        catalog_data = ModelCatalogResponse(
            models=items,
            total_count=len(items)
        )

        return SuccessResponse(
            data=catalog_data,
            message=f"Retrieved {len(items)} model{'s' if len(items) != 1 else ''} from catalog"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get model catalog", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve model catalog"
            ).model_dump()
        )


# Export router
__all__ = ['router']
