"""
Offline Mesh - Distributed Compute Routes

MLX distributed computing endpoints for mesh network.
"""

from fastapi import APIRouter, HTTPException, Request
from api.errors import http_404, http_500
from typing import Dict, Any
import logging

from api.mlx_distributed import get_mlx_distributed
from api.offline_mesh.models import SubmitJobRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compute/start")
async def start_compute_server(request: Request, port: int = 8766) -> Dict[str, Any]:
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
            raise http_500("Failed to start compute server")

    except Exception as e:
        logger.error(f"Failed to start compute server: {e}")
        raise http_500(str(e))


@router.get("/compute/nodes")
async def get_compute_nodes() -> Dict[str, Any]:
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
        raise http_500(str(e))


@router.post("/compute/job/submit")
async def submit_compute_job(request: Request, body: SubmitJobRequest) -> Dict[str, Any]:
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
        raise http_500(str(e))


@router.get("/compute/job/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get job status"""
    try:
        distributed = get_mlx_distributed()
        job = distributed.get_job(job_id)

        if not job:
            raise http_404("Job not found", resource="job")

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
        raise http_500(str(e))


@router.get("/compute/stats")
async def get_compute_stats() -> Dict[str, Any]:
    """Get distributed computing statistics"""
    try:
        distributed = get_mlx_distributed()
        return distributed.get_stats()

    except Exception as e:
        logger.error(f"Failed to get compute stats: {e}")
        raise http_500(str(e))
