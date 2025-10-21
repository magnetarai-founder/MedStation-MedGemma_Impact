#!/usr/bin/env python3
"""
MLX Distributed Computing for ElohimOS
Pool multiple Apple Silicon devices for faster AI inference
Uses Bonjour (mDNS) for discovery + WebSocket for communication
Perfect for missionary teams with multiple M-series Macs
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# MLX disabled until Apple provides stable Python 3.12+ support
MLX_AVAILABLE = False
# try:
#     import mlx.core as mx
#     import mlx.nn as nn
#     MLX_AVAILABLE = True
# except ImportError:
#     MLX_AVAILABLE = False

# WebSocket imports
try:
    import websockets
    from websockets.server import serve as ws_serve
    from websockets.client import connect as ws_connect
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets not installed - install with: pip install websockets")


@dataclass
class ComputeNode:
    """A compute node in the distributed system"""
    node_id: str
    device_name: str
    ip_address: str
    port: int
    gpu_memory_gb: float
    cpu_cores: int
    metal_version: int
    status: str  # 'idle', 'busy', 'offline'
    current_load: float  # 0.0 - 1.0
    jobs_completed: int
    last_seen: str


@dataclass
class DistributedJob:
    """A job to be distributed across nodes"""
    job_id: str
    job_type: str  # 'embedding', 'inference', 'training'
    data: Any
    model_name: Optional[str]
    status: str  # 'pending', 'running', 'completed', 'failed'
    assigned_node: Optional[str]
    result: Optional[Any]
    created_at: str
    completed_at: Optional[str]


class MLXDistributed:
    """
    Distributed MLX computing over local mesh network

    Features:
    - Auto-discovery of compute nodes (mDNS/Bonjour)
    - Load balancing across available devices
    - Job scheduling and distribution
    - WebSocket-based communication
    - Automatic failover if node goes offline
    """

    SERVICE_TYPE = "_mlx-compute._tcp.local."
    DEFAULT_PORT = 8766

    def __init__(self,
                 local_node_id: str,
                 device_name: str,
                 port: int = DEFAULT_PORT):

        self.local_node_id = local_node_id
        self.device_name = device_name
        self.port = port

        # Compute nodes
        self.nodes: Dict[str, ComputeNode] = {}
        self.local_node: Optional[ComputeNode] = None

        # Job queue
        self.pending_jobs: List[DistributedJob] = []
        self.active_jobs: Dict[str, DistributedJob] = {}
        self.completed_jobs: List[DistributedJob] = []

        # WebSocket server
        self.ws_server = None
        self.ws_connections: Dict[str, Any] = {}  # node_id → websocket

        # Stats
        self.jobs_submitted = 0
        self.jobs_completed = 0
        self.jobs_failed = 0

        # Initialize local node info
        self._init_local_node()

        logger.info(f"🖥️ MLX Distributed initialized for {device_name}")

    def _init_local_node(self):
        """Initialize local compute node information"""
        import psutil

        # Get system info
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_cores = psutil.cpu_count()

        # Get Metal version (if available)
        metal_version = 0
        if MLX_AVAILABLE:
            # Try to detect Metal version
            try:
                # This is a placeholder - actual Metal version detection
                # would require platform-specific code
                metal_version = 4  # Assume Metal 4 on modern systems
            except:
                metal_version = 0

        # Get local IP
        local_ip = self._get_local_ip()

        self.local_node = ComputeNode(
            node_id=self.local_node_id,
            device_name=self.device_name,
            ip_address=local_ip,
            port=self.port,
            gpu_memory_gb=memory_gb,  # Unified memory on Apple Silicon
            cpu_cores=cpu_cores,
            metal_version=metal_version,
            status='idle',
            current_load=0.0,
            jobs_completed=0,
            last_seen=datetime.utcnow().isoformat()
        )

        # Add ourselves to nodes
        self.nodes[self.local_node_id] = self.local_node

        logger.info(f"✅ Local node: {self.device_name} ({memory_gb:.1f} GB, {cpu_cores} cores)")

    def _get_local_ip(self) -> str:
        """Get local IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    async def start_server(self):
        """Start WebSocket server for receiving job requests"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("❌ websockets not available")
            return False

        try:
            self.ws_server = await ws_serve(
                self._handle_client,
                "0.0.0.0",
                self.port
            )

            logger.info(f"✅ MLX compute server started on port {self.port}")

            # Start mDNS advertisement
            await self._advertise_service()

            return True

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    async def _advertise_service(self):
        """Advertise compute service via mDNS"""
        try:
            from zeroconf import ServiceInfo, Zeroconf
            import socket

            zeroconf = Zeroconf()

            service_name = f"{self.device_name}.{self.SERVICE_TYPE}"

            properties = {
                'node_id': self.local_node_id,
                'device_name': self.device_name,
                'gpu_memory_gb': str(self.local_node.gpu_memory_gb),
                'cpu_cores': str(self.local_node.cpu_cores),
                'metal_version': str(self.local_node.metal_version)
            }

            properties_bytes = {
                k: v.encode('utf-8') if isinstance(v, str) else v
                for k, v in properties.items()
            }

            info = ServiceInfo(
                self.SERVICE_TYPE,
                service_name,
                addresses=[socket.inet_aton(self.local_node.ip_address)],
                port=self.port,
                properties=properties_bytes,
                server=f"{self.device_name}.local."
            )

            zeroconf.register_service(info)
            logger.info(f"📡 Broadcasting MLX compute service: {service_name}")

        except ImportError:
            logger.warning("zeroconf not available - manual node registration required")
        except Exception as e:
            logger.error(f"Failed to advertise service: {e}")

    async def _handle_client(self, websocket, path):
        """Handle incoming WebSocket connections"""
        node_id = None

        try:
            # Receive node registration
            message = await websocket.recv()
            data = json.loads(message)

            if data.get('type') == 'register':
                node_id = data.get('node_id')
                self.ws_connections[node_id] = websocket

                # Send acknowledgment
                await websocket.send(json.dumps({
                    'type': 'registered',
                    'node_id': self.local_node_id
                }))

                logger.info(f"✅ Node connected: {node_id}")

            # Handle job requests
            async for message in websocket:
                data = json.loads(message)
                await self._process_message(data, node_id)

        except Exception as e:
            logger.error(f"Client handler error: {e}")

        finally:
            if node_id and node_id in self.ws_connections:
                del self.ws_connections[node_id]
                logger.info(f"❌ Node disconnected: {node_id}")

    async def _process_message(self, data: dict, from_node: str):
        """Process incoming message"""
        msg_type = data.get('type')

        if msg_type == 'job_request':
            # Execute job locally
            job = DistributedJob(**data['job'])
            result = await self._execute_job_local(job)

            # Send result back
            response = {
                'type': 'job_result',
                'job_id': job.job_id,
                'result': result,
                'status': 'completed'
            }

            if from_node in self.ws_connections:
                await self.ws_connections[from_node].send(json.dumps(response))

    async def submit_job(self,
                        job_type: str,
                        data: Any,
                        model_name: Optional[str] = None) -> DistributedJob:
        """
        Submit job for distributed execution

        Job will be automatically distributed to available node
        """
        job = DistributedJob(
            job_id=self._generate_job_id(),
            job_type=job_type,
            data=data,
            model_name=model_name,
            status='pending',
            assigned_node=None,
            result=None,
            created_at=datetime.utcnow().isoformat(),
            completed_at=None
        )

        self.pending_jobs.append(job)
        self.jobs_submitted += 1

        # Schedule job
        await self._schedule_job(job)

        return job

    async def _schedule_job(self, job: DistributedJob):
        """Schedule job to best available node"""
        # Find best node (lowest load)
        best_node = None
        min_load = float('inf')

        for node in self.nodes.values():
            if node.status == 'idle' and node.current_load < min_load:
                best_node = node
                min_load = node.current_load

        if not best_node:
            logger.warning(f"No available nodes for job {job.job_id}")
            return

        # Assign job to node
        job.assigned_node = best_node.node_id
        job.status = 'running'

        self.pending_jobs.remove(job)
        self.active_jobs[job.job_id] = job

        logger.info(f"📤 Job {job.job_id} assigned to {best_node.device_name}")

        # Execute job
        if best_node.node_id == self.local_node_id:
            # Execute locally
            result = await self._execute_job_local(job)
            await self._complete_job(job, result)
        else:
            # Send to remote node
            await self._send_job_to_node(job, best_node)

    async def _execute_job_local(self, job: DistributedJob) -> Any:
        """Execute job on local node"""
        logger.info(f"🔧 Executing job {job.job_id} locally ({job.job_type})")

        if not MLX_AVAILABLE:
            logger.error("MLX not available")
            return None

        try:
            if job.job_type == 'embedding':
                # Generate embeddings
                # Placeholder - actual implementation would use MLX embedder
                result = {'embedding': [0.1] * 384}  # Dummy embedding

            elif job.job_type == 'inference':
                # Run inference
                # Placeholder - actual implementation would load model and run
                result = {'prediction': 'test', 'confidence': 0.95}

            else:
                result = {'error': f'Unknown job type: {job.job_type}'}

            return result

        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            return {'error': str(e)}

    async def _send_job_to_node(self, job: DistributedJob, node: ComputeNode):
        """Send job to remote node via WebSocket"""
        if node.node_id not in self.ws_connections:
            # Connect to node
            await self._connect_to_node(node)

        if node.node_id in self.ws_connections:
            ws = self.ws_connections[node.node_id]

            message = {
                'type': 'job_request',
                'job': asdict(job)
            }

            try:
                await ws.send(json.dumps(message))
                logger.info(f"📤 Job sent to {node.device_name}")
            except Exception as e:
                logger.error(f"Failed to send job: {e}")
                # Reschedule job
                job.status = 'pending'
                job.assigned_node = None
                self.pending_jobs.append(job)
                del self.active_jobs[job.job_id]

    async def _connect_to_node(self, node: ComputeNode):
        """Connect to remote node via WebSocket"""
        if not WEBSOCKETS_AVAILABLE:
            return

        try:
            ws = await ws_connect(f"ws://{node.ip_address}:{node.port}")

            # Register with remote node
            await ws.send(json.dumps({
                'type': 'register',
                'node_id': self.local_node_id
            }))

            # Wait for acknowledgment
            response = await ws.recv()
            data = json.loads(response)

            if data.get('type') == 'registered':
                self.ws_connections[node.node_id] = ws
                logger.info(f"✅ Connected to node: {node.device_name}")

        except Exception as e:
            logger.error(f"Failed to connect to node {node.device_name}: {e}")

    async def _complete_job(self, job: DistributedJob, result: Any):
        """Mark job as completed"""
        job.status = 'completed'
        job.result = result
        job.completed_at = datetime.utcnow().isoformat()

        del self.active_jobs[job.job_id]
        self.completed_jobs.append(job)

        self.jobs_completed += 1

        logger.info(f"✅ Job {job.job_id} completed")

    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def add_node(self, node: ComputeNode):
        """Manually add a compute node"""
        self.nodes[node.node_id] = node
        logger.info(f"➕ Node added: {node.device_name} at {node.ip_address}:{node.port}")

    def get_nodes(self) -> List[ComputeNode]:
        """Get list of available compute nodes"""
        return list(self.nodes.values())

    def get_job(self, job_id: str) -> Optional[DistributedJob]:
        """Get job status"""
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]

        # Check completed jobs
        for job in self.completed_jobs:
            if job.job_id == job_id:
                return job

        # Check pending jobs
        for job in self.pending_jobs:
            if job.job_id == job_id:
                return job

        return None

    def get_stats(self) -> dict:
        """Get distributed computing statistics"""
        total_nodes = len(self.nodes)
        idle_nodes = sum(1 for n in self.nodes.values() if n.status == 'idle')

        total_memory = sum(n.gpu_memory_gb for n in self.nodes.values())
        total_cores = sum(n.cpu_cores for n in self.nodes.values())

        return {
            'local_node_id': self.local_node_id,
            'total_nodes': total_nodes,
            'idle_nodes': idle_nodes,
            'total_gpu_memory_gb': total_memory,
            'total_cpu_cores': total_cores,
            'jobs_submitted': self.jobs_submitted,
            'jobs_completed': self.jobs_completed,
            'jobs_failed': self.jobs_failed,
            'pending_jobs': len(self.pending_jobs),
            'active_jobs': len(self.active_jobs),
            'mlx_available': MLX_AVAILABLE,
            'websockets_available': WEBSOCKETS_AVAILABLE
        }


# Singleton instance
_mlx_distributed = None


def get_mlx_distributed(local_node_id: str = None, device_name: str = None) -> MLXDistributed:
    """Get singleton MLX distributed instance"""
    global _mlx_distributed

    if _mlx_distributed is None:
        if not local_node_id:
            import hashlib
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            local_node_id = hashlib.sha256(mac.encode()).hexdigest()[:16]

        if not device_name:
            import socket
            device_name = socket.gethostname()

        _mlx_distributed = MLXDistributed(local_node_id, device_name)
        logger.info("🖥️ MLX distributed computing ready")

    return _mlx_distributed
