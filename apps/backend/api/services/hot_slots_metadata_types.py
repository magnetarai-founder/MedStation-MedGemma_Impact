"""
Hot Slots Metadata Types - Dataclass for slot metadata

Extracted from hot_slots_metadata.py during P2 decomposition.
Contains:
- HotSlotMetadata (slot metadata dataclass)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HotSlotMetadata:
    """Metadata for a single hot slot"""
    slot_number: int
    model_name: Optional[str]
    is_pinned: bool
    loaded_at: Optional[datetime]
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: datetime


__all__ = [
    "HotSlotMetadata",
]
