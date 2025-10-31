#!/usr/bin/env python3
"""
FastAPI Router for Offline Mesh Networking
Exposes all offline collaboration features via REST API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from offline_mesh_discovery import get_mesh_discovery, LocalPeer
from offline_file_share import get_file_share, SharedFile, FileTransferProgress
from mesh_relay import get_mesh_relay, MeshMessage
from offline_data_sync import get_data_sync, SyncState
from mlx_distributed import get_mlx_distributed, ComputeNode, DistributedJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mesh", tags=["Offline Mesh"])


# ============================================================================
# PEER DISCOVERY ENDPOINTS
# ============================================================================

@router.post("/discovery/start")
async def start_discovery(request: Request, display_name: str, device_name: str):
    """Start mDNS peer discovery on local network"""
    try:
        discovery = get_mesh_discovery(display_name, device_name)
        success = await discovery.start()

        if success:
            return {
                "status": "started",
                "peer_id": discovery.peer_id,
                "display_name": display_name,
                "device_name": device_name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start discovery")

    except Exception as e:
        logger.error(f"Failed to start discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/peers")
async def get_discovered_peers():
    """Get list of discovered peers on local network"""
    try:
        discovery = get_mesh_discovery()
        peers = discovery.get_peers()

        return {
            "count": len(peers),
            "peers": [
                {
                    "peer_id": p.peer_id,
                    "display_name": p.display_name,
                    "device_name": p.device_name,
                    "ip_address": p.ip_address,
                    "port": p.port,
                    "capabilities": p.capabilities,
                    "status": p.status,
                    "last_seen": p.last_seen
                }
                for p in peers
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/stats")
async def get_discovery_stats():
    """Get discovery statistics"""
    try:
        discovery = get_mesh_discovery()
        return discovery.get_stats()

    except Exception as e:
        logger.error(f"Failed to get discovery stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery/stop")
async def stop_discovery(request: Request):
    """Stop peer discovery"""
    try:
        discovery = get_mesh_discovery()
        await discovery.stop()

        return {"status": "stopped"}

    except Exception as e:
        logger.error(f"Failed to stop discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FILE SHARING ENDPOINTS
# ============================================================================

class ShareFileRequest(BaseModel):
    file_path: str
    shared_by_peer_id: str
    shared_by_name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/files/share")
async def share_file(request: Request, body: ShareFileRequest):
    """Share a file on the local mesh network"""
    try:
        file_share = get_file_share()

        file_path = Path(body.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        shared_file = await file_share.share_file(
            file_path=file_path,
            shared_by_peer_id=body.shared_by_peer_id,
            shared_by_name=body.shared_by_name,
            description=body.description,
            tags=body.tags
        )

        return {
            "file_id": shared_file.file_id,
            "filename": shared_file.filename,
            "size_bytes": shared_file.size_bytes,
            "sha256_hash": shared_file.sha256_hash,
            "shared_at": shared_file.shared_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to share file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/list")
async def list_shared_files(tags: Optional[str] = None):
    """Get list of shared files (optionally filtered by tags)"""
    try:
        file_share = get_file_share()

        tag_list = tags.split(',') if tags else None
        files = file_share.get_shared_files(tags=tag_list)

        return {
            "count": len(files),
            "files": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "size_bytes": f.size_bytes,
                    "size_mb": f.size_bytes / (1024 * 1024),
                    "mime_type": f.mime_type,
                    "shared_by_name": f.shared_by_name,
                    "shared_at": f.shared_at,
                    "description": f.description,
                    "tags": f.tags
                }
                for f in files
            ]
        }

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DownloadFileRequest(BaseModel):
    file_id: str
    peer_ip: str
    peer_port: int
    destination_path: str


@router.post("/files/download")
async def download_file(request: Request, body: DownloadFileRequest):
    """Download file from peer"""
    try:
        file_share = get_file_share()

        destination = Path(body.destination_path)

        downloaded_path = await file_share.download_file(
            file_id=body.file_id,
            peer_ip=body.peer_ip,
            peer_port=body.peer_port,
            destination=destination
        )

        return {
            "status": "completed",
            "file_path": str(downloaded_path)
        }

    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/transfers")
async def get_active_transfers():
    """Get active file transfers"""
    try:
        file_share = get_file_share()
        transfers = file_share.get_active_transfers()

        return {
            "count": len(transfers),
            "transfers": [
                {
                    "file_id": t.file_id,
                    "filename": t.filename,
                    "bytes_transferred": t.bytes_transferred,
                    "total_bytes": t.total_bytes,
                    "progress_percent": (t.bytes_transferred / t.total_bytes * 100) if t.total_bytes > 0 else 0,
                    "speed_mbps": t.speed_mbps,
                    "eta_seconds": t.eta_seconds,
                    "status": t.status
                }
                for t in transfers
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get transfers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_shared_file(request: Request, file_id: str):
    """Remove file from sharing"""
    try:
        file_share = get_file_share()

        success = await file_share.delete_shared_file(file_id)

        if not success:
            raise HTTPException(status_code=404, detail="File not found")

        return {"status": "deleted", "file_id": file_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/stats")
async def get_file_sharing_stats():
    """Get file sharing statistics"""
    try:
        file_share = get_file_share()
        return file_share.get_stats()

    except Exception as e:
        logger.error(f"Failed to get file stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MESH RELAY ENDPOINTS
# ============================================================================

@router.post("/relay/peer/add")
async def add_relay_peer(request: Request, peer_id: str, latency_ms: float = 10.0):
    """Add a direct peer to relay network"""
    try:
        relay = get_mesh_relay()
        relay.add_direct_peer(peer_id, latency_ms)

        return {
            "status": "added",
            "peer_id": peer_id,
            "latency_ms": latency_ms
        }

    except Exception as e:
        logger.error(f"Failed to add peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relay/peer/{peer_id}")
async def remove_relay_peer(request: Request, peer_id: str):
    """Remove peer from relay network"""
    try:
        relay = get_mesh_relay()
        relay.remove_direct_peer(peer_id)

        return {"status": "removed", "peer_id": peer_id}

    except Exception as e:
        logger.error(f"Failed to remove peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SendMessageRequest(BaseModel):
    dest_peer_id: str
    payload: Dict[str, Any]
    ttl: Optional[int] = None


@router.post("/relay/send")
async def send_relay_message(request: Request, body: SendMessageRequest):
    """Send message through relay network"""
    try:
        relay = get_mesh_relay()

        success = await relay.send_message(
            dest_peer_id=body.dest_peer_id,
            payload=body.payload,
            ttl=body.ttl
        )

        if success:
            return {"status": "sent", "dest_peer_id": body.dest_peer_id}
        else:
            return {"status": "queued", "dest_peer_id": body.dest_peer_id, "reason": "no_route"}

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/route/{peer_id}")
async def get_route_to_peer(peer_id: str):
    """Get route to destination peer"""
    try:
        relay = get_mesh_relay()
        route = relay.get_route_to(peer_id)

        if route:
            return {
                "dest_peer_id": peer_id,
                "route": route,
                "hop_count": len(route) - 1
            }
        else:
            raise HTTPException(status_code=404, detail="No route found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/stats")
async def get_relay_stats():
    """Get relay statistics"""
    try:
        relay = get_mesh_relay()
        return relay.get_stats()

    except Exception as e:
        logger.error(f"Failed to get relay stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relay/routing-table")
async def get_routing_table():
    """Get current routing table"""
    try:
        relay = get_mesh_relay()
        return relay.get_routing_table()

    except Exception as e:
        logger.error(f"Failed to get routing table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA SYNC ENDPOINTS
# ============================================================================

class SyncRequest(BaseModel):
    peer_id: str
    tables: Optional[List[str]] = None


@router.post("/sync/start")
async def start_sync(request: Request, body: SyncRequest):
    """Start data synchronization with peer"""
    try:
        sync = get_data_sync()

        state = await sync.sync_with_peer(
            peer_id=body.peer_id,
            tables=body.tables
        )

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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/state/{peer_id}")
async def get_sync_state(peer_id: str):
    """Get sync state with specific peer"""
    try:
        sync = get_data_sync()
        state = sync.get_sync_state(peer_id)

        if not state:
            raise HTTPException(status_code=404, detail="No sync state found")

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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/states")
async def get_all_sync_states():
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/stats")
async def get_sync_stats():
    """Get data sync statistics"""
    try:
        sync = get_data_sync()
        return sync.get_stats()

    except Exception as e:
        logger.error(f"Failed to get sync stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SyncExchangeRequest(BaseModel):
    """Sync operation exchange request"""
    sender_peer_id: str
    operations: List[Dict[str, Any]]


@router.post("/sync/exchange")
async def exchange_sync_operations(request: Request, body: SyncExchangeRequest):
    """
    Exchange sync operations with peer (called by remote peer during sync)

    This endpoint receives operations from a remote peer and returns
    our operations for them to apply.
    """
    try:
        sync = get_data_sync()

        # Parse incoming operations
        from offline_data_sync import SyncOperation
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
        logger.info(f"Applied {len(incoming_ops)} operations from {body.sender_peer_id} ({conflicts} conflicts)")

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
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MLX DISTRIBUTED COMPUTING ENDPOINTS
# ============================================================================

@router.post("/compute/start")
async def start_compute_server(request: Request, port: int = 8766):
    """Start MLX distributed compute server"""
    try:
        distributed = get_mlx_distributed()

        success = await distributed.start_server()

        if success:
            return {
                "status": "started",
                "node_id": distributed.local_node_id,
                "device_name": distributed.device_name,
                "port": distributed.port
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start compute server")

    except Exception as e:
        logger.error(f"Failed to start compute server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compute/nodes")
async def get_compute_nodes():
    """Get available compute nodes"""
    try:
        distributed = get_mlx_distributed()
        nodes = distributed.get_nodes()

        return {
            "count": len(nodes),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "device_name": n.device_name,
                    "ip_address": n.ip_address,
                    "port": n.port,
                    "gpu_memory_gb": n.gpu_memory_gb,
                    "cpu_cores": n.cpu_cores,
                    "metal_version": n.metal_version,
                    "status": n.status,
                    "current_load": n.current_load,
                    "jobs_completed": n.jobs_completed
                }
                for n in nodes
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get compute nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SubmitJobRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_* fields

    job_type: str  # 'embedding', 'inference', 'training'
    data: Any
    model_name: Optional[str] = None


@router.post("/compute/job/submit")
async def submit_compute_job(request: Request, body: SubmitJobRequest):
    """Submit job for distributed execution"""
    try:
        distributed = get_mlx_distributed()

        job = await distributed.submit_job(
            job_type=body.job_type,
            data=body.data,
            model_name=body.model_name
        )

        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "assigned_node": job.assigned_node,
            "created_at": job.created_at
        }

    except Exception as e:
        logger.error(f"Failed to submit job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compute/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        distributed = get_mlx_distributed()
        job = distributed.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "assigned_node": job.assigned_node,
            "result": job.result,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compute/stats")
async def get_compute_stats():
    """Get distributed computing statistics"""
    try:
        distributed = get_mlx_distributed()
        return distributed.get_stats()

    except Exception as e:
        logger.error(f"Failed to get compute stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
