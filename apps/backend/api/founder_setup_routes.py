"""Backward Compatibility Shim - use api.founder_setup instead."""

from api.founder_setup.routes import router, logger
from api.founder_setup.types import (
    SetupStatusResponse,
    InitializeSetupRequest,
    InitializeSetupResponse,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
)

__all__ = [
    "router",
    "logger",
    "SetupStatusResponse",
    "InitializeSetupRequest",
    "InitializeSetupResponse",
    "VerifyPasswordRequest",
    "VerifyPasswordResponse",
]
