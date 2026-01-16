"""
Compatibility Shim for Hot Slots Router

The implementation now lives in the `api.hot_slots` package:
- api.hot_slots.types: Request/response models
- api.hot_slots.router: API endpoints

This shim maintains backward compatibility.
"""

from api.hot_slots.types import (
    HotSlot,
    HotSlotsResponse,
    LoadSlotRequest,
    SlotOperationResponse,
)
from api.hot_slots.router import router

__all__ = [
    # Types
    "HotSlot",
    "HotSlotsResponse",
    "LoadSlotRequest",
    "SlotOperationResponse",
    # Router
    "router",
]
