"""
Compatibility Shim for Panic Mode Service

The implementation now lives in the `api.panic_mode` package:
- api.panic_mode.service: PanicMode class and get_panic_mode function

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.panic_mode.service import (
    PanicMode,
    get_panic_mode,
)

__all__ = [
    "PanicMode",
    "get_panic_mode",
]
