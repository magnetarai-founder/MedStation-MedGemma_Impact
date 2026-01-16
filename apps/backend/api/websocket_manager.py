"""
Compatibility Shim for WebSocket Manager

The implementation now lives in the `api.websocket` package:
- api.websocket.manager: ConnectionManager class

This shim maintains backward compatibility.
"""

from api.websocket.manager import (
    ConnectionManager,
    manager,
)

__all__ = [
    "ConnectionManager",
    "manager",
]
