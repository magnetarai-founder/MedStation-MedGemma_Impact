"""
Compatibility Shim for Panic Mode Router

The implementation now lives in the `api.panic_mode` package:
- api.panic_mode.router: FastAPI router with endpoints
- api.panic_mode.types: Request/response models

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.panic_mode.router import router

# Re-export types for backwards compatibility
from api.panic_mode.types import (
    PanicTriggerRequest,
    PanicStatusResponse,
    PanicTriggerResponse,
    EmergencyModeRequest,
    EmergencyModeResponse,
)

__all__ = [
    "router",
    "PanicTriggerRequest",
    "PanicStatusResponse",
    "PanicTriggerResponse",
    "EmergencyModeRequest",
    "EmergencyModeResponse",
]
