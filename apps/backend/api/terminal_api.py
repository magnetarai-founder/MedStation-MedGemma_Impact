"""
Terminal API - Backwards Compatibility Shim

This file provides backwards compatibility after the terminal_api module
was decomposed into a package during P2 monolithic file fixes.

The actual implementation is now in api/terminal/:
- constants.py: Rate limits, connection tracking state
- security.py: SECRET_PATTERNS, redact_secrets
- models.py: SpawnTerminalResponseData, BashAssistRequest, BashAssistResponse
- routes.py: HTTP endpoints (spawn, sessions, close, resize, etc.)
- websocket.py: terminal_websocket handler
- bash_assist.py: bash_assist endpoint

Import from api.terminal for new code.
"""

# Re-export everything from the package for backwards compatibility
from api.terminal import (
    # Router
    router,
    # Constants
    MAX_WS_CONNECTIONS_PER_IP,
    MAX_WS_CONNECTIONS_TOTAL,
    MAX_SESSION_DURATION_SEC,
    MAX_INACTIVITY_SEC,
    MAX_INPUT_SIZE,
    MAX_OUTPUT_BURST,
    get_ws_connection_lock,
    get_ws_connections_by_ip,
    get_total_ws_connections,
    set_total_ws_connections,
    increment_ws_connections,
    decrement_ws_connections,
    get_session_metadata,
    _reset_connection_state,
    # Security
    SECRET_PATTERNS,
    redact_secrets,
    # Models
    SpawnTerminalResponseData,
    BashAssistRequest,
    BashAssistResponse,
    # WebSocket
    terminal_websocket,
    # Bash assist function
    bash_assist,
)

# Re-export route functions for backwards compatibility
from api.terminal.routes import (
    spawn_terminal,
    spawn_system_terminal,
    start_terminal_socket,
    list_terminal_sessions,
    get_terminal_session,
    close_terminal_session,
    get_terminal_context,
    resize_terminal,
)

# Re-export legacy module-level globals for test compatibility
# These are now managed by constants.py but some tests may import them directly
_ws_connections_by_ip = get_ws_connections_by_ip()
_total_ws_connections = get_total_ws_connections()
_ws_connection_lock = None  # Lazy init via get_ws_connection_lock()
_session_metadata = get_session_metadata()

__all__ = [
    # Router
    "router",
    # Constants
    "MAX_WS_CONNECTIONS_PER_IP",
    "MAX_WS_CONNECTIONS_TOTAL",
    "MAX_SESSION_DURATION_SEC",
    "MAX_INACTIVITY_SEC",
    "MAX_INPUT_SIZE",
    "MAX_OUTPUT_BURST",
    # Legacy globals (now functions)
    "_ws_connections_by_ip",
    "_total_ws_connections",
    "_ws_connection_lock",
    "_session_metadata",
    # Security
    "SECRET_PATTERNS",
    "redact_secrets",
    # Models
    "SpawnTerminalResponseData",
    "BashAssistRequest",
    "BashAssistResponse",
    # Route functions
    "spawn_terminal",
    "spawn_system_terminal",
    "start_terminal_socket",
    "list_terminal_sessions",
    "get_terminal_session",
    "close_terminal_session",
    "get_terminal_context",
    "resize_terminal",
    # WebSocket
    "terminal_websocket",
    # Bash assist
    "bash_assist",
]
