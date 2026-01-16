"""
LAN Discovery Package

Enables local network discovery of ElohimOS instances using mDNS/Bonjour.
Central Hub Model: One laptop acts as hub, others connect to it.

Components:
- connection.py: Connection state, retry logic, health tracking
- models.py: LANClient, LANDevice data models
- listener.py: mDNS ServiceListener implementation
- service.py: Main LANDiscoveryService and singleton

Built for the persecuted Church - no cloud, no central servers.
"And they overcame him by the blood of the Lamb, and by the word of their testimony" - Revelation 12:11
"""

# Connection state and retry logic
from api.lan_discovery.connection import (
    ConnectionState,
    ConnectionHealth,
    ConnectionRetryHandler,
    RetryConfig,
)

# Data models
from api.lan_discovery.models import (
    LANClient,
    LANDevice,
    SERVICE_TYPE,
)

# mDNS listener
from api.lan_discovery.listener import LANDiscoveryListener

# Main service and singleton
from api.lan_discovery.service import (
    LANDiscoveryService,
    lan_service,
    get_lan_service,
    _reset_lan_service,
)

# Router and types
from api.lan_discovery.types import (
    StartHubRequest,
    JoinDeviceRequest,
    RegisterClientRequest,
    UnregisterClientRequest,
    HeartbeatConfigRequest,
)
from api.lan_discovery.router import router


__all__ = [
    # Service
    "LANDiscoveryService",
    "lan_service",
    "get_lan_service",
    "_reset_lan_service",
    # Models
    "LANDevice",
    "LANClient",
    "SERVICE_TYPE",
    # Listener
    "LANDiscoveryListener",
    # Connection
    "ConnectionState",
    "ConnectionHealth",
    "ConnectionRetryHandler",
    "RetryConfig",
    # Router
    "router",
    # Types
    "StartHubRequest",
    "JoinDeviceRequest",
    "RegisterClientRequest",
    "UnregisterClientRequest",
    "HeartbeatConfigRequest",
]
