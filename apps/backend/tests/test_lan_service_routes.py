"""
Tests for LAN Service API Routes

Tests the FastAPI endpoints for LAN discovery functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

# We need to mock auth before importing the router
@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests"""
    with patch("api.lan_service.get_current_user") as mock:
        mock.return_value = {"user_id": "test_user"}
        yield mock


@pytest.fixture
def mock_lan_service():
    """Mock the lan_service singleton"""
    with patch("api.lan_service.lan_service") as mock:
        mock.device_id = "test_device_001"
        mock.device_name = "TestDevice"
        mock.is_hub = False
        mock.is_connected = False
        mock.discovered_devices = {}
        mock.connected_clients = {}
        mock._get_local_ip.return_value = "192.168.1.100"
        yield mock


class TestStartDiscoveryEndpoint:
    """Tests for POST /api/v1/lan/discovery/start"""

    @pytest.mark.asyncio
    async def test_start_discovery_success(self, mock_lan_service):
        """Test starting discovery successfully"""
        mock_lan_service.start_discovery = AsyncMock()
        mock_lan_service.get_status.return_value = {
            "device_id": "test_device",
            "is_hub": False,
            "discovered_devices_count": 0
        }

        from api.lan_discovery.router import start_discovery

        class MockRequest:
            pass

        result = await start_discovery(MockRequest())

        assert result["status"] == "success"
        assert "service_info" in result
        mock_lan_service.start_discovery.assert_called_once()


class TestStopDiscoveryEndpoint:
    """Tests for POST /api/v1/lan/discovery/stop"""

    @pytest.mark.asyncio
    async def test_stop_discovery_success(self, mock_lan_service):
        """Test stopping discovery successfully"""
        mock_lan_service.stop_discovery = AsyncMock()

        from api.lan_discovery.router import stop_discovery

        class MockRequest:
            pass

        result = await stop_discovery(MockRequest())

        assert result["status"] == "success"
        mock_lan_service.stop_discovery.assert_called_once()


class TestGetDevicesEndpoint:
    """Tests for GET /api/v1/lan/devices"""

    @pytest.mark.asyncio
    async def test_get_devices_empty(self, mock_lan_service):
        """Test getting devices when none discovered"""
        mock_lan_service.get_discovered_devices.return_value = []

        from api.lan_discovery.router import get_discovered_devices

        result = await get_discovered_devices()

        assert result["status"] == "success"
        assert result["devices"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_devices_with_results(self, mock_lan_service):
        """Test getting devices with discovered devices"""
        mock_lan_service.get_discovered_devices.return_value = [
            {"id": "device_001", "name": "Device 1", "ip": "192.168.1.101"},
            {"id": "device_002", "name": "Device 2", "ip": "192.168.1.102"}
        ]

        from api.lan_discovery.router import get_discovered_devices

        result = await get_discovered_devices()

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["devices"]) == 2


class TestStartHubEndpoint:
    """Tests for POST /api/v1/lan/hub/start"""

    @pytest.mark.asyncio
    async def test_start_hub_success(self, mock_lan_service):
        """Test starting hub successfully"""
        mock_lan_service.start_hub = AsyncMock()

        from api.lan_discovery.router import start_hub
        from api.lan_discovery.types import StartHubRequest

        class MockRequest:
            pass

        body = StartHubRequest(port=8765, device_name="TestHub")
        result = await start_hub(MockRequest(), body)

        assert result["status"] == "success"
        assert "hub_info" in result


class TestStopHubEndpoint:
    """Tests for POST /api/v1/lan/hub/stop"""

    @pytest.mark.asyncio
    async def test_stop_hub_success(self, mock_lan_service):
        """Test stopping hub successfully"""
        mock_lan_service.stop_hub = AsyncMock()

        from api.lan_discovery.router import stop_hub

        class MockRequest:
            pass

        result = await stop_hub(MockRequest())

        assert result["status"] == "success"
        mock_lan_service.stop_hub.assert_called_once()


class TestConnectEndpoint:
    """Tests for POST /api/v1/lan/connect"""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_lan_service):
        """Test connecting to device successfully"""
        mock_lan_service.connect_to_device = AsyncMock(return_value={
            "status": "connected",
            "hub": {"name": "HubDevice", "ip": "192.168.1.1"}
        })

        from api.lan_discovery.router import connect_to_device
        from api.lan_discovery.types import JoinDeviceRequest

        class MockRequest:
            pass

        body = JoinDeviceRequest(device_id="hub_001")
        result = await connect_to_device(MockRequest(), body)

        # The endpoint merges the result with status: "success"
        assert "success" in str(result["status"]) or result["status"] == "connected"
        assert "HubDevice" in result["message"]


