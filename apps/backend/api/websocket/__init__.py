"""
WebSocket Package

Real-time communication for MedStation:
- ConnectionManager: WebSocket connection tracking and broadcasting
- Collaborative editing via Yjs CRDT
- Workspace session management across tabs
"""

from api.websocket.manager import (
    ConnectionManager,
    manager,
)

from api.websocket.collab import router as collab_router

from api.websocket.session import (
    WorkspaceSessionManager,
    get_workspace_session_manager,
)

__all__ = [
    # Connection Manager
    "ConnectionManager",
    "manager",
    # Collaboration Router
    "collab_router",
    # Workspace Session
    "WorkspaceSessionManager",
    "get_workspace_session_manager",
]
