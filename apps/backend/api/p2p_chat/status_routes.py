"""
P2P Chat - Status and Peer Routes

Service initialization, status check, and peer discovery endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import logging

from api.errors import http_404, http_500, http_503
from api.p2p_chat.models import (
    Peer,
    PeerListResponse,
    P2PStatusResponse,
)
from api.services.p2p_chat import get_p2p_chat_service, init_p2p_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/initialize")
async def initialize_p2p_service(request: Request, display_name: str, device_name: str) -> Dict[str, Any]:
    """
    Initialize the P2P chat service
    Called once when the app starts
    """
    try:
        service = init_p2p_chat_service(display_name, device_name)
        await service.start()

        return {
            "status": "started",
            "peer_id": service.peer_id,
            "display_name": display_name,
            "device_name": device_name
        }

    except Exception as e:
        logger.error(f"Failed to initialize P2P service: {e}")
        raise http_500(str(e))


@router.get("/status", response_model=P2PStatusResponse)
async def get_p2p_status() -> P2PStatusResponse:
    """Get current P2P network status"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running")

    peers = await service.list_peers()
    online_peers = [p for p in peers if p.status == "online" and p.peer_id != service.peer_id]

    channels = await service.list_channels()

    # Get multiaddrs if host is available
    addrs = []
    if service.host:
        addrs = [str(addr) for addr in service.host.get_addrs()]

    return P2PStatusResponse(
        peer_id=service.peer_id,
        is_connected=service.is_running,
        discovered_peers=len(online_peers),
        active_channels=len(channels),
        multiaddrs=addrs
    )


@router.get("/peers", response_model=PeerListResponse)
async def list_peers() -> PeerListResponse:
    """List all discovered peers"""
    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized")

    peers = await service.list_peers()

    return PeerListResponse(
        peers=peers,
        total=len(peers)
    )


@router.get("/peers/{peer_id}", response_model=Peer)
async def get_peer(peer_id: str) -> Peer:
    """Get details about a specific peer"""
    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized")

    peers = await service.list_peers()
    peer = next((p for p in peers if p.peer_id == peer_id), None)

    if not peer:
        raise http_404("Peer not found", resource="peer")

    return peer
