"""
Compatibility Shim for Focus Mode Service

The implementation now lives in the `api.focus_mode` package:
- api.focus_mode.service: FocusModeService class

This shim maintains backward compatibility.
"""

from api.focus_mode.service import FocusModeService
from api.focus_mode.types import (
    FocusMode,
    FocusModeConfig,
    FocusModeState,
)

__all__ = [
    "FocusModeService",
    "FocusMode",
    "FocusModeConfig",
    "FocusModeState",
]
