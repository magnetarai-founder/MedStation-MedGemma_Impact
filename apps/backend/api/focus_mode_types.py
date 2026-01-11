"""
Focus Mode Types - Enums and models for focus mode functionality

Extracted from focus_mode_service.py during P2 decomposition.
Contains:
- FocusMode enum (focus mode types)
- FocusModeConfig model (mode configuration)
- FocusModeState model (current mode state)
"""

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel


class FocusMode(str, Enum):
    """Focus mode types

    Modes:
    - QUIET: Muted colors, subtle animations, distraction-free
    - FIELD: High contrast, battery saver, optimized for outdoor use
    - EMERGENCY: Critical functions only, auto-trigger on low battery
    """
    QUIET = "quiet"
    FIELD = "field"
    EMERGENCY = "emergency"


class FocusModeConfig(BaseModel):
    """Configuration for a focus mode

    Attributes:
        mode: Focus mode type
        enabled: Whether mode is enabled
        auto_trigger_battery: Battery % to auto-trigger (None = disabled)
        auto_trigger_panic: Whether to trigger on panic mode
        preferences: Additional mode-specific preferences
    """
    mode: FocusMode
    enabled: bool = True
    auto_trigger_battery: Optional[int] = None
    auto_trigger_panic: bool = False
    preferences: Dict[str, Any] = {}


class FocusModeState(BaseModel):
    """Current focus mode state

    Attributes:
        current_mode: Currently active focus mode
        previous_mode: Previous focus mode (for restoration)
        changed_at: When mode was last changed
        changed_by: User who changed the mode
        trigger_reason: Reason for change ("manual", "battery", "panic")
        battery_level: Battery level when mode was changed
    """
    current_mode: FocusMode
    previous_mode: Optional[FocusMode] = None
    changed_at: str
    changed_by: Optional[str] = None
    trigger_reason: Optional[str] = None
    battery_level: Optional[int] = None


__all__ = [
    # Enum
    "FocusMode",
    # Models
    "FocusModeConfig",
    "FocusModeState",
]
