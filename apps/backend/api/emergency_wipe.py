"""
Compatibility Shim for Emergency Wipe

The implementation now lives in the `api.security` package:
- api.security.emergency_wipe: perform_dod_wipe, wipe_single_file

This shim maintains backward compatibility.
"""

from api.security.emergency_wipe import (
    perform_dod_wipe,
    wipe_single_file,
)

__all__ = [
    "perform_dod_wipe",
    "wipe_single_file",
]