class TestDisconnectEndpoint:
    """Tests for POST /api/v1/lan/disconnect"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self, mock_lan_service):
        """Test disconnecting from hub successfully"""
        mock_lan_service.disconnect_from_hub = AsyncMock(return_value={
            "status": "disconnected",
            "hub": {"name": "HubDevice"}
        })

        from api.lan_discovery.router import disconnect_from_hub

        class MockRequest:
            pass

        result = await disconnect_from_hub(MockRequest())

        # The endpoint returns success or disconnected status
        assert "success" in str(result["status"]) or result["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, mock_lan_service):
        """Test disconnecting when not connected"""
        mock_lan_service.disconnect_from_hub = AsyncMock(return_value={
            "status": "not_connected"
        })

        from api.lan_discovery.router import disconnect_from_hub

        class MockRequest:
            pass

        result = await disconnect_from_hub(MockRequest())

        assert result["status"] == "success"
        assert "Not connected" in result["message"]


class TestStatusEndpoint:
    """Tests for GET /api/v1/lan/status"""

    @pytest.mark.asyncio
    async def test_get_status(self, mock_lan_service):
        """Test getting LAN status"""
        mock_lan_service.get_status.return_value = {
            "device_id": "test_device",
            "is_hub": False,
            "is_connected": False,
            "discovered_devices_count": 0
        }
        mock_lan_service.get_discovered_devices.return_value = []

        from api.lan_discovery.router import get_lan_status

        result = await get_lan_status()

        assert result["status"] == "success"
        assert "service" in result
        assert "devices" in result


class TestRegisterClientEndpoint:
    """Tests for POST /api/v1/lan/register-client"""

    @pytest.mark.asyncio
    async def test_register_client_success(self, mock_lan_service):
        """Test registering a client successfully"""
        from api.lan_discovery import LANClient

        mock_client = LANClient(
            id="client_001",
            name="ClientDevice",
            ip="192.168.1.101",
            connected_at=datetime.now().isoformat()
        )
        mock_lan_service.register_client.return_value = mock_client

        from api.lan_discovery.router import register_client
        from api.lan_discovery.types import RegisterClientRequest

        class MockRequest:
            pass

        body = RegisterClientRequest(
            client_id="client_001",
            client_name="ClientDevice",
            client_ip="192.168.1.101"
        )
        result = await register_client(MockRequest(), body)

        assert result["status"] == "success"
        assert "client" in result

    @pytest.mark.asyncio
    async def test_register_client_not_hub(self, mock_lan_service):
        """Test registering client when not running as hub"""
        mock_lan_service.register_client.side_effect = ValueError("not running as hub")

        from api.lan_discovery.router import register_client
        from api.lan_discovery.types import RegisterClientRequest
        from fastapi import HTTPException

        class MockRequest:
            pass

        body = RegisterClientRequest(
            client_id="client_001",
            client_name="ClientDevice",
            client_ip="192.168.1.101"
        )

        with pytest.raises(HTTPException) as exc_info:
            await register_client(MockRequest(), body)

        assert exc_info.value.status_code == 400


class TestUnregisterClientEndpoint:
    """Tests for POST /api/v1/lan/unregister-client"""

    @pytest.mark.asyncio
    async def test_unregister_client_success(self, mock_lan_service):
        """Test unregistering a client"""
        mock_lan_service.unregister_client.return_value = True

        from api.lan_discovery.router import unregister_client
        from api.lan_discovery.types import UnregisterClientRequest

        class MockRequest:
            pass

        body = UnregisterClientRequest(client_id="client_001")
        result = await unregister_client(MockRequest(), body)

        assert result["status"] == "success"
        assert result["message"] == "Client unregistered"

    @pytest.mark.asyncio
    async def test_unregister_client_not_found(self, mock_lan_service):
        """Test unregistering a client that wasn't registered"""
        mock_lan_service.unregister_client.return_value = False

        from api.lan_discovery.router import unregister_client
        from api.lan_discovery.types import UnregisterClientRequest

        class MockRequest:
            pass

        body = UnregisterClientRequest(client_id="nonexistent")
        result = await unregister_client(MockRequest(), body)

        assert result["status"] == "success"
        assert "was not registered" in result["message"]


class TestGetClientsEndpoint:
    """Tests for GET /api/v1/lan/clients"""

    @pytest.mark.asyncio
    async def test_get_clients_as_hub(self, mock_lan_service):
        """Test getting clients when running as hub"""
        mock_lan_service.is_hub = True
        mock_lan_service.get_connected_clients.return_value = [
            {"id": "client_001", "name": "Client 1"},
            {"id": "client_002", "name": "Client 2"}
        ]

        from api.lan_discovery.router import get_connected_clients

        result = await get_connected_clients()

        assert result["status"] == "success"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_get_clients_not_hub(self, mock_lan_service):
        """Test getting clients when not running as hub"""
        mock_lan_service.is_hub = False

        from api.lan_discovery.router import get_connected_clients
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_connected_clients()

        assert exc_info.value.status_code == 400
        assert "Not running as hub" in str(exc_info.value.detail)
