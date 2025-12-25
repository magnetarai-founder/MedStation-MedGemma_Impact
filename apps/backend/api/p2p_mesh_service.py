"""
P2P Mesh Service for Network Selector

Wrapper around existing p2p_chat_service for the Network Selector UI.
Provides simple API for peer discovery, connection codes, and mesh networking.
"""

from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging
import secrets
import string
import json

from api.p2p_chat_service import get_p2p_chat_service, init_p2p_chat_service
from api.rate_limiter import connection_code_limiter, get_client_ip

logger = logging.getLogger(__name__)

from fastapi import Depends
from api.auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/p2p",
    tags=["P2P Mesh"],
    dependencies=[Depends(get_current_user)]  # Require auth for all P2P mesh endpoints
)


class ConnectionCode(BaseModel):
    """Connection code for pairing peers"""
    code: str
    peer_id: str
    multiaddrs: List[str]
    expires_at: Optional[str] = None


class AddPeerRequest(BaseModel):
    """Request to add peer by connection code"""
    code: str


class P2PMeshPeer(BaseModel):
    """Peer information for NetworkSelector"""
    id: str
    name: str
    location: Optional[str] = None
    connected: bool


# Persistent storage for connection codes
# Store in database to survive restarts (critical for offline deployments)
from api.config_paths import get_config_paths
import sqlite3
from datetime import datetime, timedelta

PATHS = get_config_paths()
CODES_DB_PATH = PATHS.data_dir / "p2p_connection_codes.db"


def _init_codes_db() -> None:
    """Initialize database for connection codes"""
    CODES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS connection_codes (
                code TEXT PRIMARY KEY,
                peer_id TEXT NOT NULL,
                multiaddrs TEXT NOT NULL,
                expires_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def _save_connection_code(code: str, connection: ConnectionCode) -> None:
    """Save connection code to persistent storage"""
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO connection_codes (code, peer_id, multiaddrs, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            code,
            connection.peer_id,
            json.dumps(connection.multiaddrs),
            connection.expires_at,
            datetime.now().isoformat()
        ))
        conn.commit()


def _load_connection_codes() -> Dict[str, ConnectionCode]:
    """Load all valid connection codes from database"""
    codes = {}
    try:
        with sqlite3.connect(str(CODES_DB_PATH)) as conn:
            cursor = conn.execute("""
                SELECT code, peer_id, multiaddrs, expires_at
                FROM connection_codes
                WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')
            """)
            for row in cursor.fetchall():
                code, peer_id, multiaddrs_json, expires_at = row
                codes[code] = ConnectionCode(
                    code=code,
                    peer_id=peer_id,
                    multiaddrs=json.loads(multiaddrs_json),
                    expires_at=expires_at
                )
    except Exception as e:
        logger.error(f"Failed to load connection codes: {e}")
    return codes


# Initialize persistent storage
_init_codes_db()

# Load existing connection codes from database
connection_codes: Dict[str, ConnectionCode] = _load_connection_codes()

logger.info(f"Loaded {len(connection_codes)} connection codes from database")


def generate_connection_code() -> str:
    """Generate a human-readable connection code"""
    # Format: OMNI-XXXX-XXXX (8 characters total)
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"OMNI-{part1}-{part2}"


