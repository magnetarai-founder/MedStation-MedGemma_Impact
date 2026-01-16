"""
Compatibility Shim for LAN Service

The implementation now lives in the `api.lan_discovery` package:
- api.lan_discovery.router: API endpoints
- api.lan_discovery.types: Request models

This shim maintains backward compatibility.
"""

from api.lan_discovery import (
    lan_service,
    router,
    StartHubRequest,
    JoinDeviceRequest,
    RegisterClientRequest,
    UnregisterClientRequest,
    HeartbeatConfigRequest,
)

__all__ = [
    # Service singleton
    "lan_service",
    # Router
    "router",
    # Types
    "StartHubRequest",
    "JoinDeviceRequest",
    "RegisterClientRequest",
    "UnregisterClientRequest",
    "HeartbeatConfigRequest",
]
