"""
Compatibility Shim for Collaborative Editing WebSocket

The implementation now lives in the `api.websocket` package:
- api.websocket.collab: router and collaboration functions

This shim maintains backward compatibility.
"""

from api.websocket.collab import router

__all__ = [
    "router",
]
