#!/usr/bin/env python3
"""
Hot Slot Management API Router
Phase 2: Hot Slot Management - HTTP API Layer

Provides REST endpoints for managing model hot slots (4 slots with LRU eviction and pinning).
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any
import logging

from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["hot_slots"])


# ===== Request/Response Models =====

class HotSlot(BaseModel):
    """Hot slot state"""
    slotNumber: int = Field(..., alias="slot_number")
    modelId: str | None = Field(None, alias="model_id")
    modelName: str | None = Field(None, alias="model_name")
    isPinned: bool = Field(False, alias="is_pinned")
    loadedAt: str | None = Field(None, alias="loaded_at")  # ISO timestamp
    lastUsed: str | None = Field(None, alias="last_used")  # ISO timestamp

    class Config:
        populate_by_name = True


class HotSlotsResponse(BaseModel):
    """Response for GET /hot-slots"""
    slots: list[HotSlot]
    totalSlots: int = Field(4, alias="total_slots")
    occupied: int
    available: int

    class Config:
        populate_by_name = True


class LoadSlotRequest(BaseModel):
    """Request for POST /hot-slots/{slot}/load"""
    modelId: str = Field(..., alias="model_id")
    pin: bool = False  # Whether to pin this model

    class Config:
        populate_by_name = True


class SlotOperationResponse(BaseModel):
    """Generic response for slot operations"""
    success: bool
    slotNumber: int = Field(..., alias="slot_number")
    modelId: str | None = Field(None, alias="model_id")
    message: str
    hotSlots: dict[int, str | None] = Field(..., alias="hot_slots")

    class Config:
        populate_by_name = True


# ===== Endpoints =====

@router.get("/hot-slots", response_model=HotSlotsResponse)
async def get_hot_slots(current_user = Depends(get_current_user)):
    """
    Get current hot slot assignments

    Returns all 4 hot slots with their current assignments, pinned status, and timestamps.
    """
    try:
        from api.services.hot_slots_metadata import get_metadata_storage

        # Get metadata storage
        storage = get_metadata_storage()
        user_id = current_user.get("username", "founder")

        # Get all slots with metadata
        all_slots = storage.get_all_slots(user_id)

        # Convert to response
        slots = []
        occupied_count = 0

        for slot_meta in all_slots:
            if slot_meta.model_name:
                occupied_count += 1

            slots.append(HotSlot(
                slot_number=slot_meta.slot_number,
                model_id=slot_meta.model_name,
                model_name=slot_meta.model_name,
                is_pinned=slot_meta.is_pinned,
                loaded_at=slot_meta.loaded_at.isoformat() if slot_meta.loaded_at else None,
                last_used=slot_meta.last_used.isoformat() if slot_meta.last_used else None
            ))

        return HotSlotsResponse(
            slots=slots,
            total_slots=4,
            occupied=occupied_count,
            available=4 - occupied_count
        )

    except Exception as e:
        logger.error(f"Failed to get hot slots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get hot slots: {str(e)}")


@router.post("/hot-slots/{slot_number}/load", response_model=SlotOperationResponse)
async def load_model_to_slot(
    slot_number: int,
    request: LoadSlotRequest,
    current_user = Depends(get_current_user)
):
    """
    Load a model into a specific hot slot

    If the slot is occupied, the existing model will be unloaded (unless pinned).
    If the model is already in another slot, it will be moved to the new slot.
    """
    # Validate slot number
    if slot_number < 1 or slot_number > 4:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    try:
        from api.services.chat.hot_slots import assign_to_hot_slot
        from api.services.hot_slots_metadata import get_metadata_storage

        # Assign model to slot (handles eviction automatically)
        result = await assign_to_hot_slot(slot_number, request.modelId)

        # Store metadata with pinning
        storage = get_metadata_storage()
        user_id = current_user.get("username", "founder")

        storage.load_model_to_slot(
            user_id=user_id,
            slot_number=slot_number,
            model_name=request.modelId,
            pin=request.pin
        )

        return SlotOperationResponse(
            success=result["success"],
            slot_number=slot_number,
            model_id=request.modelId,
            message=f"Model '{request.modelId}' loaded to slot {slot_number}" + (" (pinned)" if request.pin else ""),
            hot_slots=result["hot_slots"]
        )

    except Exception as e:
        logger.error(f"Failed to load model to slot {slot_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model to slot: {str(e)}"
        )


@router.post("/hot-slots/{slot_number}/unload", response_model=SlotOperationResponse)
async def unload_model_from_slot(
    slot_number: int,
    current_user = Depends(get_current_user)
):
    """
    Unload a model from a specific hot slot

    If the slot is empty, returns success.
    If the model is pinned, returns error.
    """
    # Validate slot number
    if slot_number < 1 or slot_number > 4:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    try:
        from api.services.chat.hot_slots import remove_from_hot_slot
        from api.services.hot_slots_metadata import get_metadata_storage

        # Check if slot is pinned
        storage = get_metadata_storage()
        user_id = current_user.get("username", "founder")

        slot_meta = storage.get_slot_metadata(user_id, slot_number)
        if slot_meta and slot_meta.is_pinned:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot unload slot {slot_number}: model is pinned"
            )

        # Remove model from slot
        result = await remove_from_hot_slot(slot_number)

        # Remove metadata
        storage.unload_slot(user_id, slot_number)

        return SlotOperationResponse(
            success=result["success"],
            slot_number=slot_number,
            model_id=result.get("model"),
            message=f"Model unloaded from slot {slot_number}",
            hot_slots=result["hot_slots"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unload model from slot {slot_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unload model from slot: {str(e)}"
        )


@router.patch("/hot-slots/{slot_number}/pin", response_model=SlotOperationResponse)
async def toggle_slot_pin(
    slot_number: int,
    current_user = Depends(get_current_user)
):
    """
    Toggle pin status for a hot slot

    Pinned slots are protected from LRU eviction.
    If the slot is empty, returns error.
    """
    # Validate slot number
    if slot_number < 1 or slot_number > 4:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    try:
        from api.services.chat.hot_slots import get_hot_slots
        from api.services.hot_slots_metadata import get_metadata_storage

        # Toggle pin in metadata storage
        storage = get_metadata_storage()
        user_id = current_user.get("username", "founder")

        new_pin_status = storage.toggle_pin(user_id, slot_number)

        if new_pin_status is None:
            raise HTTPException(status_code=400, detail=f"Slot {slot_number} is empty")

        # Get current slots
        hot_slots_dict = await get_hot_slots()
        model_name = hot_slots_dict.get(slot_number)

        return SlotOperationResponse(
            success=True,
            slot_number=slot_number,
            model_id=model_name,
            message=f"Slot {slot_number} {'pinned' if new_pin_status else 'unpinned'}",
            hot_slots=hot_slots_dict
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle pin for slot {slot_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle pin status: {str(e)}"
        )


@router.post("/hot-slots/load-all")
async def load_all_hot_slot_models(
    keep_alive: str = "1h",
    current_user = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Load all assigned hot slot models into memory

    Useful for preloading models on startup or after system restart.
    """
    try:
        from api.services.chat.hot_slots import load_hot_slot_models

        result = await load_hot_slot_models(keep_alive)

        return {
            "success": True,
            "total_loaded": result["total"],
            "results": result["results"],
            "keep_alive": result["keep_alive"]
        }

    except Exception as e:
        logger.error(f"Failed to load all hot slot models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load models: {str(e)}"
        )
