"""
Offline Mesh Package

FastAPI Router for Offline Mesh Networking.
Exposes all offline collaboration features via REST API.

Components:
- models.py: Pydantic request/response models
- discovery_routes.py: mDNS peer discovery endpoints
- files_routes.py: P2P file sharing endpoints
- relay_routes.py: Message relay/routing endpoints
- sync_routes.py: CRDT-based data sync endpoints
- compute_routes.py: MLX distributed computing endpoints
"""

from fastapi import APIRouter, Depends

from api.auth_middleware import get_current_user

# Import models for re-export
from api.offline_mesh.models import (
    DiscoveryStartResponse,
    PeerInfo,
    PeersListResponse,
    StatusResponse,
    FileShareResponse,
    RelayPeerResponse,
    SyncResponse,
    ShareFileRequest,
    DownloadFileRequest,
    SendMessageRequest,
    SyncRequest,
    SyncExchangeRequest,
    SubmitJobRequest,
)

# Import sub-routers
from api.offline_mesh.discovery_routes import (
    router as discovery_router,
    start_discovery,
    get_discovered_peers,
    get_discovery_stats,
    stop_discovery,
)
from api.offline_mesh.files_routes import (
    router as files_router,
    share_file,
    list_shared_files,
    download_file,
    get_active_transfers,
    delete_shared_file,
    get_file_sharing_stats,
)
from api.offline_mesh.relay_routes import (
    router as relay_router,
    add_relay_peer,
    remove_relay_peer,
    send_relay_message,
    get_route_to_peer,
    get_relay_stats,
    get_routing_table,
)
from api.offline_mesh.sync_routes import (
    router as sync_router,
    start_sync,
    get_sync_state,
    get_all_sync_states,
    get_sync_stats,
    exchange_sync_operations,
)
from api.offline_mesh.compute_routes import (
    router as compute_router,
    start_compute_server,
    get_compute_nodes,
    submit_compute_job,
    get_job_status,
    get_compute_stats,
)

# Create main router that includes all sub-routers
router = APIRouter(
    prefix="/api/v1/mesh",
    tags=["Offline Mesh"],
    dependencies=[Depends(get_current_user)]  # Require auth
)
router.include_router(discovery_router)
router.include_router(files_router)
router.include_router(relay_router)
router.include_router(sync_router)
router.include_router(compute_router)


__all__ = [
    # Main router
    "router",
    # Response models
    "DiscoveryStartResponse",
    "PeerInfo",
    "PeersListResponse",
    "StatusResponse",
    "FileShareResponse",
    "RelayPeerResponse",
    "SyncResponse",
    # Request models
    "ShareFileRequest",
    "DownloadFileRequest",
    "SendMessageRequest",
    "SyncRequest",
    "SyncExchangeRequest",
    "SubmitJobRequest",
    # Discovery endpoints
    "start_discovery",
    "get_discovered_peers",
    "get_discovery_stats",
    "stop_discovery",
    # File sharing endpoints
    "share_file",
    "list_shared_files",
    "download_file",
    "get_active_transfers",
    "delete_shared_file",
    "get_file_sharing_stats",
    # Relay endpoints
    "add_relay_peer",
    "remove_relay_peer",
    "send_relay_message",
    "get_route_to_peer",
    "get_relay_stats",
    "get_routing_table",
    # Sync endpoints
    "start_sync",
    "get_sync_state",
    "get_all_sync_states",
    "get_sync_stats",
    "exchange_sync_operations",
    # Compute endpoints
    "start_compute_server",
    "get_compute_nodes",
    "submit_compute_job",
    "get_job_status",
    "get_compute_stats",
]
