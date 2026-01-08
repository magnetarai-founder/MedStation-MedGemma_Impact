"""
Terminal API Constants

Rate limiting, connection tracking, and security thresholds.
"""

import asyncio
from collections import defaultdict
from typing import Dict, Optional

# ===== WebSocket Rate Limiting =====

MAX_WS_CONNECTIONS_PER_IP = 5
MAX_WS_CONNECTIONS_TOTAL = 100
MAX_SESSION_DURATION_SEC = 30 * 60  # 30 minutes
MAX_INACTIVITY_SEC = 5 * 60  # 5 minutes
MAX_INPUT_SIZE = 16 * 1024  # 16 KB
MAX_OUTPUT_BURST = 20  # Max messages per tick


# ===== Connection Tracking State =====

# Track active connections per IP to prevent DoS
_ws_connections_by_ip: defaultdict[str, int] = defaultdict(int)
_total_ws_connections: int = 0
_ws_connection_lock: Optional[asyncio.Lock] = None
_session_metadata: Dict[str, dict] = {}  # Track session start time and last activity


def get_ws_connection_lock() -> asyncio.Lock:
    """Get or create the WebSocket connection lock"""
    global _ws_connection_lock
    if _ws_connection_lock is None:
        _ws_connection_lock = asyncio.Lock()
    return _ws_connection_lock


def get_ws_connections_by_ip() -> defaultdict[str, int]:
    """Get the connection tracking dict by IP"""
    return _ws_connections_by_ip


def get_total_ws_connections() -> int:
    """Get total WebSocket connection count"""
    return _total_ws_connections


def set_total_ws_connections(count: int) -> None:
    """Set total WebSocket connection count"""
    global _total_ws_connections
    _total_ws_connections = count


def increment_ws_connections(client_ip: str) -> None:
    """Increment connection counts for an IP"""
    global _total_ws_connections
    _ws_connections_by_ip[client_ip] += 1
    _total_ws_connections += 1


def decrement_ws_connections(client_ip: str) -> None:
    """Decrement connection counts for an IP"""
    global _total_ws_connections
    _ws_connections_by_ip[client_ip] -= 1
    _total_ws_connections -= 1
    # Clean up empty IP entries
    if _ws_connections_by_ip[client_ip] == 0:
        del _ws_connections_by_ip[client_ip]


def get_session_metadata() -> Dict[str, dict]:
    """Get session metadata dict"""
    return _session_metadata


# For testing only
def _reset_connection_state() -> None:
    """Reset all connection tracking state - for testing only"""
    global _ws_connections_by_ip, _total_ws_connections, _ws_connection_lock, _session_metadata
    _ws_connections_by_ip = defaultdict(int)
    _total_ws_connections = 0
    _ws_connection_lock = None
    _session_metadata = {}
