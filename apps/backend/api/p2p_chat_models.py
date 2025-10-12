"""
P2P Team Chat Data Models
Secure, offline-first peer-to-peer messaging for missionary teams
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MessageType(str, Enum):
    """Types of messages in the P2P network"""
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"
    TYPING = "typing"
    PRESENCE = "presence"
    ACK = "ack"


class ChannelType(str, Enum):
    """Types of communication channels"""
    PUBLIC = "public"  # Everyone in the network can see
    PRIVATE = "private"  # Invite-only channel
    DIRECT = "direct"  # 1-on-1 DM


class PeerStatus(str, Enum):
    """Peer connection status"""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


# ===== Core Models =====

class Peer(BaseModel):
    """Represents a peer in the network"""
    peer_id: str  # libp2p peer ID
    display_name: str
    device_name: str  # e.g., "John's MacBook Pro"
    public_key: str  # For message encryption
    status: PeerStatus = PeerStatus.OFFLINE
    last_seen: str  # ISO timestamp
    multiaddrs: List[str] = Field(default_factory=list)  # libp2p multiaddresses

    # Optional metadata
    avatar_hash: Optional[str] = None  # IPFS hash of avatar image
    bio: Optional[str] = None


class Channel(BaseModel):
    """A communication channel (public, private, or DM)"""
    id: str = Field(default_factory=lambda: f"ch_{uuid.uuid4().hex[:12]}")
    name: str
    type: ChannelType
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str  # peer_id of creator

    # Members
    members: List[str] = Field(default_factory=list)  # peer_ids
    admins: List[str] = Field(default_factory=list)  # peer_ids with admin rights

    # Channel metadata
    description: Optional[str] = None
    topic: Optional[str] = None
    pinned_messages: List[str] = Field(default_factory=list)  # message IDs

    # For DMs (type=DIRECT)
    dm_participants: Optional[List[str]] = None  # Exactly 2 peer_ids


class Message(BaseModel):
    """A message in a channel"""
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:16]}")
    channel_id: str
    sender_id: str  # peer_id
    sender_name: str  # Display name at time of sending

    # Content
    type: MessageType
    content: str  # Text content or file description
    encrypted: bool = True  # All messages encrypted by default

    # Timestamps
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    edited_at: Optional[str] = None

    # File attachments (if type=FILE)
    file_metadata: Optional[Dict[str, Any]] = None  # {name, size, hash, mime_type}

    # Message threading
    thread_id: Optional[str] = None  # For threaded replies
    reply_to: Optional[str] = None  # ID of message being replied to

    # Reactions
    reactions: Dict[str, List[str]] = Field(default_factory=dict)  # {emoji: [peer_ids]}

    # Delivery tracking
    delivered_to: List[str] = Field(default_factory=list)  # peer_ids that received it
    read_by: List[str] = Field(default_factory=list)  # peer_ids that read it


class FileTransfer(BaseModel):
    """Represents a file being transferred over P2P"""
    id: str = Field(default_factory=lambda: f"ft_{uuid.uuid4().hex[:12]}")
    file_name: str
    file_size: int
    file_hash: str  # SHA256 hash for integrity
    mime_type: str

    # Transfer info
    sender_id: str
    recipient_ids: List[str]
    channel_id: Optional[str] = None

    # Progress tracking
    chunks_total: int
    chunks_received: int = 0
    progress_percent: float = 0.0

    # Status
    status: str = "pending"  # pending, transferring, completed, failed
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Storage
    local_path: Optional[str] = None  # Where file is saved locally


class TypingIndicator(BaseModel):
    """Someone is typing..."""
    channel_id: str
    peer_id: str
    display_name: str
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ===== Request/Response Models =====

class CreateChannelRequest(BaseModel):
    """Request to create a new channel"""
    name: str
    type: ChannelType
    description: Optional[str] = None
    topic: Optional[str] = None
    members: List[str] = Field(default_factory=list)  # peer_ids to invite


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    channel_id: str
    content: str
    type: MessageType = MessageType.TEXT
    reply_to: Optional[str] = None
    file_metadata: Optional[Dict[str, Any]] = None


class CreateDMRequest(BaseModel):
    """Request to create a direct message"""
    peer_id: str  # Who to DM


class InviteToChannelRequest(BaseModel):
    """Invite peers to a channel"""
    channel_id: str
    peer_ids: List[str]


class UpdatePresenceRequest(BaseModel):
    """Update user's presence status"""
    status: PeerStatus
    custom_status: Optional[str] = None


# ===== Response Models =====

class PeerListResponse(BaseModel):
    """List of discovered peers"""
    peers: List[Peer]
    total: int


class ChannelListResponse(BaseModel):
    """List of channels"""
    channels: List[Channel]
    total: int


class MessageListResponse(BaseModel):
    """List of messages in a channel"""
    channel_id: str
    messages: List[Message]
    total: int
    has_more: bool = False


class P2PStatusResponse(BaseModel):
    """Status of P2P network"""
    peer_id: str
    is_connected: bool
    discovered_peers: int
    active_channels: int
    multiaddrs: List[str]
