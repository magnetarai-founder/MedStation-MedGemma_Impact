"""
Offline Mesh - Pydantic Models

Request and response models for offline mesh networking API.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class DiscoveryStartResponse(BaseModel):
    status: str
    peer_id: str
    display_name: str
    device_name: str


class PeerInfo(BaseModel):
    peer_id: str
    display_name: str
    device_name: str
    ip_address: str
    port: int
    capabilities: List[str]
    status: str
    last_seen: str


class PeersListResponse(BaseModel):
    count: int
    peers: List[PeerInfo]


class StatusResponse(BaseModel):
    status: str


class FileShareResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    sha256_hash: str
    shared_at: str


class RelayPeerResponse(BaseModel):
    status: str
    peer_id: str
    latency_ms: float


class SyncResponse(BaseModel):
    status: str
    peer_id: str
    last_sync: str
    operations_sent: int
    operations_received: int
    conflicts_resolved: int


# ============================================================================
# REQUEST MODELS
# ============================================================================

class ShareFileRequest(BaseModel):
    file_path: str
    shared_by_peer_id: str
    shared_by_name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DownloadFileRequest(BaseModel):
    file_id: str
    peer_ip: str
    peer_port: int
    destination_path: str


class SendMessageRequest(BaseModel):
    dest_peer_id: str
    payload: Dict[str, Any]
    ttl: Optional[int] = None


class SyncRequest(BaseModel):
    peer_id: str
    tables: Optional[List[str]] = None


class SyncExchangeRequest(BaseModel):
    """Sync operation exchange request"""
    sender_peer_id: str
    operations: List[Dict[str, Any]]


class SubmitJobRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_* fields

    job_type: str  # 'embedding', 'inference', 'training'
    data: Any
    model_name: Optional[str] = None
