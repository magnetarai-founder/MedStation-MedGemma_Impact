"""
Mesh Relay Package

Multi-hop message routing for peer-to-peer mesh networking.
Supports signed handshakes with Ed25519 for peer authentication.

Modules:
- security: SignedHandshake, verify_handshake_signature
- models: RouteMetrics, MeshMessage
- connection: MeshConnection, MeshConnectionPool
- relay: MeshRelay, get_mesh_relay
"""

from api.mesh.security import (
    SignedHandshake,
    verify_handshake_signature,
    HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS,
    HANDSHAKE_NONCE_CACHE_MAX_SIZE,
    NACL_AVAILABLE,
    _check_handshake_nonce,
    _clear_nonce_cache,
)

from api.mesh.models import (
    RouteMetrics,
    MeshMessage,
)

from api.mesh.connection import (
    MeshConnection,
    MeshConnectionPool,
    WEBSOCKETS_AVAILABLE,
)

from api.mesh.relay import (
    MeshRelay,
    get_mesh_relay,
    _reset_mesh_relay,
)

__all__ = [
    # Security
    "SignedHandshake",
    "verify_handshake_signature",
    "HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS",
    "HANDSHAKE_NONCE_CACHE_MAX_SIZE",
    "NACL_AVAILABLE",
    "_check_handshake_nonce",
    "_clear_nonce_cache",
    # Models
    "RouteMetrics",
    "MeshMessage",
    # Connection
    "MeshConnection",
    "MeshConnectionPool",
    "WEBSOCKETS_AVAILABLE",
    # Relay
    "MeshRelay",
    "get_mesh_relay",
    "_reset_mesh_relay",
]
