#!/usr/bin/env python3
"""
Offline Mesh Discovery for ElohimOS
Local network peer discovery using mDNS (zero-configuration networking)
Perfect for missionary teams working without internet
"""

import asyncio
import socket
import json
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import zeroconf for mDNS discovery
try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("zeroconf not installed - peer discovery will be limited")


@dataclass
class LocalPeer:
    """A discovered peer on the local network"""
    peer_id: str
    display_name: str
    device_name: str
    ip_address: str
    port: int
    capabilities: List[str]  # ['chat', 'file_share', 'data_sync']
    last_seen: str
    status: str = "online"


class OfflineMeshDiscovery:
    """
    Offline peer discovery using mDNS (Bonjour/Avahi)

    Discovers other ElohimOS instances on the local network
    Works without internet - only requires local WiFi/LAN
    """

    SERVICE_TYPE = "_omnistudio._tcp.local."

    def __init__(self,
                 display_name: str,
                 device_name: str,
                 port: int = 8765,
                 capabilities: Optional[List[str]] = None):

        self.display_name = display_name
        self.device_name = device_name
        self.port = port
        self.capabilities = capabilities or ['chat', 'file_share', 'data_sync']

        # Discovered peers
        self.peers: Dict[str, LocalPeer] = {}
        self.peer_callbacks: List[Callable] = []

        # Zeroconf instance
        self.zeroconf: Optional[Zeroconf] = None
        self.service_browser: Optional[ServiceBrowser] = None
        self.service_info: Optional[ServiceInfo] = None

        # Running state
        self.is_running = False

        # Generate unique peer ID from hostname + MAC
        self.peer_id = self._generate_peer_id()

        logger.info(f"🔍 Offline mesh discovery initialized for {display_name}")

    def _generate_peer_id(self) -> str:
        """Generate unique peer ID from device info"""
        import hashlib
        import uuid

        # Use MAC address for stable ID across restarts
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                       for elements in range(0, 2*6, 2)][::-1])

        peer_id = hashlib.sha256(mac.encode()).hexdigest()[:16]
        return peer_id

    async def start(self):
        """Start mDNS service discovery and announcement"""
        if not ZEROCONF_AVAILABLE:
            logger.error("❌ zeroconf not available - cannot start discovery")
            logger.error("Install with: pip install zeroconf")
            return False

        try:
            # Start zeroconf
            self.zeroconf = Zeroconf()

            # Register our service
            await self._register_service()

            # Start browsing for peers
            self.service_browser = ServiceBrowser(
                self.zeroconf,
                self.SERVICE_TYPE,
                handlers=[self._on_service_state_change]
            )

            self.is_running = True
            logger.info(f"✅ Mesh discovery started on port {self.port}")
            logger.info(f"   Peer ID: {self.peer_id}")
            logger.info(f"   Display name: {self.display_name}")
            logger.info(f"   Device: {self.device_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to start mesh discovery: {e}")
            return False

    async def _register_service(self):
        """Register this device as an available peer"""
        if not self.zeroconf:
            return

        # Get local IP
        local_ip = self._get_local_ip()

        # Create service info
        service_name = f"{self.display_name} ({self.device_name}).{self.SERVICE_TYPE}"

        # Service properties (additional metadata)
        properties = {
            'peer_id': self.peer_id,
            'display_name': self.display_name,
            'device_name': self.device_name,
            'capabilities': ','.join(self.capabilities),
            'version': '1.0.0'
        }

        # Convert properties to bytes
        properties_bytes = {
            k: v.encode('utf-8') if isinstance(v, str) else v
            for k, v in properties.items()
        }

        self.service_info = ServiceInfo(
            self.SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties=properties_bytes,
            server=f"{self.device_name}.local."
        )

        # Register
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.zeroconf.register_service,
            self.service_info
        )

        logger.info(f"📡 Broadcasting presence: {service_name}")

    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Doesn't actually connect
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange):
        """Handle service discovery events"""
        try:
            if state_change is ServiceStateChange.Added:
                # New peer discovered
                asyncio.create_task(self._handle_peer_added(zeroconf, service_type, name))

            elif state_change is ServiceStateChange.Removed:
                # Peer left
                self._handle_peer_removed(name)

        except Exception as e:
            logger.error(f"Error handling service change: {e}")

    async def _handle_peer_added(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Handle newly discovered peer"""
        try:
            # Get service info
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                zeroconf.get_service_info,
                service_type,
                name
            )

            if not info:
                return

            # Extract properties
            properties = {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in info.properties.items()
            }

            peer_id = properties.get('peer_id', 'unknown')

            # Don't add ourselves
            if peer_id == self.peer_id:
                return

            # Get IP address
            ip_address = socket.inet_ntoa(info.addresses[0])

            # Create peer object
            peer = LocalPeer(
                peer_id=peer_id,
                display_name=properties.get('display_name', 'Unknown'),
                device_name=properties.get('device_name', 'Unknown'),
                ip_address=ip_address,
                port=info.port,
                capabilities=properties.get('capabilities', '').split(','),
                last_seen=datetime.utcnow().isoformat(),
                status='online'
            )

            # Add to peers
            self.peers[peer_id] = peer

            logger.info(f"✨ New peer discovered: {peer.display_name} ({peer.device_name}) at {peer.ip_address}:{peer.port}")

            # Notify callbacks
            for callback in self.peer_callbacks:
                try:
                    await callback('peer_joined', peer)
                except Exception as e:
                    logger.error(f"Peer callback error: {e}")

        except Exception as e:
            logger.error(f"Error handling peer added: {e}")

    def _handle_peer_removed(self, name: str):
        """Handle peer leaving"""
        # Find and remove peer
        for peer_id, peer in list(self.peers.items()):
            if peer.display_name in name or peer.device_name in name:
                peer.status = 'offline'
                logger.info(f"👋 Peer left: {peer.display_name}")

                # Notify callbacks
                for callback in self.peer_callbacks:
                    try:
                        asyncio.create_task(callback('peer_left', peer))
                    except Exception as e:
                        logger.error(f"Peer callback error: {e}")

                # Remove after delay (in case they come back)
                asyncio.create_task(self._remove_peer_delayed(peer_id))

    async def _remove_peer_delayed(self, peer_id: str, delay: int = 30):
        """Remove peer after delay"""
        await asyncio.sleep(delay)
        if peer_id in self.peers and self.peers[peer_id].status == 'offline':
            del self.peers[peer_id]

    def get_peers(self) -> List[LocalPeer]:
        """Get list of discovered peers"""
        return list(self.peers.values())

    def get_peer(self, peer_id: str) -> Optional[LocalPeer]:
        """Get specific peer by ID"""
        return self.peers.get(peer_id)

    def get_peer_by_id(self, peer_id: str) -> Optional[LocalPeer]:
        """Alias for get_peer - get specific peer by ID"""
        return self.get_peer(peer_id)

    def on_peer_event(self, callback: Callable):
        """Register callback for peer events"""
        self.peer_callbacks.append(callback)

    async def stop(self):
        """Stop discovery service"""
        if not self.is_running:
            return

        try:
            # Unregister service
            if self.zeroconf and self.service_info:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.zeroconf.unregister_service,
                    self.service_info
                )

            # Close zeroconf
            if self.zeroconf:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.zeroconf.close
                )

            self.is_running = False
            logger.info("🛑 Mesh discovery stopped")

        except Exception as e:
            logger.error(f"Error stopping discovery: {e}")

    def get_stats(self) -> Dict:
        """Get discovery statistics"""
        return {
            'is_running': self.is_running,
            'peer_id': self.peer_id,
            'display_name': self.display_name,
            'device_name': self.device_name,
            'port': self.port,
            'capabilities': self.capabilities,
            'discovered_peers': len(self.peers),
            'peers': [asdict(p) for p in self.peers.values()]
        }


# Singleton instance
_mesh_discovery = None


def get_mesh_discovery(display_name: str = None, device_name: str = None) -> OfflineMeshDiscovery:
    """Get singleton mesh discovery instance"""
    global _mesh_discovery

    if _mesh_discovery is None:
        if not display_name or not device_name:
            import socket
            device_name = socket.gethostname()
            display_name = f"ElohimOS ({device_name})"

        _mesh_discovery = OfflineMeshDiscovery(
            display_name=display_name,
            device_name=device_name
        )
        logger.info("🔍 Offline mesh discovery ready")

    return _mesh_discovery
