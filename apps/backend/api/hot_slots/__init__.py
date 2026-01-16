"""
Hot Slots Package

Model hot slot management for ElohimOS:
- 4 slots with LRU eviction
- Pinning support
- REST API endpoints
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
