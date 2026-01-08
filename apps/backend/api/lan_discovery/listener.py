"""
LAN Discovery Listener

mDNS/Zeroconf service listener for discovering ElohimOS instances.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from zeroconf import ServiceInfo, Zeroconf, ServiceListener

from api.lan_discovery.models import LANDevice

logger = logging.getLogger(__name__)


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
