"""
Mesh Relay Models - Data structures for mesh networking

RouteMetrics: Metrics for route quality
MeshMessage: Messages that can be relayed through the mesh
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RouteMetrics:
    """Metrics for a route between peers"""
    latency_ms: float
    hop_count: int
    reliability: float  # 0.0 - 1.0
    last_measured: str


@dataclass
class MeshMessage:
    """Message that can be relayed through the mesh"""
    message_id: str
    source_peer_id: str
    dest_peer_id: str
    payload: dict
    ttl: int  # Time-to-live (max hops)
    route_history: List[str]  # Peer IDs in route
    timestamp: str
