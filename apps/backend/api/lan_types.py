"""
LAN Service Types - Request models for LAN discovery and hub management

Extracted from lan_service.py during P2 decomposition.
Contains:
- StartHubRequest (hub startup config)
- JoinDeviceRequest (device connection)
- RegisterClientRequest, UnregisterClientRequest (client management)
- HeartbeatConfigRequest (connection health config)
"""

from pydantic import BaseModel
from typing import Optional


class StartHubRequest(BaseModel):
    """Request to start hub"""
    port: Optional[int] = 8765
    device_name: Optional[str] = None


class JoinDeviceRequest(BaseModel):
    """Request to join a discovered device"""
    device_id: str


class RegisterClientRequest(BaseModel):
    """Request from a client to register with this hub"""
    client_id: str
    client_name: str
    client_ip: str


class UnregisterClientRequest(BaseModel):
    """Request from a client to unregister from this hub"""
    client_id: str


class HeartbeatConfigRequest(BaseModel):
    """Request to configure heartbeat settings"""
    interval_seconds: Optional[float] = None
    auto_reconnect: Optional[bool] = None


__all__ = [
    "StartHubRequest",
    "JoinDeviceRequest",
    "RegisterClientRequest",
    "UnregisterClientRequest",
    "HeartbeatConfigRequest",
]
