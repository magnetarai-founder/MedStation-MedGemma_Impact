"""
Collaborative Editing WebSocket Server

Provides real-time collaboration using Yjs CRDT via ypy-websocket.
Supports both notes (markdown) and grid docs (tables).

Security:
- JWT authentication via query param or Sec-WebSocket-Protocol
- Per-document access control (reuse existing permissions)
- Sanitized logging (no document content)

Persistence:
- In-memory Y.Doc for Week 3
- Optional snapshots to PATHS.cache_dir/collab_docs/ for recovery
"""

import logging
import json
import asyncio
import time
from typing import Dict, Optional, Set, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse

from api.config_paths import get_config_paths
from api.rate_limiter import rate_limiter
from api.utils import sanitize_for_log
from api.services.collab_acl import user_can_access_doc
from api.services.collab_state import set_snapshot_applier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collab", tags=["collaboration"])

# Configuration
PATHS = get_config_paths()
COLLAB_DOCS_DIR = PATHS.cache_dir / "collab_docs"
COLLAB_DOCS_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOT_INTERVAL_SECONDS = 300  # 5 minutes
SNAPSHOT_RETENTION_HOURS = 24  # Keep snapshots for 24 hours
MAX_CONNECTIONS_PER_DOC = 50  # Safety limit

# In-memory Y.Doc storage and WebSocket connections
# Format: {doc_id: {"ydoc": Y.Doc, "connections": Set[WebSocket], "last_snapshot": timestamp}}
collab_docs: Dict[str, Dict] = {}

# JWT configuration (reuse from auth_middleware)
try:
    from api.auth_middleware import JWT_SECRET, JWT_ALGORITHM
except ImportError:
    # SECURITY: No hardcoded fallback - require proper secret
    import os
    JWT_SECRET = os.getenv("ELOHIMOS_JWT_SECRET_KEY")
    if not JWT_SECRET:
        raise RuntimeError("ELOHIMOS_JWT_SECRET_KEY must be set - no fallback allowed")
    JWT_ALGORITHM = "HS256"


# ===== Helper Functions =====

