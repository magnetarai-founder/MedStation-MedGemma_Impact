"""
Tests for LAN Discovery Connection Logic

Tests cover:
- Connection retry with exponential backoff
- Connection health tracking
- Heartbeat monitoring
- Auto-reconnect on connection loss
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.lan_discovery import (
    ConnectionState,
    ConnectionHealth,
    ConnectionRetryHandler,
    RetryConfig,
    LANDiscoveryService,
    LANDevice,
)


# ===== ConnectionHealth Tests =====

class TestConnectionHealth:
    """Tests for ConnectionHealth dataclass"""

    def test_initial_state(self):
        """Health should start disconnected with zero counts"""
        health = ConnectionHealth()
        assert health.state == ConnectionState.DISCONNECTED
        assert health.consecutive_failures == 0
        assert health.total_reconnects == 0
        assert health.last_heartbeat is None
        assert health.last_error is None

    def test_record_success(self):
        """Recording success should update health state"""
        health = ConnectionHealth()
        health.consecutive_failures = 5
        health.last_error = "some error"

        health.record_success()

        assert health.consecutive_failures == 0
        assert health.state == ConnectionState.CONNECTED
        assert health.last_error is None
        assert health.last_heartbeat is not None

    def test_record_failure(self):
        """Recording failure should increment failure count"""
        health = ConnectionHealth()

        health.record_failure("Connection refused")

        assert health.consecutive_failures == 1
        assert health.last_error == "Connection refused"

        health.record_failure("Timeout")

        assert health.consecutive_failures == 2
        assert health.last_error == "Timeout"

    def test_record_reconnect(self):
        """Recording reconnect should increment counter and update state"""
        health = ConnectionHealth()

        health.record_reconnect()

        assert health.total_reconnects == 1
        assert health.state == ConnectionState.RECONNECTING

        health.record_reconnect()

        assert health.total_reconnects == 2

    def test_to_dict(self):
        """to_dict should return all fields"""
        health = ConnectionHealth()
        health.record_success()

        result = health.to_dict()

        assert "last_heartbeat" in result
        assert "consecutive_failures" in result
        assert "total_reconnects" in result
        assert "state" in result
        assert "last_error" in result
        assert result["state"] == "connected"


# ===== RetryConfig Tests =====

class TestRetryConfig:
    """Tests for RetryConfig dataclass"""

    def test_default_values(self):
        """Default config should have reasonable values"""
        config = RetryConfig()
        assert config.max_retries == 5
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter == 0.1

    def test_custom_values(self):
        """Custom config should override defaults"""
        config = RetryConfig(
            max_retries=10,
            initial_delay=2.0,
            max_delay=60.0
        )
        assert config.max_retries == 10
        assert config.initial_delay == 2.0
        assert config.max_delay == 60.0


# ===== ConnectionRetryHandler Tests =====

class TestConnectionRetryHandler:
    """Tests for ConnectionRetryHandler"""

    @pytest.mark.asyncio
    async def test_first_attempt_no_delay(self):
        """First attempt should have no delay"""
        handler = ConnectionRetryHandler(RetryConfig(max_retries=3))
        delays = []

        async for delay in handler:
            delays.append(delay)
            handler.mark_success()
            break

        assert len(delays) == 1
        assert delays[0] == 0

    @pytest.mark.asyncio
    async def test_max_retries_honored(self):
        """Handler should stop after max_retries"""
        config = RetryConfig(max_retries=3, initial_delay=0.01)
        handler = ConnectionRetryHandler(config)
        attempts = 0

        async for _ in handler:
            attempts += 1
            handler.mark_failure("test error")

        assert attempts == 3
        assert handler.is_exhausted

    @pytest.mark.asyncio
    async def test_mark_success_stops_iteration(self):
        """mark_success should stop further iterations"""
        handler = ConnectionRetryHandler(RetryConfig(max_retries=10))
        attempts = 0

        async for _ in handler:
            attempts += 1
            if attempts == 2:
                handler.mark_success()
                break

        assert attempts == 2
        assert handler.is_exhausted

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Delays should increase exponentially"""
        # Use very short delays for testing
        config = RetryConfig(
            max_retries=4,
            initial_delay=0.01,
            max_delay=1.0,
            backoff_multiplier=2.0,
            jitter=0  # No jitter for predictable testing
        )
        handler = ConnectionRetryHandler(config)
        delays = []

        async for delay in handler:
            delays.append(delay)
            handler.mark_failure("test")

        # First attempt: 0 (no delay)
        # Second attempt: 0.01 (initial_delay)
        # Third attempt: 0.02 (initial * 2)
        # Fourth attempt: 0.04 (initial * 4)
        assert delays[0] == 0
        assert abs(delays[1] - 0.01) < 0.001
        assert abs(delays[2] - 0.02) < 0.001
        assert abs(delays[3] - 0.04) < 0.001

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Delay should be capped at max_delay"""
        config = RetryConfig(
            max_retries=10,
            initial_delay=100.0,  # Very high initial
            max_delay=0.05,  # But low cap
            jitter=0
        )
        handler = ConnectionRetryHandler(config)

        async for delay in handler:
            handler.mark_failure("test")
            if handler.attempt > 1:
                # After first attempt, delay should be capped
                assert delay <= 0.05
            if handler.attempt >= 3:
                break


# ===== LANDiscoveryService Connection Tests =====

class TestLANDiscoveryServiceConnection:
    """Tests for LANDiscoveryService connection with retry"""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test"""
        return LANDiscoveryService(device_name="TestDevice")

    @pytest.fixture
    def mock_device(self):
        """Create a mock hub device"""
        return LANDevice(
            id="test-hub-123",
            name="TestHub",
            ip="192.168.1.100",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now(UTC).isoformat()
        )

    def test_initial_connection_health(self, service):
        """Service should start with disconnected health state"""
        assert service.connection_health.state == ConnectionState.DISCONNECTED
        assert service.is_connected is False
        assert service._auto_reconnect is True

    def test_set_auto_reconnect(self, service):
        """set_auto_reconnect should update setting"""
        service.set_auto_reconnect(False)
        assert service._auto_reconnect is False

        service.set_auto_reconnect(True)
        assert service._auto_reconnect is True

    def test_set_heartbeat_interval(self, service):
        """set_heartbeat_interval should update with minimum"""
        service.set_heartbeat_interval(60.0)
        assert service._heartbeat_interval == 60.0

        # Should enforce minimum of 5 seconds
        service.set_heartbeat_interval(1.0)
        assert service._heartbeat_interval == 5.0

    @pytest.mark.asyncio
    async def test_connect_device_not_found(self, service):
        """connect_to_device should raise if device not discovered"""
        with pytest.raises(ValueError, match="not found"):
            await service.connect_to_device("nonexistent-device")

    @pytest.mark.asyncio
    async def test_connect_device_not_hub(self, service, mock_device):
        """connect_to_device should raise if device is not a hub"""
        mock_device.is_hub = False
        service.discovered_devices[mock_device.id] = mock_device

        with pytest.raises(ValueError, match="not a hub"):
            await service.connect_to_device(mock_device.id)

    @pytest.mark.asyncio
    async def test_connect_with_retry_success(self, service, mock_device):
        """connect_to_device should succeed on first attempt"""
        service.discovered_devices[mock_device.id] = mock_device

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.connect_to_device(
                mock_device.id,
                with_retry=True,
                start_heartbeat=False
            )

            assert result["status"] == "connected"
            assert service.is_connected is True
            assert service.connection_health.state == ConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_without_retry_fails(self, service, mock_device):
        """connect_to_device without retry should fail on first error"""
        service.discovered_devices[mock_device.id] = mock_device
        service.retry_config = RetryConfig(max_retries=5)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Connection error"):
                await service.connect_to_device(
                    mock_device.id,
                    with_retry=False,
                    start_heartbeat=False
                )

            assert service.is_connected is False
            assert service.connection_health.state == ConnectionState.FAILED

    @pytest.mark.asyncio
    async def test_disconnect_updates_state(self, service, mock_device):
        """disconnect_from_hub should update connection state"""
        # Set up as connected
        service.discovered_devices[mock_device.id] = mock_device
        service.connected_hub = mock_device
        service.is_connected = True
        service.connection_health.state = ConnectionState.CONNECTED

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.disconnect_from_hub()

            assert result["status"] == "disconnected"
            assert service.is_connected is False
            assert service.connection_health.state == ConnectionState.DISCONNECTED

    def test_get_status_includes_health(self, service):
        """get_status should include connection health info"""
        status = service.get_status()

        assert "connection_health" in status
        assert "auto_reconnect_enabled" in status
        assert "heartbeat_interval" in status
        assert "heartbeat_active" in status

    @pytest.mark.asyncio
    async def test_send_heartbeat_when_not_connected(self, service):
        """send_heartbeat should return False when not connected"""
        result = await service.send_heartbeat()
        assert result is False


