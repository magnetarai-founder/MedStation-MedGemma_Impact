"""
P2P Chat - WebSocket Routes

Real-time WebSocket connection and broadcast functionality.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

from api.auth_middleware import extract_websocket_token, auth_service
from api.p2p_chat.state import active_connections

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> None:
    """
    WebSocket connection for real-time chat updates
    Sends events for new messages, peer status changes, etc.

    Authentication:
        - Preferred: Sec-WebSocket-Protocol header with "jwt-<token>" or "bearer.<token>"
        - Fallback: Query param ?token=xxx (deprecated)

    Security: Requires valid JWT token for authentication
    """
    # SECURITY: Extract token from header (preferred) or query param (deprecated fallback)
    auth_token = extract_websocket_token(websocket, token)

    if not auth_token:
        await websocket.close(code=1008, reason="Missing authentication token")
        logger.warning("P2P WebSocket rejected: no token")
        return

    user_payload = auth_service.verify_token(auth_token)
    if not user_payload:
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning("P2P WebSocket rejected: invalid token")
        return

    user_id = user_payload.get("user_id")

    await websocket.accept()
    active_connections.append(websocket)

    logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(active_connections)}")

    try:
        # Keep connection alive and listen for pings
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(active_connections)}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_event(event: Dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients"""
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)
