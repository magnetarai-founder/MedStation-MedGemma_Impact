"""
Founder Setup Package

Provides first-time founder password setup functionality:
- One-time password initialization
- macOS Keychain integration for secure storage
- Strong password validation
- API endpoints for setup wizard
"""

from api.founder_setup.types import (
    SetupStatusResponse,
    InitializeSetupRequest,
    InitializeSetupResponse,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
)
from api.founder_setup.wizard import get_founder_wizard, FounderSetupWizard
from api.founder_setup.routes import router

__all__ = [
    # Types
    "SetupStatusResponse",
    "InitializeSetupRequest",
    "InitializeSetupResponse",
    "VerifyPasswordRequest",
    "VerifyPasswordResponse",
    # Wizard
    "get_founder_wizard",
    "FounderSetupWizard",
    # Router
    "router",
]