# ===== Heartbeat Tests =====

class TestHeartbeat:
    """Tests for heartbeat functionality"""

    @pytest.fixture
    def service(self):
        """Create a fresh service"""
        return LANDiscoveryService()

    @pytest.mark.asyncio
    async def test_start_stop_heartbeat(self, service):
        """Heartbeat should start and stop correctly"""
        await service._start_heartbeat()
        assert service._heartbeat_task is not None
        assert not service._heartbeat_task.done()

        await service._stop_heartbeat()
        assert service._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_heartbeat_callback_registration(self, service):
        """Connection callbacks should be registerable"""
        callback_called = False

        def on_lost():
            nonlocal callback_called
            callback_called = True

        service.on_connection_lost(on_lost)
        assert service._on_connection_lost is not None

        # Trigger callback
        service._on_connection_lost()
        assert callback_called is True


# ===== Integration Tests =====

class TestLANConnectionIntegration:
    """Integration tests for connection resilience"""

    @pytest.fixture
    def service(self):
        return LANDiscoveryService()

    @pytest.fixture
    def mock_hub(self):
        return LANDevice(
            id="integration-hub",
            name="IntegrationHub",
            ip="10.0.0.1",
            port=8765,
            is_hub=True,
            version="1.0.0",
            discovered_at=datetime.now(UTC).isoformat()
        )

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, service, mock_hub):
        """Test complete connect -> heartbeat -> disconnect flow"""
        service.discovered_devices[mock_hub.id] = mock_hub

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Connect
            result = await service.connect_to_device(
                mock_hub.id,
                start_heartbeat=False
            )
            assert result["status"] == "connected"

            # Send manual heartbeat
            success = await service.send_heartbeat()
            assert success is True

            # Disconnect
            result = await service.disconnect_from_hub()
            assert result["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, service, mock_hub):
        """Test that retry handles transient failures"""
        service.discovered_devices[mock_hub.id] = mock_hub
        service.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # Fast for testing
            jitter=0
        )

        attempt_count = 0
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        async def mock_post(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Transient failure")
            return mock_response_success

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.connect_to_device(
                mock_hub.id,
                with_retry=True,
                start_heartbeat=False
            )

            assert result["status"] == "connected"
            assert attempt_count == 3
