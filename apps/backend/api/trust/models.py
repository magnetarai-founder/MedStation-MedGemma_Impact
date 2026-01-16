"""
MagnetarTrust - Trust Network Models

Part of MagnetarMission: Decentralized trust and resource-sharing network
for churches, missions, and humanitarian teams.

Phase 1: Trust Network MVP
"""

from datetime import UTC, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


# ===== Enums =====

class NodeType(str, Enum):
    """Type of trust node"""
    INDIVIDUAL = "individual"
    CHURCH = "church"
    MISSION = "mission"
    FAMILY = "family"
    ORGANIZATION = "organization"


class TrustLevel(str, Enum):
    """Level of trust relationship"""
    DIRECT = "direct"  # I know you personally
    VOUCHED = "vouched"  # Someone I trust vouches for you
    NETWORK = "network"  # 2-3 degrees of separation


class DisplayMode(str, Enum):
    """Display mode for node (peacetime vs persecution)"""
    PEACETIME = "peacetime"  # Full names, churches visible
    UNDERGROUND = "underground"  # Pseudonyms, codes only


# ===== Core Models =====

class TrustNode(BaseModel):
    """
    A node in the trust network.
    Can be an individual, church, mission, or organization.
    """
    id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:16]}")
    public_key: str  # For signing transactions and vouching

    # Identity (changes based on display_mode)
    public_name: str  # Real name/church name (peacetime mode)
    alias: Optional[str] = None  # Pseudonym/code (underground mode)

    # Node metadata
    type: NodeType
    display_mode: DisplayMode = DisplayMode.PEACETIME
    bio: Optional[str] = None
    location: Optional[str] = None  # Obfuscated in underground mode

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Network metadata
    is_hub: bool = False  # Churches/missions can be trust hubs
    vouched_by: Optional[str] = None  # node_id of voucher (if applicable)


class TrustRelationship(BaseModel):
    """
    A trust relationship between two nodes.
    Represents "from_node trusts to_node"
    """
    id: str = Field(default_factory=lambda: f"trust_{uuid.uuid4().hex[:16]}")

    from_node: str  # node_id doing the trusting
    to_node: str  # node_id being trusted

    level: TrustLevel
    vouched_by: Optional[str] = None  # node_id who vouched (if level=VOUCHED)

    # Timestamps
    established: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_verified: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Metadata
    note: Optional[str] = None  # Why I trust this person/org
    is_mutual: bool = False  # Does to_node also trust from_node?


# ===== Request/Response Models =====

class RegisterNodeRequest(BaseModel):
    """
    Request to register a new trust node.

    SECURITY: Registration now requires a signature proving ownership of the private key.
    The signature must be over the canonical payload (nonce + timestamp + public_key + public_name + type).
    This prevents MITM attacks where an attacker registers with a victim's public key.

    Replay Protection:
    - timestamp: Must be within 5 minutes (prevents old signature reuse)
    - nonce: 16-byte random value (prevents replay within timestamp window)
    """
    public_key: str  # Base64-encoded Ed25519 public key
    public_name: str
    type: NodeType
    alias: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    display_mode: DisplayMode = DisplayMode.PEACETIME

    # Security fields (required for authenticated registration)
    timestamp: str = Field(
        description="ISO 8601 timestamp of registration request (prevents replay attacks)"
    )
    nonce: str = Field(
        default="",
        description="Random 16-byte hex string for replay protection within timestamp window"
    )
    signature: str = Field(
        description="Base64-encoded Ed25519 signature over canonical payload"
    )

    def get_canonical_payload(self) -> str:
        """
        Get the canonical payload that was signed.
        Format: nonce|timestamp|public_key|public_name|type
        """
        return f"{self.nonce}|{self.timestamp}|{self.public_key}|{self.public_name}|{self.type.value}"


class VouchRequest(BaseModel):
    """Request to vouch for another node"""
    target_node_id: str  # Node being vouched for
    level: TrustLevel = TrustLevel.VOUCHED
    note: Optional[str] = None


class TrustNetworkResponse(BaseModel):
    """Response containing a node's trust network"""
    node_id: str
    direct_trusts: List[TrustNode]  # Nodes I directly trust
    vouched_trusts: List[TrustNode]  # Nodes vouched for by someone I trust
    network_trusts: List[TrustNode]  # 2-3 degrees out
    total_network_size: int


class NodeListResponse(BaseModel):
    """Response containing a list of trust nodes"""
    nodes: List[TrustNode]
    total: int


class TrustRelationshipResponse(BaseModel):
    """Response containing trust relationships"""
    relationships: List[TrustRelationship]
    total: int
