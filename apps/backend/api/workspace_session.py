"""
Compatibility Shim for Workspace Session Manager

The implementation now lives in the `api.websocket` package:
- api.websocket.session: WorkspaceSessionManager class

This shim maintains backward compatibility.
"""

from api.websocket.session import (
    WorkspaceSessionManager,
    get_workspace_session_manager,
)

__all__ = [
    "WorkspaceSessionManager",
    "get_workspace_session_manager",
]
