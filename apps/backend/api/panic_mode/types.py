"""
Panic Mode Types - Request/response models for emergency security operations

Extracted from panic_mode_router.py during P2 decomposition.
Contains:
- PanicTriggerRequest, PanicTriggerResponse (panic mode activation)
- PanicStatusResponse (current status)
- EmergencyModeRequest, EmergencyModeResponse (DoD 7-pass wipe)
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class PanicTriggerRequest(BaseModel):
    """Request to trigger panic mode"""
    confirmation: str = Field(..., description="Must be 'CONFIRM' to proceed")
    reason: Optional[str] = Field("Manual trigger", description="Reason for panic activation")


class PanicStatusResponse(BaseModel):
    """Current panic mode status"""
    panic_active: bool
    last_panic: Optional[str]
    secure_mode: bool


class PanicTriggerResponse(BaseModel):
    """Response after triggering panic mode"""
    panic_activated: bool
    timestamp: str
    reason: str
    actions_taken: list[str]
    errors: list[str]
    status: str


class EmergencyModeRequest(BaseModel):
    """Request to trigger emergency mode (DoD 7-pass wipe)"""
    confirmation: str = Field(..., description="Must be 'CONFIRM' to proceed")
    reason: Optional[str] = Field("User-initiated emergency", description="Reason for emergency activation")


class EmergencyModeResponse(BaseModel):
    """Response after emergency mode wipe"""
    success: bool
    files_wiped: int
    passes: int
    method: str
    duration_seconds: float
    timestamp: str
    errors: List[str] = []


__all__ = [
    "PanicTriggerRequest",
    "PanicStatusResponse",
    "PanicTriggerResponse",
    "EmergencyModeRequest",
    "EmergencyModeResponse",
]
