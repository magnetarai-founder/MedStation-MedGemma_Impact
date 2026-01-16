"""
Compatibility Shim for Offline Mesh Discovery

The implementation now lives in the `api.offline` package:
- api.offline.mesh_discovery: OfflineMeshDiscovery class

This shim maintains backward compatibility.
"""

from api.offline.mesh_discovery import (
    LocalPeer,
    OfflineMeshDiscovery,
    get_mesh_discovery,
)

__all__ = [
    "LocalPeer",
    "OfflineMeshDiscovery",
    "get_mesh_discovery",
]
