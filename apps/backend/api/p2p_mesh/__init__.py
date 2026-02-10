"""
P2P Mesh Package

Peer-to-peer mesh networking for MedStation:
- Connection code management
- Peer discovery and diagnostics
- Mesh network API endpoints
"""

from api.p2p_mesh.models import (
    ConnectionCode,
    AddPeerRequest,
    P2PMeshPeer,
    DiagnosticCheck,
    DiagnosticsResponse,
    RunChecksResponse,
)
from api.p2p_mesh.db import (
    PATHS,
    CODES_DB_PATH,
    init_codes_db,
    save_connection_code,
    load_connection_codes,
    generate_connection_code,
)
from api.p2p_mesh.service import router

__all__ = [
    # Models
    "ConnectionCode",
    "AddPeerRequest",
    "P2PMeshPeer",
    "DiagnosticCheck",
    "DiagnosticsResponse",
    "RunChecksResponse",
    # Database
    "PATHS",
    "CODES_DB_PATH",
    "init_codes_db",
    "save_connection_code",
    "load_connection_codes",
    "generate_connection_code",
    # Router
    "router",
]
