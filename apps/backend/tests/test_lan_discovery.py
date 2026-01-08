"""
Tests for LAN Discovery Service

Tests the mDNS-based local network discovery and hub connection functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from api.lan_discovery import (
    LANDiscoveryService,
    LANDevice,
    LANClient,
    LANDiscoveryListener,
    SERVICE_TYPE,
)


class TestLANDevice:
    """Tests for LANDevice dataclass"""

    def test_lan_device_creation(self):
        """Test creating a LANDevice"""
        device = LANDevice(
            id="test-device-001",
            name="TestDevice",
            ip="192.168.1.100",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at="2025-01-01T00:00:00"
        )

        assert device.id == "test-device-001"
        assert device.name == "TestDevice"
        assert device.ip == "192.168.1.100"
        assert device.port == 8765
        assert device.is_hub is True
        assert device.version == "1.0.0"

    def test_lan_device_to_dict(self):
        """Test LANDevice serialization"""
        device = LANDevice(
            id="test-device",
            name="TestDevice",
            ip="192.168.1.100",
            port=8765,
            is_hub=False,
            version="2.0.0",
            discovered_at="2025-01-01T00:00:00"
        )

        result = device.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test-device"
        assert result["name"] == "TestDevice"
        assert result["ip"] == "192.168.1.100"
        assert result["port"] == 8765
        assert result["is_hub"] is False


class TestLANClient:
    """Tests for LANClient dataclass"""

    def test_lan_client_creation(self):
        """Test creating a LANClient"""
        client = LANClient(
            id="client-001",
            name="ClientDevice",
            ip="192.168.1.101",
            connected_at="2025-01-01T00:00:00"
        )

        assert client.id == "client-001"
        assert client.name == "ClientDevice"
        assert client.ip == "192.168.1.101"

    def test_lan_client_to_dict(self):
        """Test LANClient serialization"""
        client = LANClient(
            id="client-001",
            name="ClientDevice",
            ip="192.168.1.101",
            connected_at="2025-01-01T00:00:00"
        )

        result = client.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "client-001"
        assert result["name"] == "ClientDevice"


class TestLANDiscoveryService:
    """Tests for LANDiscoveryService"""

    def test_service_initialization(self):
        """Test service initializes with correct defaults"""
        service = LANDiscoveryService(device_name="TestDevice", version="1.0.0")

        assert service.device_name == "TestDevice"
        assert service.version == "1.0.0"
        assert service.is_hub is False
        assert service.port == 8765
        assert service.discovered_devices == {}
        assert service.connected_clients == {}
        assert service.connected_hub is None
        assert service.is_connected is False

    def test_generate_device_id(self):
        """Test device ID generation includes hostname"""
        service = LANDiscoveryService()
        device_id = service.device_id

        assert device_id is not None
        assert len(device_id) > 0
        assert "_" in device_id  # Format: hostname_timestamp

    def test_get_local_ip(self):
        """Test local IP retrieval"""
        service = LANDiscoveryService()
        ip = service._get_local_ip()

        assert ip is not None
        # Should be either a valid IP or fallback
        assert ip == "127.0.0.1" or "." in ip

    def test_get_discovered_devices_empty(self):
        """Test getting discovered devices when none exist"""
        service = LANDiscoveryService()
        devices = service.get_discovered_devices()

        assert devices == []

    def test_get_discovered_devices_with_devices(self):
        """Test getting discovered devices"""
        service = LANDiscoveryService()
        device = LANDevice(
            id="test-device",
            name="TestDevice",
            ip="192.168.1.100",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now().isoformat()
        )
        service.discovered_devices["test-device"] = device

        devices = service.get_discovered_devices()

        assert len(devices) == 1
        assert devices[0]["id"] == "test-device"

    def test_register_client_when_hub(self):
        """Test registering a client when running as hub"""
        service = LANDiscoveryService()
        service.is_hub = True

        client = service.register_client(
            client_id="client-001",
            client_name="ClientDevice",
            client_ip="192.168.1.101"
        )

        assert client.id == "client-001"
        assert client.name == "ClientDevice"
        assert "client-001" in service.connected_clients

    def test_register_client_when_not_hub(self):
        """Test registering a client fails when not running as hub"""
        service = LANDiscoveryService()
        service.is_hub = False

        with pytest.raises(ValueError, match="not running as hub"):
            service.register_client(
                client_id="client-001",
                client_name="ClientDevice",
                client_ip="192.168.1.101"
            )

    def test_unregister_client_exists(self):
        """Test unregistering an existing client"""
        service = LANDiscoveryService()
        service.is_hub = True
        service.register_client("client-001", "ClientDevice", "192.168.1.101")

        result = service.unregister_client("client-001")

        assert result is True
        assert "client-001" not in service.connected_clients

    def test_unregister_client_not_exists(self):
        """Test unregistering a non-existent client"""
        service = LANDiscoveryService()

        result = service.unregister_client("non-existent")

        assert result is False

    def test_get_connected_clients(self):
        """Test getting connected clients"""
        service = LANDiscoveryService()
        service.is_hub = True
        service.register_client("client-001", "Client1", "192.168.1.101")
        service.register_client("client-002", "Client2", "192.168.1.102")

        clients = service.get_connected_clients()

        assert len(clients) == 2
        client_ids = [c["id"] for c in clients]
        assert "client-001" in client_ids
        assert "client-002" in client_ids

    def test_get_status_basic(self):
        """Test getting basic service status"""
        service = LANDiscoveryService(device_name="TestHub")

        status = service.get_status()

        assert status["device_name"] == "TestHub"
        assert status["is_hub"] is False
        assert status["is_connected"] is False
        assert status["discovered_devices_count"] == 0

    def test_get_status_as_hub(self):
        """Test getting status when running as hub"""
        service = LANDiscoveryService(device_name="TestHub")
        service.is_hub = True
        service.port = 8765
        service.register_client("client-001", "Client1", "192.168.1.101")

        status = service.get_status()

        assert status["is_hub"] is True
        assert status["port"] == 8765
        assert status["connected_clients_count"] == 1
        assert "connected_clients" in status

    def test_get_status_as_connected_client(self):
        """Test getting status when connected to a hub"""
        service = LANDiscoveryService()
        service.is_connected = True
        service.connected_hub = LANDevice(
            id="hub-001",
            name="HubDevice",
            ip="192.168.1.1",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now().isoformat()
        )

        status = service.get_status()

        assert status["is_connected"] is True
        assert "connected_hub" in status
        assert status["connected_hub"]["name"] == "HubDevice"


class TestLANDiscoveryServiceAsync:
    """Async tests for LANDiscoveryService"""

    @pytest.mark.asyncio
    async def test_start_discovery(self):
        """Test starting discovery"""
        service = LANDiscoveryService()

        with patch("api.lan_discovery.service.AsyncZeroconf") as mock_zc:
            mock_instance = MagicMock()
            mock_zc.return_value = mock_instance

            with patch("api.lan_discovery.service.AsyncServiceBrowser"):
                await service.start_discovery()

            assert service.zeroconf is not None

    @pytest.mark.asyncio
    async def test_stop_discovery(self):
        """Test stopping discovery"""
        service = LANDiscoveryService()

        # Mock the zeroconf and browser
        mock_browser = MagicMock()
        mock_browser.async_cancel = AsyncMock()
        service.service_browser = mock_browser

        mock_zc = MagicMock()
        mock_zc.async_close = AsyncMock()
        service.zeroconf = mock_zc

        await service.stop_discovery()

        assert service.service_browser is None
        assert service.zeroconf is None
        mock_browser.async_cancel.assert_called_once()
        mock_zc.async_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_hub(self):
        """Test starting as hub"""
        service = LANDiscoveryService(device_name="TestHub")

        with patch("api.lan_discovery.service.AsyncZeroconf") as mock_zc:
            mock_instance = MagicMock()
            mock_instance.async_register_service = AsyncMock()
            mock_zc.return_value = mock_instance

            await service.start_hub(port=9000)

            assert service.is_hub is True
            assert service.port == 9000
            mock_instance.async_register_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_hub(self):
        """Test stopping hub"""
        service = LANDiscoveryService()
        service.is_hub = True
        service.register_client("client-001", "Client1", "192.168.1.101")

        mock_zc = MagicMock()
        mock_zc.async_unregister_service = AsyncMock()
        service.zeroconf = mock_zc
        service.service_info = MagicMock()

        await service.stop_hub()

        assert service.is_hub is False
        assert len(service.connected_clients) == 0
        mock_zc.async_unregister_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_to_device_not_found(self):
        """Test connecting to a device that doesn't exist"""
        service = LANDiscoveryService()

        with pytest.raises(ValueError, match="not found"):
            await service.connect_to_device("non-existent-device")

    @pytest.mark.asyncio
    async def test_connect_to_device_not_hub(self):
        """Test connecting to a device that isn't a hub"""
        service = LANDiscoveryService()
        device = LANDevice(
            id="device-001",
            name="NotAHub",
            ip="192.168.1.100",
            port=8765,
            is_hub=False,  # Not a hub
            version="1.0.0",
            discovered_at=datetime.now().isoformat()
        )
        service.discovered_devices["device-001"] = device

        with pytest.raises(ValueError, match="not a hub"):
            await service.connect_to_device("device-001")

    @pytest.mark.asyncio
    async def test_connect_to_device_success(self):
        """Test successful connection to a hub"""
        service = LANDiscoveryService()
        device = LANDevice(
            id="hub-001",
            name="HubDevice",
            ip="192.168.1.1",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now().isoformat()
        )
        service.discovered_devices["hub-001"] = device

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}

            mock_context = MagicMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_context

            result = await service.connect_to_device("hub-001")

            assert result["status"] == "connected"
            assert service.is_connected is True
            assert service.connected_hub == device

    @pytest.mark.asyncio
    async def test_disconnect_from_hub_not_connected(self):
        """Test disconnecting when not connected"""
        service = LANDiscoveryService()
        service.is_connected = False

        result = await service.disconnect_from_hub()

        assert result["status"] == "not_connected"

    @pytest.mark.asyncio
    async def test_disconnect_from_hub_success(self):
        """Test successful disconnection"""
        service = LANDiscoveryService()
        service.is_connected = True
        service.connected_hub = LANDevice(
            id="hub-001",
            name="HubDevice",
            ip="192.168.1.1",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now().isoformat()
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_context = MagicMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_context

            result = await service.disconnect_from_hub()

            assert result["status"] == "disconnected"
            assert service.is_connected is False
            assert service.connected_hub is None


class TestLANDiscoveryListener:
    """Tests for LANDiscoveryListener"""

    def test_listener_initialization(self):
        """Test listener initializes with callbacks"""
        on_discovered = MagicMock()
        on_removed = MagicMock()

        listener = LANDiscoveryListener(
            on_device_discovered=on_discovered,
            on_device_removed=on_removed
        )

        assert listener.on_device_discovered == on_discovered
        assert listener.on_device_removed == on_removed

    def test_service_type_constant(self):
        """Test the service type constant is correct"""
        assert SERVICE_TYPE == "_omnistudio._tcp.local."
