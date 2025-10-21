#!/usr/bin/env python3
"""
Mesh Relay Routing for ElohimOS
Multi-hop message routing when peers can't connect directly
Perfect for missionaries spread across buildings/areas
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


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


class MeshRelay:
    """
    Intelligent mesh relay routing system

    Features:
    - Multi-hop routing (A → B → C)
    - Automatic route discovery
    - Load balancing across multiple paths
    - Dead route detection and failover
    - Message deduplication
    """

    MAX_TTL = 10  # Maximum hops before message expires
    ROUTE_CACHE_SIZE = 1000
    MESSAGE_CACHE_SIZE = 5000  # For deduplication

    def __init__(self, local_peer_id: str):
        self.local_peer_id = local_peer_id

        # Network topology
        self.direct_peers: Set[str] = set()  # Peers we can reach directly
        self.route_table: Dict[str, List[str]] = {}  # dest_peer_id → [next_hop_peer_id, ...]
        self.route_metrics: Dict[Tuple[str, str], RouteMetrics] = {}  # (peer_a, peer_b) → metrics

        # Message tracking
        self.seen_messages: Set[str] = set()  # For deduplication
        self.pending_routes: Dict[str, List[MeshMessage]] = defaultdict(list)  # Queued messages

        # Stats
        self.messages_relayed = 0
        self.routes_discovered = 0
        self.dead_routes_detected = 0

        logger.info(f"🔀 Mesh relay initialized for peer {local_peer_id}")

    def add_direct_peer(self, peer_id: str, latency_ms: float = 10.0):
        """Register a directly connected peer"""
        self.direct_peers.add(peer_id)

        # Update route metrics
        metrics = RouteMetrics(
            latency_ms=latency_ms,
            hop_count=1,
            reliability=1.0,
            last_measured=datetime.utcnow().isoformat()
        )
        self.route_metrics[(self.local_peer_id, peer_id)] = metrics

        # Direct route
        self.route_table[peer_id] = [peer_id]

        logger.info(f"✅ Direct peer added: {peer_id} ({latency_ms}ms)")

    def remove_direct_peer(self, peer_id: str):
        """Remove a peer that disconnected"""
        if peer_id in self.direct_peers:
            self.direct_peers.remove(peer_id)

            # Invalidate routes through this peer
            self._invalidate_routes_through(peer_id)

            logger.info(f"❌ Direct peer removed: {peer_id}")

    def _invalidate_routes_through(self, peer_id: str):
        """Invalidate all routes that go through a specific peer"""
        routes_to_remove = []

        for dest_peer, next_hops in self.route_table.items():
            if peer_id in next_hops:
                # Remove this next hop
                new_hops = [h for h in next_hops if h != peer_id]

                if new_hops:
                    self.route_table[dest_peer] = new_hops
                else:
                    # No routes left to this destination
                    routes_to_remove.append(dest_peer)

        for dest_peer in routes_to_remove:
            del self.route_table[dest_peer]
            logger.debug(f"Route to {dest_peer} invalidated (went through {peer_id})")

    async def send_message(self,
                          dest_peer_id: str,
                          payload: dict,
                          ttl: Optional[int] = None) -> bool:
        """
        Send message to destination peer (with relay if needed)

        Returns True if message was sent, False if no route available
        """
        # Check if we've seen this message before (deduplication)
        message_id = self._generate_message_id(dest_peer_id, payload)

        if message_id in self.seen_messages:
            logger.debug(f"Duplicate message detected: {message_id}")
            return True

        self.seen_messages.add(message_id)

        # Limit cache size
        if len(self.seen_messages) > self.MESSAGE_CACHE_SIZE:
            # Remove oldest (simple: clear half)
            self.seen_messages = set(list(self.seen_messages)[self.MESSAGE_CACHE_SIZE // 2:])

        # Create message
        message = MeshMessage(
            message_id=message_id,
            source_peer_id=self.local_peer_id,
            dest_peer_id=dest_peer_id,
            payload=payload,
            ttl=ttl or self.MAX_TTL,
            route_history=[self.local_peer_id],
            timestamp=datetime.utcnow().isoformat()
        )

        # Check if we have a route
        if dest_peer_id not in self.route_table:
            # No route - queue message and trigger route discovery
            logger.warning(f"No route to {dest_peer_id} - queuing message")
            self.pending_routes[dest_peer_id].append(message)
            await self._discover_route(dest_peer_id)
            return False

        # Get next hop
        next_hops = self.route_table[dest_peer_id]
        if not next_hops:
            logger.error(f"No next hop for {dest_peer_id}")
            return False

        # Choose best next hop (lowest latency)
        next_hop = self._choose_best_hop(next_hops, dest_peer_id)

        # Forward message
        await self._forward_message(message, next_hop)

        self.messages_relayed += 1
        return True

    async def receive_message(self, message: MeshMessage) -> bool:
        """
        Receive and potentially relay a message

        Returns True if message was for us, False if it was relayed
        """
        # Check TTL
        if message.ttl <= 0:
            logger.warning(f"Message {message.message_id} expired (TTL=0)")
            return False

        # Check if we've seen this message (loop detection)
        if message.message_id in self.seen_messages:
            logger.debug(f"Duplicate message ignored: {message.message_id}")
            return False

        self.seen_messages.add(message.message_id)

        # Check if message is for us
        if message.dest_peer_id == self.local_peer_id:
            logger.info(f"📨 Message received from {message.source_peer_id} (via {len(message.route_history)} hops)")
            return True

        # Relay message
        message.ttl -= 1
        message.route_history.append(self.local_peer_id)

        # Find next hop
        if message.dest_peer_id not in self.route_table:
            logger.warning(f"No route to {message.dest_peer_id} - dropping message")
            return False

        next_hops = self.route_table[message.dest_peer_id]
        next_hop = self._choose_best_hop(next_hops, message.dest_peer_id)

        await self._forward_message(message, next_hop)

        self.messages_relayed += 1
        logger.debug(f"🔀 Relayed message {message.message_id} to {next_hop}")

        return False

    async def _forward_message(self, message: MeshMessage, next_hop: str):
        """Forward message to next hop"""
        # This will be implemented by the transport layer (WebSocket, TCP, etc.)
        # For now, just log
        logger.debug(f"Forwarding message {message.message_id} to {next_hop}")

        # TODO: Implement actual message sending via WebSocket/TCP
        # This should integrate with offline_mesh_discovery to get peer IP/port

    def _choose_best_hop(self, next_hops: List[str], dest_peer_id: str) -> str:
        """Choose best next hop based on metrics"""
        if len(next_hops) == 1:
            return next_hops[0]

        # Score each hop
        scored_hops = []

        for hop in next_hops:
            # Get metrics
            metrics = self.route_metrics.get((self.local_peer_id, hop))

            if not metrics:
                # No metrics - give default score
                score = 100.0
            else:
                # Lower score is better
                score = (
                    metrics.latency_ms * 1.0 +
                    metrics.hop_count * 10.0 +
                    (1.0 - metrics.reliability) * 50.0
                )

            scored_hops.append((score, hop))

        # Sort by score and return best
        scored_hops.sort()
        return scored_hops[0][1]

    async def _discover_route(self, dest_peer_id: str):
        """Discover route to destination peer"""
        logger.info(f"🔍 Discovering route to {dest_peer_id}...")

        # Send route request to all direct peers
        route_request = {
            'type': 'route_request',
            'dest_peer_id': dest_peer_id,
            'source_peer_id': self.local_peer_id
        }

        # Broadcast to direct peers
        for peer_id in self.direct_peers:
            # TODO: Actually send route request
            logger.debug(f"Sending route request to {peer_id}")

    def update_route_from_advertisement(self, route_ad: dict):
        """
        Update routing table from route advertisement

        Route advertisements are broadcast periodically by all peers
        """
        peer_id = route_ad.get('peer_id')
        reachable_peers = route_ad.get('reachable_peers', [])

        if not peer_id or not reachable_peers:
            return

        # Update routes through this peer
        for dest_peer, hop_count in reachable_peers:
            if dest_peer == self.local_peer_id:
                continue  # Skip ourselves

            # Check if this is a better route
            current_hop_count = float('inf')

            if dest_peer in self.route_table:
                # Get current best hop count
                for next_hop in self.route_table[dest_peer]:
                    metrics = self.route_metrics.get((self.local_peer_id, next_hop))
                    if metrics:
                        current_hop_count = min(current_hop_count, metrics.hop_count)

            # New route has hop_count + 1 (through advertising peer)
            new_hop_count = hop_count + 1

            if new_hop_count < current_hop_count:
                # Better route found
                self.route_table[dest_peer] = [peer_id]

                # Update metrics
                self.route_metrics[(self.local_peer_id, peer_id)] = RouteMetrics(
                    latency_ms=10.0,  # Default - should be measured
                    hop_count=new_hop_count,
                    reliability=0.95,
                    last_measured=datetime.utcnow().isoformat()
                )

                self.routes_discovered += 1
                logger.info(f"✨ New route discovered: {dest_peer} via {peer_id} ({new_hop_count} hops)")

                # Process pending messages for this destination
                if dest_peer in self.pending_routes:
                    pending = self.pending_routes.pop(dest_peer)
                    for msg in pending:
                        asyncio.create_task(self.send_message(dest_peer, msg.payload, msg.ttl))

    def generate_route_advertisement(self) -> dict:
        """
        Generate route advertisement for broadcasting

        Other peers use this to learn routes through us
        """
        reachable_peers = []

        for dest_peer, next_hops in self.route_table.items():
            if next_hops:
                # Get hop count
                metrics = self.route_metrics.get((self.local_peer_id, next_hops[0]))
                hop_count = metrics.hop_count if metrics else 1

                reachable_peers.append((dest_peer, hop_count))

        return {
            'type': 'route_advertisement',
            'peer_id': self.local_peer_id,
            'reachable_peers': reachable_peers,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _generate_message_id(self, dest_peer_id: str, payload: dict) -> str:
        """Generate unique message ID for deduplication"""
        import hashlib

        content = json.dumps({
            'source': self.local_peer_id,
            'dest': dest_peer_id,
            'payload': payload,
            'timestamp': datetime.utcnow().isoformat()
        }, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_route_to(self, dest_peer_id: str) -> Optional[List[str]]:
        """Get route to destination peer"""
        if dest_peer_id not in self.route_table:
            return None

        next_hops = self.route_table[dest_peer_id]
        if not next_hops:
            return None

        # Return route [us → next_hop → ... → dest]
        # For now, just return next hop
        return [self.local_peer_id, next_hops[0], dest_peer_id]

    def get_stats(self) -> dict:
        """Get relay statistics"""
        return {
            'local_peer_id': self.local_peer_id,
            'direct_peers': len(self.direct_peers),
            'known_routes': len(self.route_table),
            'messages_relayed': self.messages_relayed,
            'routes_discovered': self.routes_discovered,
            'dead_routes_detected': self.dead_routes_detected,
            'pending_messages': sum(len(msgs) for msgs in self.pending_routes.values())
        }

    def get_routing_table(self) -> dict:
        """Get current routing table (for debugging)"""
        return {
            dest: {
                'next_hops': hops,
                'metrics': [
                    asdict(self.route_metrics.get((self.local_peer_id, hop)))
                    for hop in hops
                    if (self.local_peer_id, hop) in self.route_metrics
                ]
            }
            for dest, hops in self.route_table.items()
        }


# Singleton instance
_mesh_relay = None


def get_mesh_relay(local_peer_id: str = None) -> MeshRelay:
    """Get singleton mesh relay instance"""
    global _mesh_relay

    if _mesh_relay is None:
        if not local_peer_id:
            import hashlib
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            local_peer_id = hashlib.sha256(mac.encode()).hexdigest()[:16]

        _mesh_relay = MeshRelay(local_peer_id)
        logger.info("🔀 Mesh relay ready")

    return _mesh_relay
