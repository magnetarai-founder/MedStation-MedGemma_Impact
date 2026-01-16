"""
Compatibility Shim for P2P Mesh Models

The implementation now lives in the `api.p2p_mesh` package:
- api.p2p_mesh.models: P2P mesh data models

This shim maintains backward compatibility.
"""

from api.p2p_mesh.models import (
    ConnectionCode,
    AddPeerRequest,
    P2PMeshPeer,
    DiagnosticCheck,
    DiagnosticsResponse,
    RunChecksResponse,
)

__all__ = [
    "ConnectionCode",
    "AddPeerRequest",
    "P2PMeshPeer",
    "DiagnosticCheck",
    "DiagnosticsResponse",
    "RunChecksResponse",
]
