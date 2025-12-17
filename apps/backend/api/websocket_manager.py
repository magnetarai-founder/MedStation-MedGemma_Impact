#!/usr/bin/env python3
"""
WebSocket Connection Manager for Real-Time Collaboration
Handles WebSocket connections for vault real-time updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
import json
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates

    Supports:
    - User-based connection tracking
    - Broadcasting to specific users or all users
    - Vault-specific channels (real/decoy)
    """

    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Track user presence
        self.user_presence: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str, vault_type: str = "real"):
        """Accept and register a WebSocket connection"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

        # Update presence
        self.user_presence[user_id] = {
            "status": "online",
            "vault_type": vault_type,
            "connected_at": datetime.now(UTC).isoformat(),
            "last_activity": datetime.now(UTC).isoformat()
        }

        logger.info(f"WebSocket connected: user={user_id}, vault={vault_type}")

        # Broadcast user came online
        await self.broadcast_to_all({
            "type": "user_presence",
            "user_id": user_id,
            "status": "online",
            "timestamp": datetime.now(UTC).isoformat()
        }, vault_type)

    def disconnect(self, websocket: WebSocket, user_id: str, vault_type: str = "real"):
        """Remove and cleanup a WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Remove user if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_presence:
                    del self.user_presence[user_id]

        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user's connections"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to {user_id}: {e}")
                    disconnected.add(connection)

            # Clean up dead connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

    async def broadcast_to_all(self, message: dict, vault_type: Optional[str] = None):
        """Broadcast message to all connected users"""
        disconnected_users = []

        for user_id, connections in self.active_connections.items():
            # Filter by vault type if specified
            if vault_type and user_id in self.user_presence:
                if self.user_presence[user_id].get("vault_type") != vault_type:
                    continue

            disconnected = set()
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {user_id}: {e}")
                    disconnected.add(connection)

            # Clean up dead connections
            for conn in disconnected:
                connections.discard(conn)

            if not connections:
                disconnected_users.append(user_id)

        # Remove empty user entries
        for user_id in disconnected_users:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            if user_id in self.user_presence:
                del self.user_presence[user_id]

    async def broadcast_file_event(self, event_type: str, file_data: dict, vault_type: str, user_id: str):
        """Broadcast file-related events"""
        message = {
            "type": "file_event",
            "event": event_type,
            "file": file_data,
            "vault_type": vault_type,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat()
        }
        await self.broadcast_to_all(message, vault_type)

    async def broadcast_activity(self, action: str, resource_type: str, details: str, vault_type: str, user_id: str):
        """Broadcast activity events"""
        message = {
            "type": "activity",
            "action": action,
            "resource_type": resource_type,
            "details": details,
            "vault_type": vault_type,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat()
        }
        await self.broadcast_to_all(message, vault_type)

    def get_online_users(self, vault_type: Optional[str] = None) -> list:
        """Get list of currently online users"""
        if vault_type:
            return [
                user_id for user_id, presence in self.user_presence.items()
                if presence.get("vault_type") == vault_type
            ]
        return list(self.user_presence.keys())

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
