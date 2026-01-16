"""
Founder Setup Types - Request/response models for founder password setup

Extracted from founder_setup_routes.py during P2 decomposition.
Contains:
- SetupStatusResponse (setup status check)
- InitializeSetupRequest, InitializeSetupResponse (password initialization)
- VerifyPasswordRequest, VerifyPasswordResponse (password verification)
"""

from pydantic import BaseModel
from typing import Optional


class SetupStatusResponse(BaseModel):
    """Setup status response"""
    setup_completed: bool
    setup_timestamp: Optional[str] = None
    password_storage_type: Optional[str] = None
    is_macos: bool


class InitializeSetupRequest(BaseModel):
    """Initialize setup request"""
    password: str
    confirm_password: str


class InitializeSetupResponse(BaseModel):
    """Initialize setup response"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    storage_type: Optional[str] = None


class VerifyPasswordRequest(BaseModel):
    """Verify password request"""
    password: str


class VerifyPasswordResponse(BaseModel):
    """Verify password response"""
    valid: bool


__all__ = [
    "SetupStatusResponse",
    "InitializeSetupRequest",
    "InitializeSetupResponse",
    "VerifyPasswordRequest",
    "VerifyPasswordResponse",
]
