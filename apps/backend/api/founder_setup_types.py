"""Backward Compatibility Shim - use api.founder_setup instead."""

from api.founder_setup.types import (
    SetupStatusResponse,
    InitializeSetupRequest,
    InitializeSetupResponse,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
)

__all__ = [
    "SetupStatusResponse",
    "InitializeSetupRequest",
    "InitializeSetupResponse",
    "VerifyPasswordRequest",
    "VerifyPasswordResponse",
]