def verify_jwt_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and return payload

    Args:
        token: JWT token string

    Returns:
        Payload dict if valid, None otherwise
    """
    try:
        import jwt
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None


def get_or_create_ydoc(doc_id: str) -> Any:
    """
    Get or create Y.Doc for document ID

    Args:
        doc_id: Document UUID

    Returns:
        Y.Doc instance (or MockYDoc if ypy unavailable)
    """
    if doc_id not in collab_docs:
        try:
            # Try ypy import
            try:
                import ypy
            except ImportError:
                logger.error("ypy not installed - install with: pip install ypy")
                # Create mock object for graceful degradation
                class MockYDoc:
                    def __init__(self):
                        self.data = {}

                collab_docs[doc_id] = {
                    "ydoc": MockYDoc(),
                    "connections": set(),
                    "last_snapshot": time.time(),
                    "using_mock": True
                }
                logger.warning(f"Using mock Y.Doc for {doc_id} - ypy not available")
                return collab_docs[doc_id]["ydoc"]

            # Create new Y.Doc
            ydoc = ypy.YDoc()

            # Try to load from snapshot
            snapshot_path = COLLAB_DOCS_DIR / f"{doc_id}.snapshot"
            if snapshot_path.exists():
                try:
                    with open(snapshot_path, "rb") as f:
                        state = f.read()
                        ypy.apply_update(ydoc, state)
                    logger.info(f"Loaded snapshot for doc {sanitize_for_log(doc_id)}")
                except Exception as e:
                    logger.error(f"Failed to load snapshot: {e}")

            collab_docs[doc_id] = {
                "ydoc": ydoc,
                "connections": set(),
                "last_snapshot": time.time(),
                "using_mock": False
            }

        except Exception as e:
            logger.error(f"Failed to create Y.Doc: {e}", exc_info=True)
            # Create mock fallback
            class MockYDoc:
                def __init__(self):
                    self.data = {}

            collab_docs[doc_id] = {
                "ydoc": MockYDoc(),
                "connections": set(),
                "last_snapshot": time.time(),
                "using_mock": True
            }

    return collab_docs[doc_id]["ydoc"]


def save_snapshot(doc_id: str) -> None:
    """
    Save Y.Doc snapshot to disk

    Args:
        doc_id: Document UUID
    """
    if doc_id not in collab_docs:
        return

    doc_data = collab_docs[doc_id]

    # Skip if using mock
    if doc_data.get("using_mock"):
        return

    try:
        import ypy
        ydoc = doc_data["ydoc"]

        # Get document state
        state = ypy.encode_state_as_update(ydoc)

        # Save to file
        snapshot_path = COLLAB_DOCS_DIR / f"{doc_id}.snapshot"
        with open(snapshot_path, "wb") as f:
            f.write(state)

        # Update timestamp
        doc_data["last_snapshot"] = time.time()

        logger.info(
            f"Saved snapshot",
            extra={
                "doc_id": sanitize_for_log(doc_id),
                "size_bytes": len(state)
            }
        )

    except Exception as e:
        logger.error(f"Failed to save snapshot for {doc_id}: {e}")


def cleanup_old_snapshots() -> None:
    """Remove snapshots older than SNAPSHOT_RETENTION_HOURS"""
    try:
        cutoff_time = time.time() - (SNAPSHOT_RETENTION_HOURS * 3600)

        for snapshot_file in COLLAB_DOCS_DIR.glob("*.snapshot"):
            if snapshot_file.stat().st_mtime < cutoff_time:
                snapshot_file.unlink()
                logger.info(f"Removed old snapshot: {snapshot_file.name}")

    except Exception as e:
        logger.error(f"Snapshot cleanup failed: {e}")


async def broadcast_to_doc(doc_id: str, message: bytes, exclude: Optional[WebSocket] = None) -> None:
    """
    Broadcast message to all connections on a document

    Args:
        doc_id: Document UUID
        message: Message bytes to send
        exclude: WebSocket to exclude from broadcast (usually sender)
    """
    if doc_id not in collab_docs:
        return

    connections = collab_docs[doc_id]["connections"].copy()

    for ws in connections:
        if ws != exclude and not ws.client_state.name == "DISCONNECTED":
            try:
                await ws.send_bytes(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                # Remove failed connection
                collab_docs[doc_id]["connections"].discard(ws)


def _apply_snapshot_impl(doc_id: str, snapshot_bytes: bytes) -> bool:
    """
    Apply a snapshot to the in-memory Y.Doc and broadcast to connected clients

    Args:
        doc_id: Document UUID
        snapshot_bytes: Snapshot data to apply

    Returns:
        True on success

    Note: This function is called from REST context (snapshot restore endpoint).
    It's synchronous but safe because collab_docs is a simple dict accessed
    from both WS and REST threads.
    """
    try:
        if doc_id not in collab_docs:
            # Create the doc if it doesn't exist yet
            ydoc = get_or_create_ydoc(doc_id)
        else:
            ydoc = collab_docs[doc_id]["ydoc"]

        # Check if using mock (ypy not available)
        if collab_docs[doc_id].get("using_mock"):
            logger.warning(f"Cannot apply snapshot to mock Y.Doc: {doc_id}")
            return False

        # Apply snapshot using ypy
        try:
            import ypy
            ypy.apply_update(ydoc, snapshot_bytes)
            logger.info(f"Applied snapshot to Y.Doc: {sanitize_for_log(doc_id)}")

            # Note: Broadcasting will happen naturally when clients reconnect and sync,
            # or we could trigger a manual broadcast here if needed. For now, relying
            # on client reconnection is simpler and avoids asyncio context issues.

            # Update last snapshot time
            collab_docs[doc_id]["last_snapshot"] = time.time()

            return True

        except Exception as e:
            logger.error(f"Failed to apply ypy snapshot: {e}", exc_info=True)
            return False

    except Exception as e:
        logger.error(f"Snapshot apply failed for {doc_id}: {e}", exc_info=True)
        return False


# Register the snapshot applier on module load
set_snapshot_applier(_apply_snapshot_impl)


# ===== Background Tasks =====

async def snapshot_task() -> None:
    """Background task to periodically save snapshots"""
    while True:
        try:
            await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)

            for doc_id, doc_data in list(collab_docs.items()):
                # Only snapshot if there are active connections
                if len(doc_data["connections"]) > 0:
                    # Check if snapshot is due
                    if time.time() - doc_data["last_snapshot"] > SNAPSHOT_INTERVAL_SECONDS:
                        save_snapshot(doc_id)

            # Cleanup old snapshots
            cleanup_old_snapshots()

        except Exception as e:
            logger.error(f"Snapshot task error: {e}")


# Snapshot task will be started by FastAPI lifespan event
# Don't start here as event loop may not be running during import
_snapshot_task: Optional[asyncio.Task] = None

async def start_snapshot_task() -> None:
    """Start the background snapshot task (called by app lifespan)"""
    global _snapshot_task
    if _snapshot_task is None:
        _snapshot_task = asyncio.create_task(snapshot_task())
        logger.info("✅ Snapshot task started")

async def stop_snapshot_task() -> None:
    """Stop the background snapshot task (called by app shutdown)"""
    global _snapshot_task
    if _snapshot_task:
        _snapshot_task.cancel()
        try:
            await _snapshot_task
        except asyncio.CancelledError:
            pass
        _snapshot_task = None
        logger.info("✅ Snapshot task stopped")


# ===== WebSocket Endpoint =====

@router.websocket("/ws/{doc_id}")
async def collab_websocket(
    websocket: WebSocket,
    doc_id: str,
    token: Optional[str] = Query(None)
) -> None:
    """
    WebSocket endpoint for real-time collaborative editing

    Supports Yjs CRDT synchronization for:
    - Notes (Markdown) via Y.Text
    - Grid docs (Tables) via Y.Array<Y.Map>

    Authentication:
    - JWT token via query param: ?token=xxx
    - OR via Sec-WebSocket-Protocol header

    Rate limiting: 10 connections per IP per minute
    """
    # Extract token from Sec-WebSocket-Protocol if not in query
    if not token:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        for protocol in protocols.split(","):
            protocol = protocol.strip()
            if protocol.startswith("jwt-"):
                token = protocol[4:]  # Remove "jwt-" prefix
                break

    # Verify authentication
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        logger.warning("WebSocket rejected: no token")
        return

    payload = verify_jwt_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning("WebSocket rejected: invalid token")
        return

    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token payload")
        return

    # ACL check: verify user has access to this document
    try:
        if not user_can_access_doc(user_id, doc_id, min_role="view"):
            await websocket.close(code=1008, reason="Access denied")
            logger.warning(
                "WebSocket ACL denied",
                extra={
                    "user_id": user_id,
                    "doc_id": sanitize_for_log(doc_id)
                }
            )
            return
    except Exception as e:
        logger.error(f"ACL check failed: {e}", exc_info=True)
        await websocket.close(code=1008, reason="Access control error")
        return

    # Rate limiting
    client_ip = websocket.client.host if websocket.client else "unknown"
    rate_key = f"collab_ws:{client_ip}"
    if not rate_limiter.check_rate_limit(rate_key, max_requests=10, window_seconds=60):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        logger.warning(f"WebSocket rate limited: {client_ip}")
        return

    # Check connection limit per document
    if doc_id in collab_docs and len(collab_docs[doc_id]["connections"]) >= MAX_CONNECTIONS_PER_DOC:
        await websocket.close(code=1008, reason="Document connection limit reached")
        logger.warning(f"Doc connection limit reached: {doc_id}")
        return

    # Accept connection
    await websocket.accept()

    # Get or create Y.Doc
    ydoc = get_or_create_ydoc(doc_id)

    # Add to connections
    if doc_id not in collab_docs:
        collab_docs[doc_id] = {
            "ydoc": ydoc,
            "connections": set(),
            "last_snapshot": time.time()
        }

    collab_docs[doc_id]["connections"].add(websocket)

    logger.info(
        "WebSocket connected",
        extra={
            "user_id": user_id,
            "doc_id": sanitize_for_log(doc_id),
            "connections": len(collab_docs[doc_id]["connections"])
        }
    )

    # Send initial sync (if ypy is available)
    if not collab_docs[doc_id].get("using_mock"):
        try:
            import ypy
            state = ypy.encode_state_as_update(ydoc)
            await websocket.send_bytes(state)
        except Exception as e:
            logger.error(f"Failed to send initial sync: {e}")

    try:
        # Message loop
        while True:
            # Receive update from client
            message = await websocket.receive_bytes()

            # Apply update to Y.Doc (if ypy available)
            if not collab_docs[doc_id].get("using_mock"):
                try:
                    import ypy
                    ypy.apply_update(ydoc, message)
                except Exception as e:
                    logger.error(f"Failed to apply update: {e}")

            # Broadcast to other connections
            await broadcast_to_doc(doc_id, message, exclude=websocket)

    except WebSocketDisconnect:
        # Remove connection
        if doc_id in collab_docs:
            collab_docs[doc_id]["connections"].discard(websocket)

            # Save snapshot on disconnect
            if len(collab_docs[doc_id]["connections"]) == 0:
                save_snapshot(doc_id)
                # Keep Y.Doc in memory for quick reconnection
                # Could optionally delete after timeout

        logger.info(
            "WebSocket disconnected",
            extra={
                "user_id": user_id,
                "doc_id": sanitize_for_log(doc_id),
                "remaining_connections": len(collab_docs.get(doc_id, {}).get("connections", set()))
            }
        )

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if doc_id in collab_docs:
            collab_docs[doc_id]["connections"].discard(websocket)


# ===== REST Endpoints =====

@router.get("/docs/{doc_id}/status", response_model=None)
async def get_doc_status(doc_id: str):
    """
    Get collaboration status for a document

    Returns:
    - active_connections: Number of active connections
    - last_snapshot: Timestamp of last snapshot
    """
    if doc_id not in collab_docs:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Document not found in collaboration system"}
        )

    doc_data = collab_docs[doc_id]

    return {
        "doc_id": doc_id,
        "active_connections": len(doc_data["connections"]),
        "last_snapshot": datetime.fromtimestamp(doc_data["last_snapshot"]).isoformat(),
        "using_mock": doc_data.get("using_mock", False)
    }


@router.post("/docs/{doc_id}/snapshot", response_model=None)
async def trigger_snapshot(doc_id: str):
    """
    Manually trigger snapshot save for a document
    """
    if doc_id not in collab_docs:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Document not found"}
        )

    save_snapshot(doc_id)

    return {
        "success": True,
        "message": "Snapshot saved",
        "doc_id": doc_id
    }
