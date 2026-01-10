"""
P2P Mesh Models - Pydantic models for P2P mesh service

Provides request/response models for:
- Connection codes (peer pairing)
- Peer information
- Diagnostics results

Extracted from p2p_mesh_service.py during P2 decomposition.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ConnectionCode(BaseModel):
    """
    Connection code for pairing peers.

    Format: OMNI-XXXX-XXXX (human-readable)
    Contains peer_id and multiaddrs for libp2p connection.
    """
    code: str
    peer_id: str
    multiaddrs: List[str]
    expires_at: Optional[str] = None


class AddPeerRequest(BaseModel):
    """Request to add peer by connection code."""
    code: str


class P2PMeshPeer(BaseModel):
    """
    Peer information for NetworkSelector UI.

    Simplified view of a P2P peer for display purposes.
    """
    id: str
    name: str
    location: Optional[str] = None
    connected: bool


# ===== Diagnostics Models =====

class DiagnosticCheck(BaseModel):
    """
    Single diagnostic check result.

    Used by the diagnostics endpoint to report individual check status.
    """
    name: str
    ok: bool
    message: str
    remediation: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    """
    P2P diagnostics overview response.

    High-level status of mDNS, port accessibility, and peer discovery.
    """
    mdns_ok: bool
    port_8000_open: bool
    peer_count: int
    hints: List[str]


class RunChecksResponse(BaseModel):
    """
    Detailed diagnostic checks response.

    Contains individual check results with pass/fail and remediation steps.
    """
    checks: List[DiagnosticCheck]


__all__ = [
    # Connection code models
    "ConnectionCode",
    "AddPeerRequest",
    # Peer models
    "P2PMeshPeer",
    # Diagnostics models
    "DiagnosticCheck",
    "DiagnosticsResponse",
    "RunChecksResponse",
]
