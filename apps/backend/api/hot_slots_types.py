"""
Hot Slots Types - Request/response models for model hot slot management

Extracted from hot_slots_router.py during P2 decomposition.
Contains:
- HotSlot (slot state model)
- HotSlotsResponse (GET response)
- LoadSlotRequest (load model request)
- SlotOperationResponse (operation result)
"""

from pydantic import BaseModel, Field


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


__all__ = [
    "HotSlot",
    "HotSlotsResponse",
    "LoadSlotRequest",
    "SlotOperationResponse",
]
