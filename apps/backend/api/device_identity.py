"""
Compatibility Shim for Device Identity

The implementation now lives in the `api.security` package:
- api.security.device_identity: ensure_device_identity, get_device_identity

This shim maintains backward compatibility.
"""

from api.security.device_identity import (
    ensure_device_identity,
    get_device_identity,
)

__all__ = [
    "ensure_device_identity",
    "get_device_identity",
]