@router.post("/start")
async def start_p2p_mesh(request: Request, display_name: str = "ElohimOS User", device_name: str = "My Device") -> Dict[str, Any]:
    """
    Start P2P mesh networking
    Initializes libp2p and begins peer discovery

    Args:
        display_name: Display name for this peer
        device_name: Device name

    Returns:
        P2P service status
    """
    try:
        # Initialize or get existing service
        service = get_p2p_chat_service()

        if not service:
            service = init_p2p_chat_service(display_name, device_name)

        # Start if not already running
        if not service.is_running:
            await service.start()

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        return {
            "status": "success",
            "message": "P2P mesh started",
            "peer_info": {
                "peer_id": service.peer_id,
                "display_name": service.display_name,
                "device_name": service.device_name,
                "multiaddrs": addrs
            }
        }

    except Exception as e:
        logger.error(f"Failed to start P2P mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_p2p_mesh(request: Request) -> Dict[str, str]:
    """
    Stop P2P mesh networking

    Returns:
        Status message
    """
    try:
        service = get_p2p_chat_service()

        if service and service.is_running:
            await service.stop()

        return {
            "status": "success",
            "message": "P2P mesh stopped"
        }

    except Exception as e:
        logger.error(f"Failed to stop P2P mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers")
async def get_p2p_peers() -> Dict[str, Any]:
    """
    Get list of connected P2P peers

    Returns:
        List of peers for NetworkSelector UI
    """
    try:
        service = get_p2p_chat_service()

        if not service:
            return {
                "status": "success",
                "peers": [],
                "count": 0
            }

        # Get all peers
        all_peers = await service.list_peers()

        # Filter out self and format for NetworkSelector
        peers = []
        for peer in all_peers:
            if peer.peer_id != service.peer_id:
                peers.append(P2PMeshPeer(
                    id=peer.peer_id,
                    name=peer.display_name or peer.device_name,
                    location=peer.bio or None,  # Could use bio field for location
                    connected=(peer.status == "online")
                ).dict())

        return {
            "status": "success",
            "peers": peers,
            "count": len(peers)
        }

    except Exception as e:
        logger.error(f"Failed to get P2P peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connection-code")
async def generate_connection_code_endpoint(request: Request) -> Dict[str, Any]:
    """
    Generate a connection code for this peer
    Other peers can use this code to connect

    Returns:
        Connection code and peer information
    """
    try:
        service = get_p2p_chat_service()

        if not service or not service.is_running:
            raise HTTPException(status_code=503, detail="P2P service not running")

        # Generate code
        code = generate_connection_code()

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        # Store connection code (in-memory and persistent storage)
        connection_info = ConnectionCode(
            code=code,
            peer_id=service.peer_id,
            multiaddrs=addrs
        )

        connection_codes[code] = connection_info
        _save_connection_code(code, connection_info)  # Persist to database

        return {
            "status": "success",
            "code": code,
            "peer_id": service.peer_id,
            "multiaddrs": addrs,
            "message": f"Share this code: {code}"
        }

    except Exception as e:
        logger.error(f"Failed to generate connection code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect_to_peer(request: Request, body: AddPeerRequest) -> Dict[str, Any]:
    """
    Connect to a peer using their connection code

    SECURITY (Dec 2025):
    - Rate limited: 5 attempts per minute per IP
    - Exponential backoff on consecutive failures
    - Lockout after 15 failed attempts

    Args:
        request: Connection code from other peer

    Returns:
        Connection status
    """
    # Rate limit check (prevents brute force attacks)
    client_ip = get_client_ip(request)
    allowed, error_message = connection_code_limiter.check_attempt(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_message)

    try:
        service = get_p2p_chat_service()

        if not service or not service.is_running:
            raise HTTPException(status_code=503, detail="P2P service not running")

        # Look up connection code
        if body.code not in connection_codes:
            # Record failure for rate limiting
            connection_code_limiter.record_failure(client_ip)
            raise HTTPException(status_code=404, detail="Invalid connection code")

        connection_info = connection_codes[body.code]

        # Attempt real P2P connection using libp2p multiaddrs
        try:
            # Get the p2p service
            if not service.host:
                raise HTTPException(status_code=503, detail="P2P host not initialized")

            # Parse multiaddrs and connect to peer
            from multiaddr import Multiaddr

            peer_multiaddrs = [Multiaddr(addr) for addr in connection_info.multiaddrs]

            if not peer_multiaddrs:
                raise HTTPException(status_code=400, detail="No valid multiaddrs found in connection code")

            # Connect to peer using first valid multiaddr
            # In production, should try all multiaddrs until one succeeds
            peer_info = service.host.get_network().connect(peer_multiaddrs[0])

            logger.info(f"✅ Successfully connected to peer {connection_info.peer_id}")

            # Record success (resets consecutive failure count)
            connection_code_limiter.record_success(client_ip)

            return {
                "status": "success",
                "message": f"Connected to peer {connection_info.peer_id}",
                "peer_id": connection_info.peer_id,
                "multiaddrs": connection_info.multiaddrs
            }

        except ImportError as e:
            logger.error(f"libp2p/multiaddr not available: {e}")
            raise HTTPException(
                status_code=503,
                detail="P2P networking libraries not installed. Install with: pip install libp2p"
            )
        except Exception as e:
            logger.error(f"Failed to connect to peer {connection_info.peer_id}: {e}")
            # Connection attempt failed (valid code but connection error)
            # Don't count as failure for rate limiting (code was valid)
            raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_p2p_mesh_status() -> Dict[str, Any]:
    """
    Get current P2P mesh status

    Returns:
        Status including connected peers, multiaddrs, etc.
    """
    try:
        service = get_p2p_chat_service()

        if not service:
            return {
                "status": "success",
                "service": {
                    "is_running": False,
                    "peer_id": None,
                    "connected_peers": 0
                }
            }

        # Get online peers
        all_peers = await service.list_peers()
        online_peers = [p for p in all_peers if p.status == "online" and p.peer_id != service.peer_id]

        # Get multiaddrs
        addrs = []
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]

        return {
            "status": "success",
            "service": {
                "is_running": service.is_running,
                "peer_id": service.peer_id,
                "display_name": service.display_name,
                "device_name": service.device_name,
                "multiaddrs": addrs,
                "connected_peers": len(online_peers)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get P2P mesh status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Diagnostics Endpoints =====

class DiagnosticCheck(BaseModel):
    """Single diagnostic check result"""
    name: str
    ok: bool
    message: str
    remediation: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    """P2P diagnostics response"""
    mdns_ok: bool
    port_8000_open: bool
    peer_count: int
    hints: List[str]


class RunChecksResponse(BaseModel):
    """Detailed diagnostic checks response"""
    checks: List[DiagnosticCheck]


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(request: Request):
    """
    Get P2P diagnostics overview

    Returns high-level status of:
    - mDNS availability
    - Port 8000 accessibility
    - Peer count
    - Troubleshooting hints
    """
    import socket
    import platform

    service = get_p2p_chat_service()

    # Check mDNS (platform-specific)
    mdns_ok = False
    try:
        if platform.system() == "Darwin":
            # macOS has native mDNS (Bonjour)
            mdns_ok = True
        else:
            # Check if Avahi or similar is running
            import subprocess
            result = subprocess.run(["which", "avahi-daemon"], capture_output=True)
            mdns_ok = result.returncode == 0
    except Exception as e:
        logger.warning(f"mDNS check failed: {e}")
        mdns_ok = False

    # Check port 8000 (simple socket check)
    port_8000_open = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        # Try to bind to port 8000
        result = sock.connect_ex(('127.0.0.1', 8000))
        port_8000_open = (result == 0)
        sock.close()
    except Exception as e:
        logger.warning(f"Port 8000 check failed: {e}")
        port_8000_open = False

    # Get peer count
    peer_count = 0
    if service and service.is_running:
        try:
            all_peers = await service.list_peers()
            online_peers = [p for p in all_peers if p.status == "online" and p.peer_id != service.peer_id]
            peer_count = len(online_peers)
        except Exception as e:
            logger.warning(f"Peer count failed: {e}")

    # Generate hints
    hints = []
    if not mdns_ok:
        hints.append("mDNS may not be available - peer discovery might be limited")
    if not port_8000_open:
        hints.append("Port 8000 appears closed - ensure backend is running")
    if peer_count == 0 and service and service.is_running:
        hints.append("No peers found - check network connection and firewall")
    if not service or not service.is_running:
        hints.append("P2P service not running - click 'Start P2P' to begin discovery")

    if not hints:
        hints.append("All systems nominal ✅")

    return DiagnosticsResponse(
        mdns_ok=mdns_ok,
        port_8000_open=port_8000_open,
        peer_count=peer_count,
        hints=hints
    )


@router.post("/diagnostics/run-checks", response_model=RunChecksResponse)
async def run_diagnostic_checks(request: Request):
    """
    Run detailed P2P diagnostic checks

    Returns individual checks with pass/fail and remediation steps
    """
    import socket
    import platform
    import subprocess

    checks = []
    service = get_p2p_chat_service()

    # Check 1: P2P Service Running
    if service and service.is_running:
        checks.append(DiagnosticCheck(
            name="P2P Service",
            ok=True,
            message="P2P service is running",
            remediation=None
        ))
    else:
        checks.append(DiagnosticCheck(
            name="P2P Service",
            ok=False,
            message="P2P service is not running",
            remediation="Click 'Start P2P' in the Network Selector to initialize peer discovery"
        ))

    # Check 2: mDNS/Bonjour
    mdns_ok = False
    mdns_message = ""
    try:
        if platform.system() == "Darwin":
            mdns_ok = True
            mdns_message = "Bonjour is available (macOS native)"
        else:
            result = subprocess.run(["which", "avahi-daemon"], capture_output=True)
            if result.returncode == 0:
                mdns_ok = True
                mdns_message = "Avahi daemon found"
            else:
                mdns_message = "Avahi daemon not found"
    except Exception as e:
        mdns_message = f"mDNS check failed: {str(e)}"

    checks.append(DiagnosticCheck(
        name="mDNS Discovery",
        ok=mdns_ok,
        message=mdns_message,
        remediation="Install Avahi (Linux) or ensure Bonjour is enabled (macOS/Windows)" if not mdns_ok else None
    ))

    # Check 3: Port 8000 Reachability
    port_ok = False
    port_message = ""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8000))
        if result == 0:
            port_ok = True
            port_message = "Port 8000 is reachable on localhost"
        else:
            port_message = f"Port 8000 is not reachable (error code: {result})"
        sock.close()
    except Exception as e:
        port_message = f"Port check failed: {str(e)}"

    checks.append(DiagnosticCheck(
        name="Backend Port (8000)",
        ok=port_ok,
        message=port_message,
        remediation="Ensure FastAPI backend is running on port 8000" if not port_ok else None
    ))

    # Check 4: Peer Discovery
    peer_count = 0
    peer_message = ""
    if service and service.is_running:
        try:
            all_peers = await service.list_peers()
            online_peers = [p for p in all_peers if p.status == "online" and p.peer_id != service.peer_id]
            peer_count = len(online_peers)
            if peer_count > 0:
                peer_message = f"Discovered {peer_count} peer(s)"
            else:
                peer_message = "No peers discovered yet"
        except Exception as e:
            peer_message = f"Peer discovery failed: {str(e)}"
    else:
        peer_message = "P2P service not running"

    checks.append(DiagnosticCheck(
        name="Peer Discovery",
        ok=peer_count > 0,
        message=peer_message,
        remediation="Ensure other ElohimOS instances are running on the same network with P2P enabled" if peer_count == 0 else None
    ))

    # Check 5: Firewall
    # This is a heuristic check - just provide guidance
    firewall_message = "Firewall status cannot be auto-detected"
    checks.append(DiagnosticCheck(
        name="Firewall Check",
        ok=True,  # Always pass but provide info
        message=firewall_message,
        remediation="If peer discovery fails, check firewall settings and allow port 8000 for local network"
    ))

    # Check 6: Network Interface
    network_ok = False
    network_message = ""
    try:
        # Try to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        network_ok = True
        network_message = f"Local IP: {local_ip}"
    except Exception as e:
        network_message = f"Network check failed: {str(e)}"

    checks.append(DiagnosticCheck(
        name="Network Interface",
        ok=network_ok,
        message=network_message,
        remediation="Ensure device is connected to a network (WiFi or Ethernet)" if not network_ok else None
    ))

    return RunChecksResponse(checks=checks)
