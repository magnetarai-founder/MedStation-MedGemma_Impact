"""
LAN Discovery Service

Enables local network discovery of OmniStudio instances using mDNS/Bonjour.
Central Hub Model: One laptop acts as hub, others connect to it.

Built for the persecuted Church - no cloud, no central servers.
"And they overcame him by the blood of the Lamb, and by the word of their testimony" - Revelation 12:11
"""

import socket
import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser

logger = logging.getLogger(__name__)

# Service type for mDNS discovery
SERVICE_TYPE = "_omnistudio._tcp.local."

@dataclass
class LANDevice:
    """Represents a discovered OmniStudio instance on the network"""
    id: str
    name: str
    ip: str
    port: int
    is_hub: bool
    version: str
    discovered_at: str

    def to_dict(self):
        return asdict(self)


class LANDiscoveryListener(ServiceListener):
    """Listener for mDNS service discovery"""

    def __init__(self, on_device_discovered=None, on_device_removed=None):
        self.on_device_discovered = on_device_discovered
        self.on_device_removed = on_device_removed

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a new service is discovered"""
        logger.info(f"Service added: {name}")
        info = zeroconf.get_service_info(service_type, name)

        if info and self.on_device_discovered:
            device = self._parse_service_info(info)
            if device:
                asyncio.create_task(self.on_device_discovered(device))

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is removed"""
        logger.info(f"Service removed: {name}")
        if self.on_device_removed:
            asyncio.create_task(self.on_device_removed(name))

    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is updated"""
        logger.debug(f"Service updated: {name}")

    def _parse_service_info(self, info: ServiceInfo) -> Optional[LANDevice]:
        """Parse ServiceInfo into LANDevice"""
        try:
            properties = {}
            if info.properties:
                for key, value in info.properties.items():
                    properties[key.decode('utf-8')] = value.decode('utf-8')

            # Get IP address
            addresses = info.parsed_addresses()
            ip = addresses[0] if addresses else None

            if not ip:
                return None

            device = LANDevice(
                id=properties.get('id', info.name),
                name=properties.get('name', info.name),
                ip=ip,
                port=info.port,
                is_hub=properties.get('is_hub', 'false').lower() == 'true',
                version=properties.get('version', '1.0.0'),
                discovered_at=datetime.now().isoformat()
            )

            return device

        except Exception as e:
            logger.error(f"Error parsing service info: {e}")
            return None


class LANDiscoveryService:
    """
    Manages LAN discovery and central hub functionality

    Architecture:
    - One instance can be a HUB (broadcasts and accepts connections)
    - Other instances can DISCOVER and CONNECT to the hub
    - All communication is local network only
    """

    def __init__(self, device_name: str = "OmniStudio", version: str = "1.0.0"):
        self.device_name = device_name
        self.version = version
        self.device_id = self._generate_device_id()
        self.is_hub = False
        self.port = 8765  # Default port for hub

        # Discovery state
        self.zeroconf: Optional[AsyncZeroconf] = None
        self.service_browser: Optional[AsyncServiceBrowser] = None
        self.service_info: Optional[ServiceInfo] = None
        self.discovered_devices: Dict[str, LANDevice] = {}
        self.connected_clients: Set[str] = set()

        logger.info(f"LAN Discovery Service initialized: {self.device_id}")

    def _generate_device_id(self) -> str:
        """Generate unique device ID based on hostname"""
        try:
            hostname = socket.gethostname()
            return f"{hostname}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        except:
            return f"omnistudio_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create a socket to find the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    async def start_discovery(self) -> None:
        """Start discovering other OmniStudio instances on the network"""
        logger.info("Starting LAN discovery...")

        self.zeroconf = AsyncZeroconf()

        listener = LANDiscoveryListener(
            on_device_discovered=self._on_device_discovered,
            on_device_removed=self._on_device_removed
        )

        self.service_browser = AsyncServiceBrowser(
            self.zeroconf.zeroconf,
            SERVICE_TYPE,
            listener
        )

        logger.info("LAN discovery started")

    async def stop_discovery(self) -> None:
        """Stop discovery"""
        logger.info("Stopping LAN discovery...")

        if self.service_browser:
            await self.service_browser.async_cancel()
            self.service_browser = None

        if self.zeroconf:
            await self.zeroconf.async_close()
            self.zeroconf = None

        logger.info("LAN discovery stopped")

    async def start_hub(self, port: int = 8765) -> None:
        """
        Start broadcasting as a hub (central node)
        Others can discover and connect to this instance
        """
        logger.info(f"Starting as LAN hub on port {port}...")

        self.is_hub = True
        self.port = port

        # Create service info for broadcasting
        local_ip = self._get_local_ip()

        properties = {
            b'id': self.device_id.encode('utf-8'),
            b'name': self.device_name.encode('utf-8'),
            b'version': self.version.encode('utf-8'),
            b'is_hub': b'true'
        }

        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            f"{self.device_name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties=properties,
            server=f"{socket.gethostname()}.local."
        )

        # Start broadcasting
        if not self.zeroconf:
            self.zeroconf = AsyncZeroconf()

        await self.zeroconf.async_register_service(self.service_info)

        logger.info(f"Hub started: {self.device_name} at {local_ip}:{port}")

    async def stop_hub(self) -> None:
        """Stop broadcasting as hub"""
        logger.info("Stopping hub...")

        if self.service_info and self.zeroconf:
            await self.zeroconf.async_unregister_service(self.service_info)
            self.service_info = None

        self.is_hub = False
        logger.info("Hub stopped")

    async def _on_device_discovered(self, device: LANDevice) -> None:
        """Called when a new device is discovered"""
        logger.info(f"Device discovered: {device.name} at {device.ip}")
        self.discovered_devices[device.id] = device

    async def _on_device_removed(self, service_name: str) -> None:
        """Called when a device is removed"""
        logger.info(f"Device removed: {service_name}")
        # Remove from discovered devices
        self.discovered_devices = {
            k: v for k, v in self.discovered_devices.items()
            if v.name != service_name
        }

    def get_discovered_devices(self) -> List[Dict]:
        """Get list of discovered devices"""
        return [device.to_dict() for device in self.discovered_devices.values()]

    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "is_hub": self.is_hub,
            "port": self.port if self.is_hub else None,
            "local_ip": self._get_local_ip(),
            "discovered_devices": len(self.discovered_devices),
            "connected_clients": len(self.connected_clients)
        }


# Global instance
lan_service = LANDiscoveryService()
