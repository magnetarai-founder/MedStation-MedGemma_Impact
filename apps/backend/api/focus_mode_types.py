"""
Compatibility Shim for Focus Mode Types

The implementation now lives in the `api.focus_mode` package:
- api.focus_mode.types: Enums and Pydantic models

This shim maintains backward compatibility.
"""

from api.focus_mode.types import (
    FocusMode,
    FocusModeConfig,
    FocusModeState,
)

__all__ = [
    "FocusMode",
    "FocusModeConfig",
    "FocusModeState",
]
