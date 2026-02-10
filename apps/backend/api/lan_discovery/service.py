"""
LAN Discovery Service

Main service for LAN discovery and central hub functionality.
Uses mDNS/Bonjour for local network discovery.
"""

import asyncio
import logging
import socket
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional

from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser

from api.lan_discovery.connection import (
    ConnectionState,
    ConnectionHealth,
    ConnectionRetryHandler,
    RetryConfig,
)
from api.lan_discovery.models import LANClient, LANDevice, SERVICE_TYPE
from api.lan_discovery.listener import LANDiscoveryListener

logger = logging.getLogger(__name__)


class LANDiscoveryService:
    """
    Manages LAN discovery and central hub functionality

    Architecture:
    - One instance can be a HUB (broadcasts and accepts connections)
    - Other instances can DISCOVER and CONNECT to the hub
    - All communication is local network only
    """

    def __init__(self, device_name: str = "MedStation", version: str = "1.0.0"):
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

        # Connection state (as client)
        self.connected_hub: Optional[LANDevice] = None
        self.is_connected: bool = False

        # Connection state (as hub)
        self.connected_clients: Dict[str, LANClient] = {}

        # Connection health and retry configuration
        self.connection_health = ConnectionHealth()
        self.retry_config = RetryConfig()

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval: float = 30.0  # seconds
        self._auto_reconnect: bool = True

        # Event callbacks for connection state changes
        self._on_connection_state_change: Optional[Callable[[ConnectionState], None]] = None
        self._on_connection_lost: Optional[Callable[[], None]] = None

        logger.info(f"LAN Discovery Service initialized: {self.device_id}")

    def _generate_device_id(self) -> str:
        """Generate unique device ID based on hostname"""
        try:
            hostname = socket.gethostname()
            return f"{hostname}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        except OSError:
            return f"omnistudio_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _get_local_ip(self) -> str:
        """
        Get local IP address without requiring external connectivity.

        SECURITY: No longer connects to 8.8.8.8 (Google DNS) to find local IP.
        Uses local-only methods with fallback chain.

        Returns:
            Local IPv4 address (non-loopback if possible)
        """
        # Method 1: Try socket.gethostbyname with hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # Check if we got a real IP (not loopback)
            if local_ip and not local_ip.startswith("127."):
                logger.debug(f"Local IP via gethostbyname: {local_ip}")
                return local_ip
        except (socket.gaierror, OSError) as e:
            logger.debug(f"gethostbyname failed: {e}")

        # Method 2: Try to find IP from network interfaces
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get('addr', '')
                        # Skip loopback and link-local
                        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                            logger.debug(f"Local IP via netifaces ({iface}): {ip}")
                            return ip
        except ImportError:
            logger.debug("netifaces not installed, skipping interface enumeration")
        except Exception as e:
            logger.debug(f"netifaces failed: {e}")

        # Method 3: Connect to local multicast address (no external traffic)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Use multicast address - doesn't require actual internet
            s.connect(("224.0.0.1", 1))
            local_ip = s.getsockname()[0]
            s.close()
            if local_ip and not local_ip.startswith("127."):
                logger.debug(f"Local IP via multicast: {local_ip}")
                return local_ip
        except OSError as e:
            logger.debug(f"Multicast method failed: {e}")

        # Fallback: loopback
        logger.warning("Could not determine local IP, using loopback")
        return "127.0.0.1"

    async def start_discovery(self) -> None:
        """Start discovering other MedStation instances on the network"""
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
        self.connected_clients.clear()
        logger.info("Hub stopped")

    async def connect_to_device(
        self,
        device_id: str,
        with_retry: bool = True,
        start_heartbeat: bool = True,
    ) -> Dict[str, Any]:
        """
        Connect to a discovered hub device with optional retry logic.

        Args:
            device_id: ID of the device to connect to
            with_retry: If True, use exponential backoff retry on failure
            start_heartbeat: If True, start heartbeat monitoring after connection

        Returns:
            Connection result with status and hub info

        Raises:
            ValueError: If device not found, not a hub, or connection failed
        """
        if device_id not in self.discovered_devices:
            raise ValueError(f"Device {device_id} not found in discovered devices")

        device = self.discovered_devices[device_id]

        if not device.is_hub:
            raise ValueError(f"Device {device.name} is not a hub")

        self.connection_health.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to hub: {device.name} at {device.ip}:{device.port}")

        last_error: Optional[str] = None

        if with_retry:
            retry_handler = ConnectionRetryHandler(self.retry_config)
            async for delay in retry_handler:
                try:
                    result = await self._attempt_connection(device)
                    retry_handler.mark_success()
                    self.connection_health.record_success()

                    if start_heartbeat:
                        await self._start_heartbeat()

                    return result
                except Exception as e:
                    last_error = str(e)
                    retry_handler.mark_failure(last_error)
                    self.connection_health.record_failure(last_error)

            # All retries exhausted
            self.connection_health.state = ConnectionState.FAILED
            raise ValueError(
                f"Failed to connect after {self.retry_config.max_retries} attempts: {last_error}"
            )
        else:
            # Single attempt without retry
            try:
                result = await self._attempt_connection(device)
                self.connection_health.record_success()

                if start_heartbeat:
                    await self._start_heartbeat()

                return result
            except Exception as e:
                self.connection_health.record_failure(str(e))
                self.connection_health.state = ConnectionState.FAILED
                raise

    async def _attempt_connection(self, device: LANDevice) -> Dict[str, Any]:
        """
        Make a single connection attempt to a hub device.

        Args:
            device: The hub device to connect to

        Returns:
            Connection result

        Raises:
            ValueError: If connection failed
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"http://{device.ip}:{device.port}/api/v1/lan/register-client",
                    json={
                        "client_id": self.device_id,
                        "client_name": self.device_name,
                        "client_ip": self._get_local_ip()
                    }
                )

                if response.status_code == 200:
                    self.connected_hub = device
                    self.is_connected = True
                    logger.info(f"Successfully connected to hub: {device.name}")
                    return {
                        "status": "connected",
                        "hub": device.to_dict()
                    }
                else:
                    error_msg = response.json().get("detail", "Connection refused")
                    logger.error(f"Hub rejected connection: {error_msg}")
                    raise ValueError(f"Hub rejected connection: {error_msg}")

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to hub {device.name}: {e}")
            raise ValueError(f"Could not reach hub at {device.ip}:{device.port}")
        except httpx.TimeoutException as e:
            logger.error(f"Connection timeout to hub {device.name}: {e}")
            raise ValueError(f"Connection timeout to hub at {device.ip}:{device.port}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.error(f"Connection error: {e}")
            raise ValueError(f"Connection error: {e}")

    async def disconnect_from_hub(self) -> Dict[str, Any]:
        """
        Disconnect from the currently connected hub

        Returns:
            Disconnection result
        """
        # Stop heartbeat first
        await self._stop_heartbeat()

        if not self.is_connected or not self.connected_hub:
            self.connection_health.state = ConnectionState.DISCONNECTED
            return {"status": "not_connected"}

        hub = self.connected_hub

        try:
            import httpx

            # Notify hub we're disconnecting
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://{hub.ip}:{hub.port}/api/v1/lan/unregister-client",
                    json={"client_id": self.device_id}
                )
        except Exception as e:
            # Log but don't fail - we're disconnecting anyway
            logger.warning(f"Failed to notify hub of disconnect: {e}")

        self.connected_hub = None
        self.is_connected = False
        self.connection_health.state = ConnectionState.DISCONNECTED
        logger.info(f"Disconnected from hub: {hub.name}")

        return {"status": "disconnected", "hub": hub.to_dict()}

    # ========== Heartbeat and Auto-Reconnect ==========

    async def _start_heartbeat(self) -> None:
        """
        Start the heartbeat monitoring task.

        Heartbeat checks connection health periodically and triggers
        auto-reconnect if connection is lost.
        """
        if self._heartbeat_task and not self._heartbeat_task.done():
            logger.debug("Heartbeat already running")
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat started (interval: {self._heartbeat_interval}s)")

    async def _stop_heartbeat(self) -> None:
        """Stop the heartbeat monitoring task"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """
        Background task that monitors connection health.

        Sends periodic pings to hub and triggers reconnect on failure.
        """
        import httpx

        consecutive_failures = 0
        max_failures_before_reconnect = 3

        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                if not self.is_connected or not self.connected_hub:
                    logger.debug("Not connected, skipping heartbeat")
                    continue

                hub = self.connected_hub

                # Send heartbeat ping
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(
                            f"http://{hub.ip}:{hub.port}/api/v1/lan/status"
                        )

                        if response.status_code == 200:
                            self.connection_health.record_success()
                            consecutive_failures = 0
                            logger.debug(f"Heartbeat OK to {hub.name}")
                        else:
                            raise Exception(f"Status {response.status_code}")

                except Exception as e:
                    consecutive_failures += 1
                    self.connection_health.record_failure(str(e))
                    logger.warning(
                        f"Heartbeat failed ({consecutive_failures}/{max_failures_before_reconnect}): {e}"
                    )

                    # Trigger reconnect after threshold
                    if consecutive_failures >= max_failures_before_reconnect:
                        logger.warning("Connection lost, initiating reconnect...")
                        await self._handle_connection_lost()
                        consecutive_failures = 0

            except asyncio.CancelledError:
                logger.debug("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def _handle_connection_lost(self) -> None:
        """
        Handle lost connection with optional auto-reconnect.

        Called when heartbeat detects connection failure.
        """
        if not self.connected_hub:
            return

        hub_device = self.connected_hub
        hub_id = hub_device.id

        # Mark as disconnected
        self.is_connected = False
        self.connection_health.state = ConnectionState.DISCONNECTED

        # Notify callback if set
        if self._on_connection_lost:
            try:
                self._on_connection_lost()
            except Exception as e:
                logger.error(f"Connection lost callback error: {e}")

        # Attempt auto-reconnect if enabled
        if self._auto_reconnect and hub_id in self.discovered_devices:
            logger.info(f"Attempting auto-reconnect to {hub_device.name}...")
            self.connection_health.record_reconnect()

            try:
                await self.connect_to_device(
                    hub_id,
                    with_retry=True,
                    start_heartbeat=False  # We're already in heartbeat loop
                )
                logger.info(f"Auto-reconnect successful to {hub_device.name}")
            except Exception as e:
                logger.error(f"Auto-reconnect failed: {e}")
                self.connection_health.state = ConnectionState.FAILED

    async def send_heartbeat(self) -> bool:
        """
        Manually send a heartbeat ping to the connected hub.

        Returns:
            True if heartbeat successful, False otherwise
        """
        if not self.is_connected or not self.connected_hub:
            return False

        import httpx
        hub = self.connected_hub

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"http://{hub.ip}:{hub.port}/api/v1/lan/status"
                )
                if response.status_code == 200:
                    self.connection_health.record_success()
                    return True
        except Exception as e:
            self.connection_health.record_failure(str(e))

        return False

    def set_auto_reconnect(self, enabled: bool) -> None:
        """Enable or disable auto-reconnect on connection loss"""
        self._auto_reconnect = enabled
        logger.info(f"Auto-reconnect {'enabled' if enabled else 'disabled'}")

    def set_heartbeat_interval(self, seconds: float) -> None:
        """Set heartbeat interval in seconds (minimum 5 seconds)"""
        self._heartbeat_interval = max(5.0, seconds)
        logger.info(f"Heartbeat interval set to {self._heartbeat_interval}s")

    def on_connection_lost(self, callback: Callable[[], None]) -> None:
        """Register callback for connection lost events"""
        self._on_connection_lost = callback

    def on_connection_state_change(self, callback: Callable[[ConnectionState], None]) -> None:
        """Register callback for connection state changes"""
        self._on_connection_state_change = callback

    def register_client(self, client_id: str, client_name: str, client_ip: str) -> LANClient:
        """
        Register a client connection (called when this instance is a hub)

        Args:
            client_id: Unique ID of the connecting client
            client_name: Display name of the client
            client_ip: IP address of the client

        Returns:
            The registered LANClient
        """
        if not self.is_hub:
            raise ValueError("Cannot register clients - not running as hub")

        client = LANClient(
            id=client_id,
            name=client_name,
            ip=client_ip,
            connected_at=datetime.now().isoformat()
        )

        self.connected_clients[client_id] = client
        logger.info(f"Client registered: {client_name} ({client_ip})")

        return client

    def unregister_client(self, client_id: str) -> bool:
        """
        Unregister a client (called when client disconnects)

        Args:
            client_id: ID of the client to unregister

        Returns:
            True if client was found and removed
        """
        if client_id in self.connected_clients:
            client = self.connected_clients.pop(client_id)
            logger.info(f"Client unregistered: {client.name}")
            return True
        return False

    def get_connected_clients(self) -> List[Dict]:
        """Get list of connected clients (when running as hub)"""
        return [client.to_dict() for client in self.connected_clients.values()]

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
        """Get current status including connection health"""
        status = {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "is_hub": self.is_hub,
            "port": self.port if self.is_hub else None,
            "local_ip": self._get_local_ip(),
            "discovered_devices_count": len(self.discovered_devices),
            "is_connected": self.is_connected,
            # Connection resilience info
            "connection_health": self.connection_health.to_dict(),
            "auto_reconnect_enabled": self._auto_reconnect,
            "heartbeat_interval": self._heartbeat_interval,
            "heartbeat_active": self._heartbeat_task is not None and not self._heartbeat_task.done(),
        }

        # Hub-specific info
        if self.is_hub:
            status["connected_clients_count"] = len(self.connected_clients)
            status["connected_clients"] = self.get_connected_clients()

        # Client-specific info
        if self.is_connected and self.connected_hub:
            status["connected_hub"] = self.connected_hub.to_dict()

        return status


# Global instance
lan_service = LANDiscoveryService()


def get_lan_service() -> LANDiscoveryService:
    """Get the global LAN discovery service instance"""
    return lan_service


def _reset_lan_service() -> None:
    """Reset the global instance - for testing only"""
    global lan_service
    lan_service = LANDiscoveryService()
