"""
Comprehensive tests for api/offline_mesh_router.py

Tests the FastAPI router for offline mesh networking features including:
- Peer discovery (mDNS)
- File sharing (P2P)
- Mesh relay messaging
- Data synchronization (CRDT)
- MLX distributed computing

Coverage targets:
- Response models
- Peer discovery endpoints
- File sharing endpoints
- Mesh relay endpoints
- Data sync endpoints
- Distributed computing endpoints
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pathlib import Path
import tempfile
import json

# Import the router
from api.offline_mesh import router


# ========== Fixtures ==========

@pytest.fixture
def mock_current_user():
    """Mock authenticated user"""
    return {"user_id": "test_user_123", "username": "testuser"}


@pytest.fixture
def app(mock_current_user):
    """Create test FastAPI app with router"""
    from api.auth_middleware import get_current_user

    test_app = FastAPI()
    test_app.include_router(router)

    # Override auth dependency
    test_app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_mesh_discovery():
    """Mock mesh discovery service"""
    mock = MagicMock()
    mock.peer_id = "peer-123-abc"
    mock.start = AsyncMock(return_value=True)
    mock.stop = AsyncMock()
    mock.get_peers = MagicMock(return_value=[])
    mock.get_stats = MagicMock(return_value={"peers_discovered": 0})
    return mock


@pytest.fixture
def mock_file_share():
    """Mock file share service"""
    mock = MagicMock()
    mock.share_file = AsyncMock()
    mock.get_shared_files = MagicMock(return_value=[])
    mock.download_file = AsyncMock()
    mock.get_active_transfers = MagicMock(return_value=[])
    mock.delete_shared_file = AsyncMock(return_value=True)
    mock.get_stats = MagicMock(return_value={"files_shared": 0})
    return mock


@pytest.fixture
def mock_mesh_relay():
    """Mock mesh relay service"""
    mock = MagicMock()
    mock.add_direct_peer = MagicMock()
    mock.remove_direct_peer = MagicMock()
    mock.send_message = AsyncMock(return_value=True)
    mock.get_route_to = MagicMock(return_value=None)
    mock.get_stats = MagicMock(return_value={"messages_sent": 0})
    mock.get_routing_table = MagicMock(return_value={})
    return mock


@pytest.fixture
def mock_data_sync():
    """Mock data sync service"""
    mock = MagicMock()
    mock.sync_with_peer = AsyncMock()
    mock.get_sync_state = MagicMock(return_value=None)
    mock.get_all_sync_states = MagicMock(return_value=[])
    mock.get_stats = MagicMock(return_value={"syncs_completed": 0})
    mock._apply_operations = AsyncMock(return_value=0)
    mock._get_operations_since_last_sync = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_mlx_distributed():
    """Mock MLX distributed service"""
    mock = MagicMock()
    mock.local_node_id = "node-123"
    mock.device_name = "TestDevice"
    mock.port = 8766
    mock.start_server = AsyncMock(return_value=True)
    mock.get_nodes = MagicMock(return_value=[])
    mock.submit_job = AsyncMock()
    mock.get_job = MagicMock(return_value=None)
    mock.get_stats = MagicMock(return_value={"jobs_completed": 0})
    return mock


# ========== Response Model Tests ==========

class TestResponseModels:
    """Tests for Pydantic response models"""

    def test_discovery_start_response(self):
        """Test DiscoveryStartResponse model"""
        from api.offline_mesh import DiscoveryStartResponse

        data = DiscoveryStartResponse(
            status="started",
            peer_id="peer-123",
            display_name="Test Peer",
            device_name="test-device"
        )

        assert data.status == "started"
        assert data.peer_id == "peer-123"

    def test_peer_info(self):
        """Test PeerInfo model"""
        from api.offline_mesh import PeerInfo

        data = PeerInfo(
            peer_id="peer-123",
            display_name="Test Peer",
            device_name="test-device",
            ip_address="192.168.1.100",
            port=8765,
            capabilities=["file_share", "sync"],
            status="online",
            last_seen="2024-01-01T00:00:00Z"
        )

        assert data.capabilities == ["file_share", "sync"]

    def test_peers_list_response(self):
        """Test PeersListResponse model"""
        from api.offline_mesh import PeersListResponse

        data = PeersListResponse(count=0, peers=[])

        assert data.count == 0
        assert data.peers == []

    def test_file_share_response(self):
        """Test FileShareResponse model"""
        from api.offline_mesh import FileShareResponse

        data = FileShareResponse(
            file_id="file-123",
            filename="test.txt",
            size_bytes=1024,
            sha256_hash="abc123",
            shared_at="2024-01-01T00:00:00Z"
        )

        assert data.size_bytes == 1024

    def test_relay_peer_response(self):
        """Test RelayPeerResponse model"""
        from api.offline_mesh import RelayPeerResponse

        data = RelayPeerResponse(
            status="added",
            peer_id="peer-123",
            latency_ms=10.5
        )

        assert data.latency_ms == 10.5

    def test_sync_response(self):
        """Test SyncResponse model"""
        from api.offline_mesh import SyncResponse

        data = SyncResponse(
            status="completed",
            peer_id="peer-123",
            last_sync="2024-01-01T00:00:00Z",
            operations_sent=10,
            operations_received=5,
            conflicts_resolved=2
        )

        assert data.operations_sent == 10


# ========== Peer Discovery Endpoint Tests ==========

class TestPeerDiscoveryEndpoints:
    """Tests for peer discovery endpoints"""

    def test_start_discovery_success(self, client, mock_mesh_discovery):
        """Test starting peer discovery"""
        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post(
                "/api/v1/mesh/discovery/start",
                params={"display_name": "Test Peer", "device_name": "test-device"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert data["peer_id"] == "peer-123-abc"
            assert data["display_name"] == "Test Peer"

    def test_start_discovery_failure(self, client, mock_mesh_discovery):
        """Test discovery start failure"""
        mock_mesh_discovery.start = AsyncMock(return_value=False)

        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post(
                "/api/v1/mesh/discovery/start",
                params={"display_name": "Test", "device_name": "test"}
            )

            assert response.status_code == 500
            assert "Failed" in response.json()["detail"]

    def test_start_discovery_exception(self, client, mock_mesh_discovery):
        """Test discovery start exception"""
        mock_mesh_discovery.start = AsyncMock(side_effect=Exception("Network error"))

        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post(
                "/api/v1/mesh/discovery/start",
                params={"display_name": "Test", "device_name": "test"}
            )

            assert response.status_code == 500
            assert "Network error" in response.json()["detail"]

    def test_get_discovered_peers_empty(self, client, mock_mesh_discovery):
        """Test getting empty peer list"""
        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.get("/api/v1/mesh/discovery/peers")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert data["peers"] == []

    def test_get_discovered_peers_with_peers(self, client, mock_mesh_discovery):
        """Test getting peer list with peers"""
        mock_peer = MagicMock()
        mock_peer.peer_id = "peer-456"
        mock_peer.display_name = "Other Peer"
        mock_peer.device_name = "other-device"
        mock_peer.ip_address = "192.168.1.101"
        mock_peer.port = 8765
        mock_peer.capabilities = ["sync"]
        mock_peer.status = "online"
        mock_peer.last_seen = "2024-01-01T00:00:00Z"

        mock_mesh_discovery.get_peers = MagicMock(return_value=[mock_peer])

        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.get("/api/v1/mesh/discovery/peers")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["peers"][0]["peer_id"] == "peer-456"

    def test_get_discovery_stats(self, client, mock_mesh_discovery):
        """Test getting discovery statistics"""
        mock_mesh_discovery.get_stats = MagicMock(return_value={
            "peers_discovered": 5,
            "uptime_seconds": 3600
        })

        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.get("/api/v1/mesh/discovery/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["peers_discovered"] == 5

    def test_stop_discovery(self, client, mock_mesh_discovery):
        """Test stopping discovery"""
        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post("/api/v1/mesh/discovery/stop")

            assert response.status_code == 200
            assert response.json()["status"] == "stopped"
            mock_mesh_discovery.stop.assert_called_once()


# ========== File Sharing Endpoint Tests ==========

class TestFileSharingEndpoints:
    """Tests for file sharing endpoints"""

    def test_share_file_success(self, client, mock_file_share):
        """Test sharing a file"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            mock_shared_file = MagicMock()
            mock_shared_file.file_id = "file-123"
            mock_shared_file.filename = "test.txt"
            mock_shared_file.size_bytes = 12
            mock_shared_file.sha256_hash = "abc123"
            mock_shared_file.shared_at = "2024-01-01T00:00:00Z"

            mock_file_share.share_file = AsyncMock(return_value=mock_shared_file)

            with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
                response = client.post(
                    "/api/v1/mesh/files/share",
                    json={
                        "file_path": temp_path,
                        "shared_by_peer_id": "peer-123",
                        "shared_by_name": "Test User"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["file_id"] == "file-123"
        finally:
            import os
            os.unlink(temp_path)

    def test_share_file_not_found(self, client, mock_file_share):
        """Test sharing nonexistent file"""
        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.post(
                "/api/v1/mesh/files/share",
                json={
                    "file_path": "/nonexistent/file.txt",
                    "shared_by_peer_id": "peer-123",
                    "shared_by_name": "Test User"
                }
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_list_shared_files_empty(self, client, mock_file_share):
        """Test listing shared files when empty"""
        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/list")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert data["files"] == []

    def test_list_shared_files_with_files(self, client, mock_file_share):
        """Test listing shared files"""
        mock_file = MagicMock()
        mock_file.file_id = "file-123"
        mock_file.filename = "test.txt"
        mock_file.size_bytes = 1024
        mock_file.mime_type = "text/plain"
        mock_file.shared_by_name = "Test User"
        mock_file.shared_at = "2024-01-01T00:00:00Z"
        mock_file.description = "Test file"
        mock_file.tags = ["test"]

        mock_file_share.get_shared_files = MagicMock(return_value=[mock_file])

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/list")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["files"][0]["file_id"] == "file-123"

    def test_list_shared_files_with_tags(self, client, mock_file_share):
        """Test listing shared files with tag filter"""
        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/list", params={"tags": "doc,report"})

            assert response.status_code == 200
            mock_file_share.get_shared_files.assert_called_once()

    def test_download_file(self, client, mock_file_share):
        """Test downloading a file"""
        mock_file_share.download_file = AsyncMock(return_value=Path("/tmp/downloaded.txt"))

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.post(
                "/api/v1/mesh/files/download",
                json={
                    "file_id": "file-123",
                    "peer_ip": "192.168.1.100",
                    "peer_port": 8765,
                    "destination_path": "/tmp/downloads"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

    def test_get_active_transfers(self, client, mock_file_share):
        """Test getting active transfers"""
        mock_transfer = MagicMock()
        mock_transfer.file_id = "file-123"
        mock_transfer.filename = "test.txt"
        mock_transfer.bytes_transferred = 512
        mock_transfer.total_bytes = 1024
        mock_transfer.speed_mbps = 10.5
        mock_transfer.eta_seconds = 30
        mock_transfer.status = "transferring"

        mock_file_share.get_active_transfers = MagicMock(return_value=[mock_transfer])

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/transfers")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["transfers"][0]["progress_percent"] == 50.0

    def test_delete_shared_file_success(self, client, mock_file_share):
        """Test deleting a shared file"""
        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.delete("/api/v1/mesh/files/file-123")

            assert response.status_code == 200
            assert response.json()["status"] == "deleted"

    def test_delete_shared_file_not_found(self, client, mock_file_share):
        """Test deleting nonexistent file"""
        mock_file_share.delete_shared_file = AsyncMock(return_value=False)

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.delete("/api/v1/mesh/files/nonexistent")

            assert response.status_code == 404

    def test_get_file_sharing_stats(self, client, mock_file_share):
        """Test getting file sharing stats"""
        mock_file_share.get_stats = MagicMock(return_value={
            "files_shared": 10,
            "total_bytes_shared": 1048576
        })

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/stats")

            assert response.status_code == 200
            assert response.json()["files_shared"] == 10


# ========== Mesh Relay Endpoint Tests ==========

class TestMeshRelayEndpoints:
    """Tests for mesh relay endpoints"""

    def test_add_relay_peer(self, client, mock_mesh_relay):
        """Test adding a relay peer"""
        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.post(
                "/api/v1/mesh/relay/peer/add",
                params={"peer_id": "peer-456", "latency_ms": 15.0}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "added"
            assert data["peer_id"] == "peer-456"
            assert data["latency_ms"] == 15.0

    def test_remove_relay_peer(self, client, mock_mesh_relay):
        """Test removing a relay peer"""
        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.delete("/api/v1/mesh/relay/peer/peer-456")

            assert response.status_code == 200
            assert response.json()["status"] == "removed"
            mock_mesh_relay.remove_direct_peer.assert_called_with("peer-456")

    def test_send_relay_message_success(self, client, mock_mesh_relay):
        """Test sending a message through relay"""
        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.post(
                "/api/v1/mesh/relay/send",
                json={
                    "dest_peer_id": "peer-456",
                    "payload": {"type": "chat", "message": "Hello"}
                }
            )

            assert response.status_code == 200
            assert response.json()["status"] == "sent"

    def test_send_relay_message_queued(self, client, mock_mesh_relay):
        """Test message queued when no route available"""
        mock_mesh_relay.send_message = AsyncMock(return_value=False)

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.post(
                "/api/v1/mesh/relay/send",
                json={
                    "dest_peer_id": "peer-456",
                    "payload": {"message": "Hello"}
                }
            )

            assert response.status_code == 200
            assert response.json()["status"] == "queued"

    def test_get_route_to_peer_found(self, client, mock_mesh_relay):
        """Test getting route when route exists"""
        mock_mesh_relay.get_route_to = MagicMock(return_value=["local", "peer-123", "peer-456"])

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.get("/api/v1/mesh/relay/route/peer-456")

            assert response.status_code == 200
            data = response.json()
            assert data["hop_count"] == 2

    def test_get_route_to_peer_not_found(self, client, mock_mesh_relay):
        """Test getting route when no route exists"""
        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.get("/api/v1/mesh/relay/route/unknown-peer")

            assert response.status_code == 404
            assert "No route" in response.json()["detail"]

    def test_get_relay_stats(self, client, mock_mesh_relay):
        """Test getting relay statistics"""
        mock_mesh_relay.get_stats = MagicMock(return_value={
            "messages_sent": 100,
            "messages_relayed": 50
        })

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.get("/api/v1/mesh/relay/stats")

            assert response.status_code == 200
            assert response.json()["messages_sent"] == 100

    def test_get_routing_table(self, client, mock_mesh_relay):
        """Test getting routing table"""
        mock_mesh_relay.get_routing_table = MagicMock(return_value={
            "peer-456": ["local", "peer-456"],
            "peer-789": ["local", "peer-123", "peer-789"]
        })

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.get("/api/v1/mesh/relay/routing-table")

            assert response.status_code == 200
            data = response.json()
            assert "peer-456" in data


# ========== Data Sync Endpoint Tests ==========

class TestDataSyncEndpoints:
    """Tests for data sync endpoints"""

    def test_start_sync_success(self, client, mock_data_sync):
        """Test starting data sync"""
        mock_state = MagicMock()
        mock_state.status = "completed"
        mock_state.peer_id = "peer-456"
        mock_state.last_sync = "2024-01-01T00:00:00Z"
        mock_state.operations_sent = 10
        mock_state.operations_received = 5
        mock_state.conflicts_resolved = 2

        mock_data_sync.sync_with_peer = AsyncMock(return_value=mock_state)

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            with patch('api.offline_mesh.sync_routes.metrics') as mock_metrics:
                mock_metrics.track.return_value.__enter__ = MagicMock()
                mock_metrics.track.return_value.__exit__ = MagicMock()

                response = client.post(
                    "/api/v1/mesh/sync/start",
                    json={"peer_id": "peer-456", "tables": ["chat_sessions"]}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["operations_sent"] == 10

    def test_start_sync_failure(self, client, mock_data_sync):
        """Test sync failure"""
        mock_data_sync.sync_with_peer = AsyncMock(side_effect=Exception("Connection failed"))

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            # Create a proper context manager mock for metrics.track
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=None)
            mock_cm.__exit__ = MagicMock(return_value=False)

            with patch('api.offline_mesh.sync_routes.metrics') as mock_metrics:
                mock_metrics.track.return_value = mock_cm

                response = client.post(
                    "/api/v1/mesh/sync/start",
                    json={"peer_id": "peer-456"}
                )

                assert response.status_code == 500
                assert "Connection failed" in response.json()["detail"]

    def test_get_sync_state_found(self, client, mock_data_sync):
        """Test getting sync state"""
        mock_state = MagicMock()
        mock_state.peer_id = "peer-456"
        mock_state.last_sync = "2024-01-01T00:00:00Z"
        mock_state.operations_sent = 10
        mock_state.operations_received = 5
        mock_state.conflicts_resolved = 2
        mock_state.status = "idle"

        mock_data_sync.get_sync_state = MagicMock(return_value=mock_state)

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            response = client.get("/api/v1/mesh/sync/state/peer-456")

            assert response.status_code == 200
            data = response.json()
            assert data["peer_id"] == "peer-456"

    def test_get_sync_state_not_found(self, client, mock_data_sync):
        """Test getting nonexistent sync state"""
        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            response = client.get("/api/v1/mesh/sync/state/unknown-peer")

            assert response.status_code == 404
            assert "No sync state" in response.json()["detail"]

    def test_get_all_sync_states(self, client, mock_data_sync):
        """Test getting all sync states"""
        mock_state = MagicMock()
        mock_state.peer_id = "peer-456"
        mock_state.last_sync = "2024-01-01T00:00:00Z"
        mock_state.operations_sent = 10
        mock_state.operations_received = 5
        mock_state.conflicts_resolved = 2
        mock_state.status = "idle"

        mock_data_sync.get_all_sync_states = MagicMock(return_value=[mock_state])

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            response = client.get("/api/v1/mesh/sync/states")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1

    def test_get_sync_stats(self, client, mock_data_sync):
        """Test getting sync statistics"""
        mock_data_sync.get_stats = MagicMock(return_value={
            "syncs_completed": 100,
            "total_conflicts": 10
        })

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            response = client.get("/api/v1/mesh/sync/stats")

            assert response.status_code == 200
            assert response.json()["syncs_completed"] == 100

    def test_exchange_sync_operations(self, client, mock_data_sync):
        """Test exchanging sync operations"""
        # The endpoint imports SyncOperation locally from offline_data_sync
        # We need to patch it at the source module
        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            # Mock the module-level import inside the endpoint function
            with patch.dict('sys.modules', {'offline_data_sync': MagicMock()}):
                # With empty operations list, the loop doesn't execute
                response = client.post(
                    "/api/v1/mesh/sync/exchange",
                    json={
                        "sender_peer_id": "peer-456",
                        "operations": []
                    }
                )

                # Should return 200 with empty operations applied
                assert response.status_code == 200
                data = response.json()
                assert data["operations_applied"] == 0


# ========== MLX Distributed Computing Endpoint Tests ==========

class TestMLXDistributedEndpoints:
    """Tests for MLX distributed computing endpoints"""

    def test_start_compute_server_success(self, client, mock_mlx_distributed):
        """Test starting compute server"""
        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.post("/api/v1/mesh/compute/start", params={"port": 8766})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert data["node_id"] == "node-123"

    def test_start_compute_server_failure(self, client, mock_mlx_distributed):
        """Test compute server start failure"""
        mock_mlx_distributed.start_server = AsyncMock(return_value=False)

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.post("/api/v1/mesh/compute/start")

            assert response.status_code == 500
            assert "Failed" in response.json()["detail"]

    def test_get_compute_nodes_empty(self, client, mock_mlx_distributed):
        """Test getting empty compute nodes list"""
        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.get("/api/v1/mesh/compute/nodes")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0

    def test_get_compute_nodes_with_nodes(self, client, mock_mlx_distributed):
        """Test getting compute nodes"""
        mock_node = MagicMock()
        mock_node.node_id = "node-456"
        mock_node.device_name = "MacBook Pro"
        mock_node.ip_address = "192.168.1.100"
        mock_node.port = 8766
        mock_node.gpu_memory_gb = 16.0
        mock_node.cpu_cores = 8
        mock_node.metal_version = "Metal 3"
        mock_node.status = "available"
        mock_node.current_load = 0.3
        mock_node.jobs_completed = 50

        mock_mlx_distributed.get_nodes = MagicMock(return_value=[mock_node])

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.get("/api/v1/mesh/compute/nodes")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["nodes"][0]["gpu_memory_gb"] == 16.0

    def test_submit_compute_job(self, client, mock_mlx_distributed):
        """Test submitting a compute job"""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_job.job_type = "embedding"
        mock_job.status = "queued"
        mock_job.assigned_node = "node-456"
        mock_job.created_at = "2024-01-01T00:00:00Z"

        mock_mlx_distributed.submit_job = AsyncMock(return_value=mock_job)

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.post(
                "/api/v1/mesh/compute/job/submit",
                json={
                    "job_type": "embedding",
                    "data": {"text": "Hello world"},
                    "model_name": "nomic-embed-text"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-123"
            assert data["status"] == "queued"

    def test_get_job_status_found(self, client, mock_mlx_distributed):
        """Test getting job status"""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_job.job_type = "embedding"
        mock_job.status = "completed"
        mock_job.assigned_node = "node-456"
        mock_job.result = {"embedding": [0.1, 0.2, 0.3]}
        mock_job.created_at = "2024-01-01T00:00:00Z"
        mock_job.completed_at = "2024-01-01T00:00:05Z"

        mock_mlx_distributed.get_job = MagicMock(return_value=mock_job)

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.get("/api/v1/mesh/compute/job/job-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["result"] is not None

    def test_get_job_status_not_found(self, client, mock_mlx_distributed):
        """Test getting nonexistent job"""
        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.get("/api/v1/mesh/compute/job/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_compute_stats(self, client, mock_mlx_distributed):
        """Test getting compute statistics"""
        mock_mlx_distributed.get_stats = MagicMock(return_value={
            "jobs_completed": 100,
            "total_compute_time_seconds": 3600
        })

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.get("/api/v1/mesh/compute/stats")

            assert response.status_code == 200
            assert response.json()["jobs_completed"] == 100


# ========== Request Model Tests ==========

class TestRequestModels:
    """Tests for Pydantic request models"""

    def test_share_file_request(self):
        """Test ShareFileRequest model"""
        from api.offline_mesh import ShareFileRequest

        data = ShareFileRequest(
            file_path="/path/to/file.txt",
            shared_by_peer_id="peer-123",
            shared_by_name="Test User",
            description="Test file",
            tags=["test", "document"]
        )

        assert data.file_path == "/path/to/file.txt"
        assert data.tags == ["test", "document"]

    def test_share_file_request_optional_fields(self):
        """Test ShareFileRequest with optional fields"""
        from api.offline_mesh import ShareFileRequest

        data = ShareFileRequest(
            file_path="/path/to/file.txt",
            shared_by_peer_id="peer-123",
            shared_by_name="Test User"
        )

        assert data.description is None
        assert data.tags is None

    def test_download_file_request(self):
        """Test DownloadFileRequest model"""
        from api.offline_mesh import DownloadFileRequest

        data = DownloadFileRequest(
            file_id="file-123",
            peer_ip="192.168.1.100",
            peer_port=8765,
            destination_path="/tmp/downloads"
        )

        assert data.peer_port == 8765

    def test_send_message_request(self):
        """Test SendMessageRequest model"""
        from api.offline_mesh import SendMessageRequest

        data = SendMessageRequest(
            dest_peer_id="peer-456",
            payload={"type": "chat", "message": "Hello"},
            ttl=10
        )

        assert data.ttl == 10

    def test_send_message_request_optional_ttl(self):
        """Test SendMessageRequest without TTL"""
        from api.offline_mesh import SendMessageRequest

        data = SendMessageRequest(
            dest_peer_id="peer-456",
            payload={"message": "Hello"}
        )

        assert data.ttl is None

    def test_sync_request(self):
        """Test SyncRequest model"""
        from api.offline_mesh import SyncRequest

        data = SyncRequest(
            peer_id="peer-456",
            tables=["chat_sessions", "vault_files"]
        )

        assert len(data.tables) == 2

    def test_sync_request_optional_tables(self):
        """Test SyncRequest without tables"""
        from api.offline_mesh import SyncRequest

        data = SyncRequest(peer_id="peer-456")

        assert data.tables is None

    def test_sync_exchange_request(self):
        """Test SyncExchangeRequest model"""
        from api.offline_mesh import SyncExchangeRequest

        data = SyncExchangeRequest(
            sender_peer_id="peer-456",
            operations=[
                {"op_id": "op-1", "table_name": "chat", "operation": "insert"}
            ]
        )

        assert len(data.operations) == 1

    def test_submit_job_request(self):
        """Test SubmitJobRequest model"""
        from api.offline_mesh import SubmitJobRequest

        data = SubmitJobRequest(
            job_type="embedding",
            data={"text": "Hello"},
            model_name="nomic-embed-text"
        )

        assert data.job_type == "embedding"


# ========== Error Handling Tests ==========

class TestErrorHandling:
    """Tests for error handling"""

    def test_discovery_exception_handling(self, client, mock_mesh_discovery):
        """Test exception handling in discovery endpoints"""
        mock_mesh_discovery.get_peers = MagicMock(side_effect=Exception("Service unavailable"))

        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.get("/api/v1/mesh/discovery/peers")

            assert response.status_code == 500
            assert "Service unavailable" in response.json()["detail"]

    def test_file_share_exception_handling(self, client, mock_file_share):
        """Test exception handling in file share endpoints"""
        mock_file_share.get_shared_files = MagicMock(side_effect=Exception("Storage error"))

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/list")

            assert response.status_code == 500
            assert "Storage error" in response.json()["detail"]

    def test_relay_exception_handling(self, client, mock_mesh_relay):
        """Test exception handling in relay endpoints"""
        mock_mesh_relay.get_stats = MagicMock(side_effect=Exception("Network error"))

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.get("/api/v1/mesh/relay/stats")

            assert response.status_code == 500
            assert "Network error" in response.json()["detail"]

    def test_compute_exception_handling(self, client, mock_mlx_distributed):
        """Test exception handling in compute endpoints"""
        mock_mlx_distributed.start_server = AsyncMock(side_effect=Exception("GPU unavailable"))

        with patch('api.offline_mesh.compute_routes.get_mlx_distributed', return_value=mock_mlx_distributed):
            response = client.post("/api/v1/mesh/compute/start")

            assert response.status_code == 500
            assert "GPU unavailable" in response.json()["detail"]


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_discovery_to_sync_workflow(self, client, mock_mesh_discovery, mock_data_sync):
        """Test discovery then sync workflow"""
        # Start discovery
        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post(
                "/api/v1/mesh/discovery/start",
                params={"display_name": "Test", "device_name": "test"}
            )
            assert response.status_code == 200
            peer_id = response.json()["peer_id"]

        # Start sync with discovered peer
        mock_state = MagicMock()
        mock_state.status = "completed"
        mock_state.peer_id = "peer-456"
        mock_state.last_sync = "2024-01-01T00:00:00Z"
        mock_state.operations_sent = 10
        mock_state.operations_received = 5
        mock_state.conflicts_resolved = 0
        mock_data_sync.sync_with_peer = AsyncMock(return_value=mock_state)

        with patch('api.offline_mesh.sync_routes.get_data_sync', return_value=mock_data_sync):
            with patch('api.offline_mesh.sync_routes.metrics') as mock_metrics:
                mock_metrics.track.return_value.__enter__ = MagicMock()
                mock_metrics.track.return_value.__exit__ = MagicMock()

                response = client.post(
                    "/api/v1/mesh/sync/start",
                    json={"peer_id": "peer-456"}
                )
                assert response.status_code == 200

    def test_file_share_to_download_workflow(self, client, mock_file_share):
        """Test share then download workflow"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"shared content")
            temp_path = f.name

        try:
            # Share file
            mock_shared = MagicMock()
            mock_shared.file_id = "file-shared"
            mock_shared.filename = "test.txt"
            mock_shared.size_bytes = 14
            mock_shared.sha256_hash = "abc123"
            mock_shared.shared_at = "2024-01-01T00:00:00Z"
            mock_file_share.share_file = AsyncMock(return_value=mock_shared)

            with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
                response = client.post(
                    "/api/v1/mesh/files/share",
                    json={
                        "file_path": temp_path,
                        "shared_by_peer_id": "peer-123",
                        "shared_by_name": "Test"
                    }
                )
                assert response.status_code == 200
                file_id = response.json()["file_id"]

            # Download file
            mock_file_share.download_file = AsyncMock(return_value=Path("/tmp/downloaded.txt"))

            with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
                response = client.post(
                    "/api/v1/mesh/files/download",
                    json={
                        "file_id": file_id,
                        "peer_ip": "192.168.1.100",
                        "peer_port": 8765,
                        "destination_path": "/tmp"
                    }
                )
                assert response.status_code == 200
        finally:
            import os
            os.unlink(temp_path)


# ========== Edge Cases Tests ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_tags_filter(self, client, mock_file_share):
        """Test file list with empty tags"""
        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/list", params={"tags": ""})

            assert response.status_code == 200

    def test_unicode_in_display_name(self, client, mock_mesh_discovery):
        """Test unicode in display name"""
        with patch('api.offline_mesh.discovery_routes.get_mesh_discovery', return_value=mock_mesh_discovery):
            response = client.post(
                "/api/v1/mesh/discovery/start",
                params={"display_name": "テスト機器", "device_name": "test-日本語"}
            )

            assert response.status_code == 200

    def test_large_payload_message(self, client, mock_mesh_relay):
        """Test sending message with large payload"""
        large_payload = {"data": "x" * 10000}

        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.post(
                "/api/v1/mesh/relay/send",
                json={
                    "dest_peer_id": "peer-456",
                    "payload": large_payload
                }
            )

            assert response.status_code == 200

    def test_zero_latency_peer(self, client, mock_mesh_relay):
        """Test adding peer with zero latency"""
        with patch('api.offline_mesh.relay_routes.get_mesh_relay', return_value=mock_mesh_relay):
            response = client.post(
                "/api/v1/mesh/relay/peer/add",
                params={"peer_id": "peer-456", "latency_ms": 0.0}
            )

            assert response.status_code == 200

    def test_transfer_progress_zero_total_bytes(self, client, mock_file_share):
        """Test transfer with zero total bytes (avoid division by zero)"""
        mock_transfer = MagicMock()
        mock_transfer.file_id = "file-123"
        mock_transfer.filename = "empty.txt"
        mock_transfer.bytes_transferred = 0
        mock_transfer.total_bytes = 0
        mock_transfer.speed_mbps = 0.0
        mock_transfer.eta_seconds = 0
        mock_transfer.status = "completed"

        mock_file_share.get_active_transfers = MagicMock(return_value=[mock_transfer])

        with patch('api.offline_mesh.files_routes.get_file_share', return_value=mock_file_share):
            response = client.get("/api/v1/mesh/files/transfers")

            assert response.status_code == 200
            # Should handle division by zero gracefully
            assert response.json()["transfers"][0]["progress_percent"] == 0
