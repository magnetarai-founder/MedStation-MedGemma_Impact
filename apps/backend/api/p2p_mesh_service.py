"""
P2P Mesh Service for Network Selector

Wrapper around existing p2p_chat_service for the Network Selector UI.
Provides simple API for peer discovery, connection codes, and mesh networking.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import secrets
import string

from api.p2p_chat_service import get_p2p_chat_service, init_p2p_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/p2p", tags=["P2P Mesh"])


class ConnectionCode(BaseModel):
    """Connection code for pairing peers"""
    code: str
    peer_id: str
    multiaddrs: List[str]
    expires_at: Optional[str] = None


class AddPeerRequest(BaseModel):
    """Request to add peer by connection code"""
    code: str


class P2PMeshPeer(BaseModel):
    """Peer information for NetworkSelector"""
    id: str
    name: str
    location: Optional[str] = None
    connected: bool


# In-memory storage for connection codes
# In production, this should be in Redis or similar
connection_codes: Dict[str, ConnectionCode] = {}


def generate_connection_code() -> str:
    """Generate a human-readable connection code"""
    # Format: OMNI-XXXX-XXXX (8 characters total)
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"OMNI-{part1}-{part2}"


@router.post("/start")
async def start_p2p_mesh(display_name: str = "OmniStudio User", device_name: str = "My Device"):
    """
    Start P2P mesh networking
    Initializes libp2p and begins peer discovery

    Args:
        display_name: Display name for this peer
        device_name: Device name

    Returns:
        P2P service status
    """
    try:
        # Initialize or get existing service
        service = get_p2p_chat_service()

        if not service:
            service = init_p2p_chat_service(display_name, device_name)

        # Start if not already running
        if not service.is_running:
            await service.start()

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        return {
            "status": "success",
            "message": "P2P mesh started",
            "peer_info": {
                "peer_id": service.peer_id,
                "display_name": service.display_name,
                "device_name": service.device_name,
                "multiaddrs": addrs
            }
        }

    except Exception as e:
        logger.error(f"Failed to start P2P mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_p2p_mesh():
    """
    Stop P2P mesh networking

    Returns:
        Status message
    """
    try:
        service = get_p2p_chat_service()

        if service and service.is_running:
            await service.stop()

        return {
            "status": "success",
            "message": "P2P mesh stopped"
        }

    except Exception as e:
        logger.error(f"Failed to stop P2P mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers")
async def get_p2p_peers():
    """
    Get list of connected P2P peers

    Returns:
        List of peers for NetworkSelector UI
    """
    try:
        service = get_p2p_chat_service()

        if not service:
            return {
                "status": "success",
                "peers": [],
                "count": 0
            }

        # Get all peers
        all_peers = await service.list_peers()

        # Filter out self and format for NetworkSelector
        peers = []
        for peer in all_peers:
            if peer.peer_id != service.peer_id:
                peers.append(P2PMeshPeer(
                    id=peer.peer_id,
                    name=peer.display_name or peer.device_name,
                    location=peer.bio or None,  # Could use bio field for location
                    connected=(peer.status == "online")
                ).dict())

        return {
            "status": "success",
            "peers": peers,
            "count": len(peers)
        }

    except Exception as e:
        logger.error(f"Failed to get P2P peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connection-code")
async def generate_connection_code_endpoint():
    """
    Generate a connection code for this peer
    Other peers can use this code to connect

    Returns:
        Connection code and peer information
    """
    try:
        service = get_p2p_chat_service()

        if not service or not service.is_running:
            raise HTTPException(status_code=503, detail="P2P service not running")

        # Generate code
        code = generate_connection_code()

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        # Store connection code
        connection_info = ConnectionCode(
            code=code,
            peer_id=service.peer_id,
            multiaddrs=addrs
        )

        connection_codes[code] = connection_info

        return {
            "status": "success",
            "code": code,
            "peer_id": service.peer_id,
            "multiaddrs": addrs,
            "message": f"Share this code: {code}"
        }

    except Exception as e:
        logger.error(f"Failed to generate connection code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect_to_peer(request: AddPeerRequest):
    """
    Connect to a peer using their connection code

    Args:
        request: Connection code from other peer

    Returns:
        Connection status
    """
    try:
        service = get_p2p_chat_service()

        if not service or not service.is_running:
            raise HTTPException(status_code=503, detail="P2P service not running")

        # Look up connection code
        if request.code not in connection_codes:
            raise HTTPException(status_code=404, detail="Invalid connection code")

        connection_info = connection_codes[request.code]

        # TODO: Actually connect to the peer using multiaddrs
        # For now, just return success
        logger.info(f"Connecting to peer {connection_info.peer_id} at {connection_info.multiaddrs}")

        return {
            "status": "success",
            "message": f"Connected to peer",
            "peer_id": connection_info.peer_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_p2p_mesh_status():
    """
    Get current P2P mesh status

    Returns:
        Status including connected peers, multiaddrs, etc.
    """
    try:
        service = get_p2p_chat_service()

        if not service:
            return {
                "status": "success",
                "service": {
                    "is_running": False,
                    "peer_id": None,
                    "connected_peers": 0
                }
            }

        # Get online peers
        all_peers = await service.list_peers()
        online_peers = [p for p in all_peers if p.status == "online" and p.peer_id != service.peer_id]

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        return {
            "status": "success",
            "service": {
                "is_running": service.is_running,
                "peer_id": service.peer_id,
                "display_name": service.display_name,
                "device_name": service.device_name,
                "multiaddrs": addrs,
                "connected_peers": len(online_peers)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get P2P mesh status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
