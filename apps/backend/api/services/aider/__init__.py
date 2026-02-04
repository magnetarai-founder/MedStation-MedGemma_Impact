"""
Aider Integration Module

Provides deep integration with Aider for code editing tasks.
Supports both subprocess execution and session-based interaction.

Usage:
    from api.services.aider import (
        AiderConfig,
        AiderBridge,
        create_aider_bridge,
        AiderSessionManager,
    )

    # Simple subprocess-based usage
    config = AiderConfig(workspace_root="/path/to/project")
    bridge = create_aider_bridge(config)

    response = await bridge.execute_edit(
        "Add error handling to the login function",
        files=["src/auth.py"]
    )

    # Session-based usage for multi-turn conversations
    session_mgr = AiderSessionManager()
    bridge = create_aider_bridge(config, use_sessions=True, session_manager=session_mgr)
"""

from .bridge import (
    AiderBridge,
    AiderEdit,
    AiderMessage,
    AiderResponse,
    AiderSession,
    EditType,
)
from .config import AiderConfig, EditFormat, get_aider_config
from .context_sync import ContextSynchronizer, FileState, SyncState
from .executor import (
    SessionAiderBridge,
    SubprocessAiderBridge,
    create_aider_bridge,
)
from .session import (
    AiderSessionManager,
    ManagedAiderSession,
    SessionConfig,
    SessionState,
)

__all__ = [
    # Config
    "AiderConfig",
    "EditFormat",
    "get_aider_config",
    # Bridge interface
    "AiderBridge",
    "AiderSession",
    "AiderEdit",
    "AiderMessage",
    "AiderResponse",
    "EditType",
    # Implementations
    "SubprocessAiderBridge",
    "SessionAiderBridge",
    "create_aider_bridge",
    # Session management
    "AiderSessionManager",
    "ManagedAiderSession",
    "SessionConfig",
    "SessionState",
    # Context sync
    "ContextSynchronizer",
    "FileState",
    "SyncState",
]
