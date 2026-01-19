"""
Offline Mesh - Data Sync Routes

CRDT-based data synchronization endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from api.errors import http_404, http_500
from typing import Dict, Any
import logging

from api.offline_data_sync import get_data_sync, SyncOperation
from api.utils import sanitize_for_log
from api.metrics import get_metrics
from api.offline_mesh.models import (
    SyncRequest,
    SyncExchangeRequest,
    SyncResponse,
)

logger = logging.getLogger(__name__)
metrics = get_metrics()

router = APIRouter()


@router.post("/sync/start", response_model=SyncResponse)
async def start_sync(request: Request, body: SyncRequest) -> SyncResponse:
    """
    Start data synchronization with peer

    Initiates bidirectional CRDT-based sync of specified database tables with
    a discovered peer. Uses operation-based CRDTs for conflict-free replication.

    Flow:
    1. Establishes sync session with target peer
    2. Exchanges vector clocks to determine divergence
    3. Sends missing operations to peer (causal ordering preserved)
    4. Receives peer's operations and applies them locally
    5. Resolves any conflicts using CRDT merge semantics
    6. Updates sync state and vector clock

    Conflict Resolution:
        - Last-write-wins (LWW) for simple values with Lamport timestamps
        - Set union for collection types
        - Custom merge functions for complex data types
        - All conflicts auto-resolved; manual intervention never required

    Args:
        peer_id: Target peer UUID (from discovery)
        tables: List of table names to sync (e.g., ["chat_sessions", "vault_files"])

    Returns:
        status: Sync completion status
        operations_sent: Count of ops sent to peer
        operations_received: Count of ops received from peer
        conflicts_resolved: Count of auto-resolved conflicts

    Notes:
        - Requires active discovery session (POST /discovery/start)
        - Sync is incremental; only sends operations since last sync
        - Safe to call repeatedly; idempotent
    """
    # METRICS: Track P2P sync operation
    with metrics.track("p2p_sync"):
        try:
            sync = get_data_sync()

            state = await sync.sync_with_peer(
                peer_id=body.peer_id,
                tables=body.tables
            )

            # METRICS: Record sync metrics
            metrics.record("p2p_ops_sent", state.operations_sent)
            metrics.record("p2p_ops_received", state.operations_received)
            metrics.record("p2p_conflicts_resolved", state.conflicts_resolved)

            return {
                "status": state.status,
                "peer_id": state.peer_id,
                "last_sync": state.last_sync,
                "operations_sent": state.operations_sent,
                "operations_received": state.operations_received,
                "conflicts_resolved": state.conflicts_resolved
            }

        except Exception as e:
            logger.error(f"Failed to sync: {e}")
            metrics.increment_error("p2p_sync")
            raise http_500(str(e))


@router.get("/sync/state/{peer_id}")
async def get_sync_state(peer_id: str) -> Dict[str, Any]:
    """Get sync state with specific peer"""
    try:
        sync = get_data_sync()
        state = sync.get_sync_state(peer_id)

        if not state:
            raise http_404("No sync state found", resource="sync_state")

        return {
            "peer_id": state.peer_id,
            "last_sync": state.last_sync,
            "operations_sent": state.operations_sent,
            "operations_received": state.operations_received,
            "conflicts_resolved": state.conflicts_resolved,
            "status": state.status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync state: {e}")
        raise http_500(str(e))


@router.get("/sync/states")
async def get_all_sync_states() -> Dict[str, Any]:
    """Get all peer sync states"""
    try:
        sync = get_data_sync()
        states = sync.get_all_sync_states()

        return {
            "count": len(states),
            "states": [
                {
                    "peer_id": s.peer_id,
                    "last_sync": s.last_sync,
                    "operations_sent": s.operations_sent,
                    "operations_received": s.operations_received,
                    "conflicts_resolved": s.conflicts_resolved,
                    "status": s.status
                }
                for s in states
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get sync states: {e}")
        raise http_500(str(e))


@router.get("/sync/stats")
async def get_sync_stats() -> Dict[str, Any]:
    """Get data sync statistics"""
    try:
        sync = get_data_sync()
        return sync.get_stats()

    except Exception as e:
        logger.error(f"Failed to get sync stats: {e}")
        raise http_500(str(e))


@router.post("/sync/exchange")
async def exchange_sync_operations(request: Request, body: SyncExchangeRequest) -> Dict[str, Any]:
    """
    Exchange sync operations with peer (called by remote peer during sync)

    This endpoint receives operations from a remote peer and returns
    our operations for them to apply.
    """
    try:
        sync = get_data_sync()

        # Parse incoming operations
        incoming_ops = []
        for op_data in body.operations:
            op = SyncOperation(
                op_id=op_data['op_id'],
                table_name=op_data['table_name'],
                operation=op_data['operation'],
                row_id=op_data['row_id'],
                data=op_data.get('data'),
                timestamp=op_data['timestamp'],
                peer_id=op_data['peer_id'],
                version=op_data['version']
            )
            incoming_ops.append(op)

        # Apply incoming operations
        conflicts = await sync._apply_operations(incoming_ops)
        safe_peer_id = sanitize_for_log(body.sender_peer_id)
        logger.info(f"Applied {len(incoming_ops)} operations from {safe_peer_id} ({conflicts} conflicts)")

        # Get our operations to send back
        ops_to_return = await sync._get_operations_since_last_sync(body.sender_peer_id, tables=None)

        # Format response
        return {
            "operations": [
                {
                    'op_id': op.op_id,
                    'table_name': op.table_name,
                    'operation': op.operation,
                    'row_id': op.row_id,
                    'data': op.data,
                    'timestamp': op.timestamp,
                    'peer_id': op.peer_id,
                    'version': op.version
                }
                for op in ops_to_return
            ],
            "conflicts_resolved": conflicts,
            "operations_applied": len(incoming_ops)
        }

    except Exception as e:
        logger.error(f"Failed to exchange sync operations: {e}")
        raise http_500(str(e))
