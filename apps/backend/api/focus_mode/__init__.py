"""
Focus Mode Package

Focus mode management for ElohimOS:
- Quiet Mode: Muted colors, distraction-free
- Field Mode: High contrast, battery saver
- Emergency Mode: Critical functions only
"""

from api.focus_mode.types import (
    FocusMode,
    FocusModeConfig,
    FocusModeState,
)
from api.focus_mode.service import FocusModeService

__all__ = [
    "FocusMode",
    "FocusModeConfig",
    "FocusModeState",
    "FocusModeService",
]
