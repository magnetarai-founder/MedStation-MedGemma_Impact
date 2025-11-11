"""
P2P Mesh Service for Network Selector

Wrapper around existing p2p_chat_service for the Network Selector UI.
Provides simple API for peer discovery, connection codes, and mesh networking.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging
import secrets
import string

from api.p2p_chat_service import get_p2p_chat_service, init_p2p_chat_service

logger = logging.getLogger(__name__)

from fastapi import Depends
from auth_middleware import get_current_user

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
from config_paths import get_config_paths
import sqlite3
from datetime import datetime, timedelta

PATHS = get_config_paths()
CODES_DB_PATH = PATHS.data_dir / "p2p_connection_codes.db"


def _init_codes_db():
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


def _save_connection_code(code: str, connection: ConnectionCode):
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
async def start_p2p_mesh(request: Request, display_name: str = "ElohimOS User", device_name: str = "My Device"):
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
async def stop_p2p_mesh(request: Request):
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
async def get_p2p_peers():
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
async def generate_connection_code_endpoint(request: Request):
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
async def connect_to_peer(request: Request, body: AddPeerRequest):
    """
    Connect to a peer using their connection code

    Args:
        request: Connection code from other peer

    Returns:
        Connection status
    """
    try:
        service = get_p2p_chat_service()

        if not service or not service.is_running:
            raise HTTPException(status_code=503, detail="P2P service not running")

        # Look up connection code
        if body.code not in connection_codes:
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
            raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_p2p_mesh_status():
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
