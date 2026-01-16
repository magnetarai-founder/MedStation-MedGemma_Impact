"""
Compatibility Shim for LAN Types

The implementation now lives in the `api.lan_discovery` package:
- api.lan_discovery.types: Request models

This shim maintains backward compatibility.
"""

from api.lan_discovery.types import (
    StartHubRequest,
    JoinDeviceRequest,
    RegisterClientRequest,
    UnregisterClientRequest,
    HeartbeatConfigRequest,
)

__all__ = [
    "StartHubRequest",
    "JoinDeviceRequest",
    "RegisterClientRequest",
    "UnregisterClientRequest",
    "HeartbeatConfigRequest",
]
