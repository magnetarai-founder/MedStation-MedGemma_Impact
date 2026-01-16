"""
Compatibility Shim for Panic Mode Types

The implementation now lives in the `api.panic_mode` package:
- api.panic_mode.types: Request/response models

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.panic_mode.types import (
    PanicTriggerRequest,
    PanicStatusResponse,
    PanicTriggerResponse,
    EmergencyModeRequest,
    EmergencyModeResponse,
)

__all__ = [
    "PanicTriggerRequest",
    "PanicStatusResponse",
    "PanicTriggerResponse",
    "EmergencyModeRequest",
    "EmergencyModeResponse",
]
