"""
Offline Mesh - Discovery Routes

mDNS peer discovery endpoints for local network.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any
import logging

from api.auth_middleware import get_current_user
from api.offline_mesh_discovery import get_mesh_discovery
from api.offline_mesh.models import (
    DiscoveryStartResponse,
    PeersListResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/discovery/start", response_model=DiscoveryStartResponse)
async def start_discovery(request: Request, display_name: str, device_name: str) -> DiscoveryStartResponse:
    """
    Start mDNS peer discovery on local network

    Initiates zero-config service discovery using Bonjour/mDNS to automatically
    find other ElohimOS instances on the same LAN without manual IP configuration.

    Flow:
    1. Broadcasts service announcement on local network via mDNS
    2. Listens for peer announcements from other instances
    3. Maintains active peer list with automatic timeout/cleanup
    4. Enables subsequent P2P operations (file sharing, sync, distributed compute)

    Args:
        display_name: Human-readable name shown to other peers (e.g., "John's MacBook")
        device_name: Device identifier for technical logs (e.g., "macbook-pro-2023")

    Returns:
        peer_id: Unique UUID for this peer session
        status: "started" on success

    Notes:
        - Requires network permissions for multicast DNS
        - Peer list auto-refreshes; call GET /discovery/peers to retrieve
        - Stop with POST /discovery/stop when disconnecting
    """
    try:
        discovery = get_mesh_discovery(display_name, device_name)
        success = await discovery.start()

        if success:
            return {
                "status": "started",
                "peer_id": discovery.peer_id,
                "display_name": display_name,
                "device_name": device_name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start discovery")

    except Exception as e:
        logger.error(f"Failed to start discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/peers", response_model=PeersListResponse)
async def get_discovered_peers() -> PeersListResponse:
    """Get list of discovered peers on local network"""
    try:
        discovery = get_mesh_discovery()
        peers = discovery.get_peers()

        return {
            "count": len(peers),
            "peers": [
                {
                    "peer_id": p.peer_id,
                    "display_name": p.display_name,
                    "device_name": p.device_name,
                    "ip_address": p.ip_address,
                    "port": p.port,
                    "capabilities": p.capabilities,
                    "status": p.status,
                    "last_seen": p.last_seen
                }
                for p in peers
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/stats")
async def get_discovery_stats() -> Dict[str, Any]:
    """Get discovery statistics"""
    try:
        discovery = get_mesh_discovery()
        return discovery.get_stats()

    except Exception as e:
        logger.error(f"Failed to get discovery stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery/stop", response_model=StatusResponse)
async def stop_discovery(request: Request) -> StatusResponse:
    """Stop peer discovery"""
    try:
        discovery = get_mesh_discovery()
        await discovery.stop()

        return {"status": "stopped"}

    except Exception as e:
        logger.error(f"Failed to stop discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))
