"""
Vault WebSocket Routes - Real-time collaboration and notifications
"""

import logging
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    vault_type: str = "real",
    token: str = None  # Auth token from query param
):
    """
    WebSocket endpoint for real-time vault updates

    Supports:
    - Real-time file upload/delete/update notifications
    - User presence tracking
    - Activity broadcasting

    Security: Requires valid JWT token for authentication
    """
    # Verify authentication before accepting connection
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        # Verify JWT token
        import jwt
        from auth_middleware import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        authenticated_user_id = payload.get("user_id")

        # Verify user_id matches token
        if authenticated_user_id != user_id:
            await websocket.close(code=1008, reason="User ID mismatch")
            return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    if manager:
        await manager.connect(websocket, user_id, vault_type)
    else:
        await websocket.accept()

    try:
        while True:
            # Receive messages for keepalive and client-initiated events
            data = await websocket.receive_text()

            # Parse incoming message
            try:
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to keepalive ping
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

                elif message.get("type") == "activity_update":
                    # Update user's last activity timestamp
                    if manager and user_id in manager.user_presence:
                        manager.user_presence[user_id]["last_activity"] = datetime.utcnow().isoformat()

                else:
                    # Echo unknown messages for debugging
                    await websocket.send_json({"type": "echo", "received": message})

            except json.JSONDecodeError:
                # If not JSON, treat as simple keepalive string
                await websocket.send_text(f"Message received: {data}")

    except WebSocketDisconnect:
        if manager:
            manager.disconnect(websocket, user_id, vault_type)
        logger.info(f"WebSocket disconnected: user={user_id}, vault={vault_type}")


@router.get("/ws/online-users")
async def get_online_users(vault_type: Optional[str] = None):
    """Get list of currently online users"""
    if not manager:
        return {
            "online_users": [],
            "total_connections": 0,
            "vault_type": vault_type,
            "manager_available": False
        }

    return {
        "online_users": manager.get_online_users(vault_type),
        "total_connections": manager.get_connection_count(),
        "vault_type": vault_type,
        "manager_available": True
    }
