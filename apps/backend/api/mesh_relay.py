"""
Mesh Relay Routing for MedStation - Backwards Compatibility Shim

This file provides backwards compatibility after the mesh_relay module
was decomposed into a package during P2 monolithic file fixes.

The actual implementation is now in api/mesh/:
- security.py: SignedHandshake, verify_handshake_signature
- models.py: RouteMetrics, MeshMessage
- connection.py: MeshConnection, MeshConnectionPool
- relay.py: MeshRelay, get_mesh_relay

Import from api.mesh for new code.
"""

# Re-export everything from the package for backwards compatibility
from api.mesh import (
    # Security
    SignedHandshake,
    verify_handshake_signature,
    HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS,
    HANDSHAKE_NONCE_CACHE_MAX_SIZE,
    NACL_AVAILABLE,
    _check_handshake_nonce,
    _clear_nonce_cache,
    # Models
    RouteMetrics,
    MeshMessage,
    # Connection
    MeshConnection,
    MeshConnectionPool,
    WEBSOCKETS_AVAILABLE,
    # Relay
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
