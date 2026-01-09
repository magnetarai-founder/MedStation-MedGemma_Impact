"""
Offline Mesh - Relay Routes

Message relay and routing endpoints for mesh network.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging

from api.mesh_relay import get_mesh_relay
from api.offline_mesh.models import (
    SendMessageRequest,
    RelayPeerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/relay/peer/add", response_model=RelayPeerResponse)
async def add_relay_peer(request: Request, peer_id: str, latency_ms: float = 10.0) -> RelayPeerResponse:
    """Add a direct peer to relay network"""
    try:
        relay = get_mesh_relay()
        relay.add_direct_peer(peer_id, latency_ms)

        return {
            "status": "added",
            "peer_id": peer_id,
            "latency_ms": latency_ms
        }

    except Exception as e:
        logger.error(f"Failed to add peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relay/peer/{peer_id}")
async def remove_relay_peer(request: Request, peer_id: str) -> Dict[str, str]:
    """Remove peer from relay network"""
    try:
        relay = get_mesh_relay()
        relay.remove_direct_peer(peer_id)

        return {"status": "removed", "peer_id": peer_id}

    except Exception as e:
        logger.error(f"Failed to remove peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relay/send")
async def send_relay_message(request: Request, body: SendMessageRequest) -> Dict[str, Any]:
    """Send message through relay network"""
    try:
        relay = get_mesh_relay()

        success = await relay.send_message(
            dest_peer_id=body.dest_peer_id,
            payload=body.payload,
            ttl=body.ttl
        )

        if success:
            return {"status": "sent", "dest_peer_id": body.dest_peer_id}
        else:
            return {"status": "queued", "dest_peer_id": body.dest_peer_id, "reason": "no_route"}

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/route/{peer_id}")
async def get_route_to_peer(peer_id: str) -> Dict[str, Any]:
    """Get route to destination peer"""
    try:
        relay = get_mesh_relay()
        route = relay.get_route_to(peer_id)

        if route:
            return {
                "dest_peer_id": peer_id,
                "route": route,
                "hop_count": len(route) - 1
            }
        else:
            raise HTTPException(status_code=404, detail="No route found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/stats")
async def get_relay_stats() -> Dict[str, Any]:
    """Get relay statistics"""
    try:
        relay = get_mesh_relay()
        return relay.get_stats()

    except Exception as e:
        logger.error(f"Failed to get relay stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/routing-table")
async def get_routing_table() -> Dict[str, Any]:
    """Get current routing table"""
    try:
        relay = get_mesh_relay()
        return relay.get_routing_table()

    except Exception as e:
        logger.error(f"Failed to get routing table: {e}")
        raise HTTPException(status_code=500, detail=str(e))
