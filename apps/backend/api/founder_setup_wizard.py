"""Backward Compatibility Shim - use api.founder_setup instead."""

from api.founder_setup.wizard import (
    FounderSetupWizard,
    get_founder_wizard,
    logger,
)

__all__ = [
    "FounderSetupWizard",
    "get_founder_wizard",
    "logger",
]
