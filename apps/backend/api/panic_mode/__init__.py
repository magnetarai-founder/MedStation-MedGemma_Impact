"""
Panic Mode Package

Emergency security system for MagnetarStudio:
- Rapid data wiping for hostile situations
- P2P connection termination
- Database encryption/securing
- DoD 7-pass emergency wipe capability
"""

from api.panic_mode.types import (
    PanicTriggerRequest,
    PanicStatusResponse,
    PanicTriggerResponse,
    EmergencyModeRequest,
    EmergencyModeResponse,
)
from api.panic_mode.service import (
    PanicMode,
    get_panic_mode,
)
from api.panic_mode.router import router

__all__ = [
    # Types
    "PanicTriggerRequest",
    "PanicStatusResponse",
    "PanicTriggerResponse",
    "EmergencyModeRequest",
    "EmergencyModeResponse",
    # Service
    "PanicMode",
    "get_panic_mode",
    # Router
    "router",
]
