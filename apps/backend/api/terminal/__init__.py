"""
Terminal API Package

Real-time terminal access via WebSocket and HTTP endpoints.

Modules:
- constants: Rate limiting and connection tracking
- security: Secret redaction for audit logs
- models: Pydantic request/response models
- routes: HTTP endpoints for terminal management
- websocket: WebSocket handler for real-time I/O
- bash_assist: NL→bash translation and safety
"""

from fastapi import APIRouter

# Re-export constants
from api.terminal.constants import (
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
)

# Re-export security
from api.terminal.security import (
    SECRET_PATTERNS,
    redact_secrets,
)

# Re-export models
from api.terminal.models import (
    SpawnTerminalResponseData,
    BashAssistRequest,
    BashAssistResponse,
)

# Re-export WebSocket handler
from api.terminal.websocket import terminal_websocket

# Re-export bash assist
from api.terminal.bash_assist import bash_assist

# Import routes router
from api.terminal.routes import router as routes_router


# Create combined router
router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])

# Include HTTP routes (without prefix since routes_router already has it)
# We need to include the routes directly, not the router
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

# Add routes to combined router
router.add_api_route("/spawn", spawn_terminal, methods=["POST"])
router.add_api_route("/spawn-system", spawn_system_terminal, methods=["POST"])
router.add_api_route("/socket/start", start_terminal_socket, methods=["POST"])
router.add_api_route("/sessions", list_terminal_sessions, methods=["GET"])
router.add_api_route("/{terminal_id}", get_terminal_session, methods=["GET"])
router.add_api_route("/{terminal_id}", close_terminal_session, methods=["DELETE"])
router.add_api_route("/{terminal_id}/context", get_terminal_context, methods=["GET"])
router.add_api_route("/{terminal_id}/resize", resize_terminal, methods=["POST"])

# Add WebSocket endpoint
router.add_api_websocket_route("/ws/{terminal_id}", terminal_websocket)

# Add bash assist endpoint
router.add_api_route("/assist", bash_assist, methods=["POST"], response_model=BashAssistResponse)


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
    "get_ws_connection_lock",
    "get_ws_connections_by_ip",
    "get_total_ws_connections",
    "set_total_ws_connections",
    "increment_ws_connections",
    "decrement_ws_connections",
    "get_session_metadata",
    "_reset_connection_state",
    # Security
    "SECRET_PATTERNS",
    "redact_secrets",
    # Models
    "SpawnTerminalResponseData",
    "BashAssistRequest",
    "BashAssistResponse",
    # WebSocket
    "terminal_websocket",
    # Bash assist
    "bash_assist",
]
