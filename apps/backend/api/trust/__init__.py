"""
Trust Package

MagnetarTrust - Decentralized trust network for churches, missions, and humanitarian teams:
- Trust node management
- Vouching and trust relationships
- Ed25519 signature verification
- Local-first SQLite storage
"""

from api.trust.models import (
    NodeType,
    TrustLevel,
    DisplayMode,
    TrustNode,
    TrustRelationship,
    RegisterNodeRequest,
    VouchRequest,
    TrustNetworkResponse,
    NodeListResponse,
    TrustRelationshipResponse,
)
from api.trust.storage import TrustStorage, get_trust_storage

# Router import is lazy to avoid requiring nacl package
# Use: from api.trust.router import router

__all__ = [
    # Enums
    "NodeType",
    "TrustLevel",
    "DisplayMode",
    # Models
    "TrustNode",
    "TrustRelationship",
    "RegisterNodeRequest",
    "VouchRequest",
    "TrustNetworkResponse",
    "NodeListResponse",
    "TrustRelationshipResponse",
    # Storage
    "TrustStorage",
    "get_trust_storage",
]
