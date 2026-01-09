"""
Comprehensive tests for api/p2p_chat_router.py

Tests FastAPI router for P2P team chat functionality including:
- Initialization endpoint
- Status & peer endpoints
- Channel management
- Message handling
- Channel invitations
- Read receipts
- E2E encryption endpoints
- WebSocket connections

Coverage targets: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

# Import the router and models
from api.p2p_chat import (
    router,
    channel_invitations,
    read_receipts,
    active_connections,
    broadcast_event,
)
from api.p2p_chat_models import (
    Peer, Channel, Message,
    CreateChannelRequest, CreateDMRequest,
    SendMessageRequest, InviteToChannelRequest,
    ChannelType
)


# ========== Fixtures ==========

@pytest.fixture
def mock_current_user():
    """Mock authenticated user"""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "role": "admin"
    }


@pytest.fixture
def mock_regular_user():
    """Mock non-admin user"""
    return {
        "user_id": "regular-user-456",
        "username": "regularuser",
        "role": "member"
    }


@pytest.fixture
def app(mock_current_user):
    """Create FastAPI test app with router"""
    from api.auth_middleware import get_current_user

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_p2p_service():
    """Create mock P2P chat service"""
    service = MagicMock()
    service.peer_id = "local-peer-123"
    service.is_running = True
    service.host = MagicMock()
    service.host.get_addrs.return_value = ["/ip4/192.168.1.100/tcp/4001"]
    return service


@pytest.fixture
def sample_peer():
    """Create sample peer"""
    from api.p2p_chat_models import PeerStatus
    return Peer(
        peer_id="peer-456",
        display_name="Test Peer",
        device_name="MacBook Pro",
        public_key="abc123pubkey",
        status=PeerStatus.ONLINE,
        last_seen=datetime.now(UTC).isoformat()
    )


@pytest.fixture
def sample_channel():
    """Create sample channel"""
    return Channel(
        id="channel-789",
        name="General",
        type=ChannelType.PUBLIC,
        created_by="local-peer-123",
        created_at=datetime.now(UTC).isoformat(),
        members=["local-peer-123", "peer-456"]
    )


@pytest.fixture
def sample_message():
    """Create sample message"""
    from api.p2p_chat_models import MessageType
    return Message(
        id="msg-001",
        channel_id="channel-789",
        sender_id="local-peer-123",
        sender_name="Test User",
        type=MessageType.TEXT,
        content="Hello, world!",
        timestamp=datetime.now(UTC).isoformat()
    )


@pytest.fixture(autouse=True)
def clear_state():
    """Clear in-memory state between tests"""
    channel_invitations.clear()
    read_receipts.clear()
    active_connections.clear()
    yield
    channel_invitations.clear()
    read_receipts.clear()
    active_connections.clear()


# ========== Initialization Tests ==========

class TestInitializeEndpoint:
    """Tests for POST /initialize"""

    def test_initialize_success(self, client, mock_p2p_service):
        """Test successful P2P service initialization"""
        mock_p2p_service.start = AsyncMock()

        with patch('api.p2p_chat.status_routes.init_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/initialize",
                params={"display_name": "Test User", "device_name": "MacBook"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["peer_id"] == "local-peer-123"
        assert data["display_name"] == "Test User"
        assert data["device_name"] == "MacBook"

    def test_initialize_failure(self, client):
        """Test initialization failure"""
        with patch('api.p2p_chat.status_routes.init_p2p_chat_service', side_effect=Exception("Failed to start")):
            response = client.post(
                "/api/v1/team/initialize",
                params={"display_name": "Test", "device_name": "Device"}
            )

        assert response.status_code == 500
        assert "Failed to start" in response.json()["detail"]


# ========== Status Endpoint Tests ==========

class TestStatusEndpoint:
    """Tests for GET /status"""

    def test_get_status_success(self, client, mock_p2p_service, sample_peer, sample_channel):
        """Test successful status retrieval"""
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])
        mock_p2p_service.list_channels = AsyncMock(return_value=[sample_channel])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/status")

        assert response.status_code == 200
        data = response.json()
        assert data["peer_id"] == "local-peer-123"
        assert data["is_connected"] is True
        assert data["discovered_peers"] == 1
        assert data["active_channels"] == 1
        assert len(data["multiaddrs"]) == 1

    def test_get_status_service_not_running(self, client, mock_p2p_service):
        """Test status when service not running"""
        mock_p2p_service.is_running = False

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/status")

        assert response.status_code == 503
        assert "not running" in response.json()["detail"]

    def test_get_status_service_none(self, client):
        """Test status when service not initialized"""
        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=None):
            response = client.get("/api/v1/team/status")

        assert response.status_code == 503

    def test_get_status_no_host(self, client, mock_p2p_service, sample_peer, sample_channel):
        """Test status when host is None"""
        mock_p2p_service.host = None
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])
        mock_p2p_service.list_channels = AsyncMock(return_value=[sample_channel])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/status")

        assert response.status_code == 200
        assert response.json()["multiaddrs"] == []


# ========== Peers Endpoint Tests ==========

class TestPeersEndpoints:
    """Tests for peer endpoints"""

    def test_list_peers_success(self, client, mock_p2p_service, sample_peer):
        """Test successful peer listing"""
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/peers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["peers"]) == 1
        assert data["peers"][0]["peer_id"] == "peer-456"

    def test_list_peers_empty(self, client, mock_p2p_service):
        """Test listing when no peers"""
        mock_p2p_service.list_peers = AsyncMock(return_value=[])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/peers")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_peers_service_none(self, client):
        """Test listing when service not initialized"""
        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=None):
            response = client.get("/api/v1/team/peers")

        assert response.status_code == 503

    def test_get_peer_success(self, client, mock_p2p_service, sample_peer):
        """Test getting specific peer"""
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/peers/peer-456")

        assert response.status_code == 200
        assert response.json()["peer_id"] == "peer-456"

    def test_get_peer_not_found(self, client, mock_p2p_service, sample_peer):
        """Test getting nonexistent peer"""
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/peers/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ========== Channel Endpoint Tests ==========

class TestChannelEndpoints:
    """Tests for channel endpoints"""

    def test_create_channel_success(self, client, mock_p2p_service, sample_channel):
        """Test successful channel creation"""
        mock_p2p_service.create_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.channels_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    "/api/v1/team/channels",
                    json={"name": "General", "type": "public"}
                )

        assert response.status_code == 200
        assert response.json()["name"] == "General"

    def test_create_channel_service_not_running(self, client, mock_p2p_service):
        """Test channel creation when service not running"""
        mock_p2p_service.is_running = False

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels",
                json={"name": "Test", "type": "public"}
            )

        assert response.status_code == 503

    def test_create_channel_failure(self, client, mock_p2p_service):
        """Test channel creation failure"""
        mock_p2p_service.create_channel = AsyncMock(side_effect=Exception("Creation failed"))

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels",
                json={"name": "Test", "type": "public"}
            )

        assert response.status_code == 500

    def test_list_channels_success(self, client, mock_p2p_service, sample_channel):
        """Test successful channel listing"""
        mock_p2p_service.list_channels = AsyncMock(return_value=[sample_channel])

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["channels"]) == 1

    def test_get_channel_success(self, client, mock_p2p_service, sample_channel):
        """Test getting specific channel"""
        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/channel-789")

        assert response.status_code == 200
        assert response.json()["id"] == "channel-789"

    def test_get_channel_not_found(self, client, mock_p2p_service):
        """Test getting nonexistent channel"""
        mock_p2p_service.get_channel = AsyncMock(return_value=None)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/nonexistent")

        assert response.status_code == 404


# ========== Direct Message Tests ==========

class TestDirectMessageEndpoints:
    """Tests for DM endpoints"""

    def test_create_dm_new(self, client, mock_p2p_service, sample_peer, sample_channel):
        """Test creating new DM channel"""
        sample_channel.type = ChannelType.DIRECT
        sample_channel.dm_participants = ["local-peer-123", "peer-456"]

        mock_p2p_service.list_channels = AsyncMock(return_value=[])
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])
        mock_p2p_service.create_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/dm",
                json={"peer_id": "peer-456"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "direct"

    def test_create_dm_existing(self, client, mock_p2p_service, sample_channel):
        """Test creating DM when already exists"""
        sample_channel.type = ChannelType.DIRECT
        sample_channel.dm_participants = ["local-peer-123", "peer-456"]

        mock_p2p_service.list_channels = AsyncMock(return_value=[sample_channel])

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/dm",
                json={"peer_id": "peer-456"}
            )

        assert response.status_code == 200
        # Returns existing channel (model uses 'id' not 'channel_id')
        assert response.json()["id"] == "channel-789"

    def test_create_dm_peer_not_found(self, client, mock_p2p_service, sample_peer):
        """Test creating DM with nonexistent peer"""
        mock_p2p_service.list_channels = AsyncMock(return_value=[])
        mock_p2p_service.list_peers = AsyncMock(return_value=[sample_peer])

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/dm",
                json={"peer_id": "nonexistent-peer"}
            )

        assert response.status_code == 404
        assert "Peer not found" in response.json()["detail"]

    def test_create_dm_service_not_running(self, client, mock_p2p_service):
        """Test creating DM when service not running"""
        mock_p2p_service.is_running = False

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/dm",
                json={"peer_id": "peer-456"}
            )

        assert response.status_code == 503


# ========== Channel Invitation Tests ==========

class TestChannelInvitations:
    """Tests for channel invitation endpoints"""

    def test_invite_to_channel_success(self, client, mock_p2p_service, sample_channel):
        """Test successful channel invitation"""
        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invite",
                json={"channel_id": "channel-789", "peer_ids": ["peer-1", "peer-2"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "invited"
        assert data["total"] == 2
        assert len(data["invitations"]) == 2

    def test_invite_duplicate(self, client, mock_p2p_service, sample_channel):
        """Test inviting same peer twice"""
        # Set up existing invitation
        channel_invitations["channel-789"] = [{
            "peer_id": "peer-1",
            "channel_id": "channel-789",
            "invited_by": "test-user-123",
            "invited_at": datetime.now(UTC).isoformat(),
            "status": "pending"
        }]

        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invite",
                json={"channel_id": "channel-789", "peer_ids": ["peer-1"]}
            )

        assert response.status_code == 200
        # Returns existing invitation
        assert response.json()["total"] == 1

    def test_invite_channel_not_found(self, client, mock_p2p_service):
        """Test inviting to nonexistent channel"""
        mock_p2p_service.get_channel = AsyncMock(return_value=None)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/nonexistent/invite",
                json={"channel_id": "nonexistent", "peer_ids": ["peer-1"]}
            )

        assert response.status_code == 404

    def test_list_invitations_admin(self, client, mock_p2p_service):
        """Test listing invitations as admin"""
        channel_invitations["channel-789"] = [
            {"peer_id": "peer-1", "invited_by": "other-user", "status": "pending"},
            {"peer_id": "peer-2", "invited_by": "test-user-123", "status": "pending"}
        ]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/channel-789/invitations")

        assert response.status_code == 200
        # Admin sees all invitations
        assert response.json()["total"] == 2

    def test_list_invitations_with_status_filter(self, client, mock_p2p_service):
        """Test listing invitations with status filter"""
        channel_invitations["channel-789"] = [
            {"peer_id": "peer-1", "invited_by": "test-user-123", "status": "pending"},
            {"peer_id": "peer-2", "invited_by": "test-user-123", "status": "accepted"}
        ]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get(
                "/api/v1/team/channels/channel-789/invitations",
                params={"status": "pending"}
            )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_accept_invitation_success(self, client, mock_p2p_service, mock_current_user):
        """Test accepting invitation"""
        channel_invitations["channel-789"] = [{
            "peer_id": "test-user-123",
            "channel_id": "channel-789",
            "invited_by": "other-user",
            "status": "pending"
        }]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invitations/test-user-123/accept"
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert channel_invitations["channel-789"][0]["status"] == "accepted"

    def test_accept_invitation_wrong_user(self, client, mock_p2p_service):
        """Test accepting invitation for another user"""
        channel_invitations["channel-789"] = [{
            "peer_id": "other-user",
            "status": "pending"
        }]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invitations/other-user/accept"
            )

        assert response.status_code == 403
        assert "Cannot accept invitation for another user" in response.json()["detail"]

    def test_accept_invitation_not_found(self, client, mock_p2p_service):
        """Test accepting nonexistent invitation"""
        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invitations/test-user-123/accept"
            )

        assert response.status_code == 404

    def test_decline_invitation_success(self, client, mock_p2p_service):
        """Test declining invitation"""
        channel_invitations["channel-789"] = [{
            "peer_id": "test-user-123",
            "status": "pending"
        }]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invitations/test-user-123/decline"
            )

        assert response.status_code == 200
        assert response.json()["status"] == "declined"

    def test_decline_invitation_wrong_user(self, client, mock_p2p_service):
        """Test declining invitation for another user"""
        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invitations/other-user/decline"
            )

        assert response.status_code == 403


# ========== Message Endpoint Tests ==========

class TestMessageEndpoints:
    """Tests for message endpoints"""

    def test_send_message_success(self, client, mock_p2p_service, sample_message):
        """Test successful message sending"""
        mock_p2p_service.send_message = AsyncMock(return_value=sample_message)

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.messages_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    "/api/v1/team/channels/channel-789/messages",
                    json={"channel_id": "channel-789", "content": "Hello!"}
                )

        assert response.status_code == 200
        assert response.json()["content"] == "Hello, world!"

    def test_send_message_service_not_running(self, client, mock_p2p_service):
        """Test sending message when service not running"""
        mock_p2p_service.is_running = False

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/messages",
                json={"channel_id": "channel-789", "content": "Hello!"}
            )

        assert response.status_code == 503

    def test_send_message_failure(self, client, mock_p2p_service):
        """Test message sending failure"""
        mock_p2p_service.send_message = AsyncMock(side_effect=Exception("Send failed"))

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/messages",
                json={"channel_id": "channel-789", "content": "Hello!"}
            )

        assert response.status_code == 500

    def test_get_messages_success(self, client, mock_p2p_service, sample_channel, sample_message):
        """Test successful message retrieval"""
        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)
        mock_p2p_service.get_messages = AsyncMock(return_value=[sample_message])

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/channel-789/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["channel_id"] == "channel-789"
        assert not data["has_more"]

    def test_get_messages_channel_not_found(self, client, mock_p2p_service):
        """Test getting messages from nonexistent channel"""
        mock_p2p_service.get_channel = AsyncMock(return_value=None)

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/nonexistent/messages")

        assert response.status_code == 404

    def test_get_messages_with_limit(self, client, mock_p2p_service, sample_channel, sample_message):
        """Test getting messages with limit"""
        messages = [sample_message] * 50
        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)
        mock_p2p_service.get_messages = AsyncMock(return_value=messages)

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get(
                "/api/v1/team/channels/channel-789/messages",
                params={"limit": 50}
            )

        assert response.status_code == 200
        assert response.json()["has_more"] is True


# ========== Read Receipt Tests ==========

class TestReadReceipts:
    """Tests for read receipt endpoints"""

    def test_mark_message_read_new(self, client, mock_p2p_service):
        """Test marking message as read for first time"""
        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/messages/msg-001/read"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "marked_read"
        assert "read_at" in data
        assert "msg-001" in read_receipts

    def test_mark_message_read_already_read(self, client, mock_p2p_service):
        """Test marking message already marked read"""
        read_receipts["msg-001"] = [{
            "peer_id": "test-user-123",
            "read_at": "2024-01-01T00:00:00Z"
        }]

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/messages/msg-001/read"
            )

        assert response.status_code == 200
        assert response.json()["status"] == "already_read"

    def test_get_message_receipts(self, client, mock_p2p_service):
        """Test getting message receipts"""
        read_receipts["msg-001"] = [
            {"peer_id": "user-1", "read_at": "2024-01-01T00:00:00Z"},
            {"peer_id": "user-2", "read_at": "2024-01-01T00:01:00Z"}
        ]

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get(
                "/api/v1/team/channels/channel-789/messages/msg-001/receipts"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_reads"] == 2
        assert "user-1" in data["read_by"]
        assert "user-2" in data["read_by"]

    def test_get_message_receipts_empty(self, client, mock_p2p_service):
        """Test getting receipts for unread message"""
        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get(
                "/api/v1/team/channels/channel-789/messages/msg-001/receipts"
            )

        assert response.status_code == 200
        assert response.json()["total_reads"] == 0

    def test_get_channel_receipts(self, client, mock_p2p_service):
        """Test getting all receipts for a channel"""
        read_receipts["msg-001"] = [
            {"peer_id": "user-1", "channel_id": "channel-789", "read_at": "2024-01-01T00:00:00Z"}
        ]
        read_receipts["msg-002"] = [
            {"peer_id": "user-2", "channel_id": "channel-789", "read_at": "2024-01-01T00:01:00Z"}
        ]
        read_receipts["msg-003"] = [
            {"peer_id": "user-1", "channel_id": "other-channel", "read_at": "2024-01-01T00:02:00Z"}
        ]

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/channel-789/receipts")

        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 2
        assert "msg-001" in data["receipts_by_message"]
        assert "msg-002" in data["receipts_by_message"]
        assert "msg-003" not in data["receipts_by_message"]


# ========== E2E Encryption Tests ==========

class TestE2EEncryption:
    """Tests for E2E encryption endpoints"""

    def test_init_e2e_keys_success(self, client, mock_p2p_service):
        """Test successful E2E key initialization"""
        mock_p2p_service.init_device_keys = MagicMock(return_value={
            "public_key": "abc123",
            "fingerprint": "AA:BB:CC:DD"
        })

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/init",
                params={"device_id": "device-1", "passphrase": "secret123"}
            )

        assert response.status_code == 200
        assert "public_key" in response.json()
        assert "fingerprint" in response.json()

    def test_init_e2e_keys_service_none(self, client):
        """Test E2E init when service not initialized"""
        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=None):
            response = client.post(
                "/api/v1/team/e2e/init",
                params={"device_id": "device-1", "passphrase": "secret123"}
            )

        assert response.status_code == 503

    def test_init_e2e_keys_failure(self, client, mock_p2p_service):
        """Test E2E init failure"""
        mock_p2p_service.init_device_keys = MagicMock(side_effect=Exception("Key generation failed"))

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/init",
                params={"device_id": "device-1", "passphrase": "secret123"}
            )

        assert response.status_code == 500

    def test_store_peer_key_success(self, client, mock_p2p_service):
        """Test storing peer public key"""
        mock_p2p_service.store_peer_key = MagicMock(return_value={
            "safety_number": "123456789012",
            "fingerprint": "EE:FF:00:11"
        })

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/peers/peer-456/keys",
                params={
                    "public_key_hex": "deadbeef" * 8,  # 32 bytes
                    "verify_key_hex": "cafebabe" * 8
                }
            )

        assert response.status_code == 200
        assert "safety_number" in response.json()

    def test_store_peer_key_invalid_hex(self, client, mock_p2p_service):
        """Test storing peer key with invalid hex"""
        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/peers/peer-456/keys",
                params={
                    "public_key_hex": "not-valid-hex",
                    "verify_key_hex": "also-invalid"
                }
            )

        assert response.status_code == 400
        assert "Invalid key format" in response.json()["detail"]

    def test_verify_peer_success(self, client, mock_p2p_service):
        """Test verifying peer fingerprint"""
        mock_p2p_service.verify_peer_fingerprint = MagicMock(return_value=True)

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post("/api/v1/team/e2e/peers/peer-456/verify")

        assert response.status_code == 200
        assert response.json()["status"] == "verified"

    def test_get_safety_changes(self, client, mock_p2p_service):
        """Test getting safety number changes"""
        mock_p2p_service.get_unacknowledged_safety_changes = MagicMock(return_value=[
            {"change_id": 1, "peer_id": "peer-456", "old_fingerprint": "AA:BB", "new_fingerprint": "CC:DD"}
        ])

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/e2e/safety-changes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["changes"]) == 1

    def test_acknowledge_safety_change(self, client, mock_p2p_service):
        """Test acknowledging safety number change"""
        mock_p2p_service.acknowledge_safety_change = MagicMock(return_value=True)

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post("/api/v1/team/e2e/safety-changes/1/acknowledge")

        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"

    def test_export_identity(self, client, mock_p2p_service):
        """Test exporting identity for device linking"""
        mock_e2e_service = MagicMock()
        mock_e2e_service.export_identity_for_linking = MagicMock(return_value={
            "encrypted_bundle": "encrypted-data",
            "salt": "salt-hex",
            "nonce": "nonce-hex"
        })
        mock_p2p_service.e2e_service = mock_e2e_service

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/export",
                params={"passphrase": "secret123"}
            )

        assert response.status_code == 200
        assert "encrypted_bundle" in response.json()

    def test_import_identity(self, client, mock_p2p_service):
        """Test importing identity from another device"""
        mock_e2e_service = MagicMock()
        mock_e2e_service.import_identity_from_link = MagicMock(
            return_value=(b"\x00" * 32, b"\x11" * 32)
        )
        mock_e2e_service.format_fingerprint = MagicMock(return_value="AA:BB:CC:DD")
        mock_p2p_service.e2e_service = mock_e2e_service

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/import",
                params={
                    "encrypted_bundle": "encrypted-hex",
                    "salt": "salt-hex",
                    "nonce": "nonce-hex",
                    "passphrase": "secret123",
                    "new_device_id": "new-device-1"
                }
            )

        assert response.status_code == 200
        assert "public_key" in response.json()
        assert "fingerprint" in response.json()
        assert response.json()["device_id"] == "new-device-1"

    def test_import_identity_failure(self, client, mock_p2p_service):
        """Test identity import failure"""
        mock_e2e_service = MagicMock()
        mock_e2e_service.import_identity_from_link = MagicMock(
            side_effect=Exception("Decryption failed")
        )
        mock_p2p_service.e2e_service = mock_e2e_service

        with patch('api.p2p_chat.e2e_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/e2e/import",
                params={
                    "encrypted_bundle": "invalid",
                    "salt": "salt",
                    "nonce": "nonce",
                    "passphrase": "wrong",
                    "new_device_id": "device"
                }
            )

        assert response.status_code == 500


# ========== Broadcast Event Tests ==========

class TestBroadcastEvent:
    """Tests for broadcast_event function"""

    @pytest.mark.asyncio
    async def test_broadcast_to_connections(self):
        """Test broadcasting event to connected clients"""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        active_connections.extend([mock_ws1, mock_ws2])

        await broadcast_event({"type": "test", "data": "hello"})

        mock_ws1.send_json.assert_called_once_with({"type": "test", "data": "hello"})
        mock_ws2.send_json.assert_called_once_with({"type": "test", "data": "hello"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self):
        """Test that disconnected clients are removed"""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_json.side_effect = Exception("Connection closed")

        active_connections.extend([mock_ws1, mock_ws2])

        await broadcast_event({"type": "test"})

        # ws2 should be removed
        assert mock_ws1 in active_connections
        assert mock_ws2 not in active_connections

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        """Test broadcasting with no connections"""
        await broadcast_event({"type": "test"})
        # Should complete without error


# ========== Router Configuration Tests ==========

class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/team"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "Team Chat" in router.tags

    def test_router_has_expected_routes(self):
        """Test router has expected routes"""
        routes = [r.path for r in router.routes]

        # Check that key routes exist (may include path parameters)
        route_patterns = ["/initialize", "/status", "/peers", "/channels", "/dm", "/ws", "/e2e/init"]
        for pattern in route_patterns:
            found = any(pattern in route for route in routes)
            assert found, f"Route pattern '{pattern}' not found in {routes}"


# ========== Non-Admin User Tests ==========

class TestNonAdminUser:
    """Tests for non-admin user permissions"""

    def test_list_invitations_non_admin(self, mock_regular_user, mock_p2p_service):
        """Test non-admin sees only their invitations"""
        from api.auth_middleware import get_current_user

        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        client = TestClient(test_app)

        channel_invitations["channel-789"] = [
            {"peer_id": "regular-user-456", "invited_by": "other-user", "status": "pending"},
            {"peer_id": "another-user", "invited_by": "regular-user-456", "status": "pending"},
            {"peer_id": "third-user", "invited_by": "other-user", "status": "pending"}
        ]

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/channel-789/invitations")

        assert response.status_code == 200
        # Non-admin should only see invitations they received or sent
        assert response.json()["total"] == 2


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_channel_name(self, client, mock_p2p_service, sample_channel):
        """Test creating channel with unicode name"""
        sample_channel.name = "日本語チャンネル"
        mock_p2p_service.create_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.channels_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    "/api/v1/team/channels",
                    json={"name": "日本語チャンネル", "type": "public"}
                )

        assert response.status_code == 200
        assert "日本語チャンネル" in response.json()["name"]

    def test_unicode_message_content(self, client, mock_p2p_service, sample_message):
        """Test sending message with unicode content"""
        sample_message.content = "こんにちは! 🎉"
        mock_p2p_service.send_message = AsyncMock(return_value=sample_message)

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.messages_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    "/api/v1/team/channels/channel-789/messages",
                    json={"channel_id": "channel-789", "content": "こんにちは! 🎉"}
                )

        assert response.status_code == 200

    def test_whitespace_channel_id(self, client, mock_p2p_service):
        """Test with whitespace channel ID"""
        mock_p2p_service.get_channel = AsyncMock(return_value=None)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/channels/%20")

        # Should return 404 (channel not found)
        assert response.status_code == 404

    def test_special_characters_in_peer_id(self, client, mock_p2p_service, sample_peer):
        """Test peer ID with special characters"""
        from api.p2p_chat_models import PeerStatus
        special_peer = Peer(
            peer_id="peer:with/special@chars",
            display_name="Test",
            device_name="Device",
            public_key="specialpubkey123",
            status=PeerStatus.ONLINE,
            last_seen=datetime.now(UTC).isoformat()
        )
        mock_p2p_service.list_peers = AsyncMock(return_value=[special_peer])

        with patch('api.p2p_chat.status_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get("/api/v1/team/peers")

        assert response.status_code == 200
        assert response.json()["total"] == 1


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_full_channel_lifecycle(self, client, mock_p2p_service, sample_channel, sample_message):
        """Test complete channel lifecycle"""
        # Create channel
        mock_p2p_service.create_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.channels_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    "/api/v1/team/channels",
                    json={"name": "Test Channel", "type": "public"}
                )

        assert response.status_code == 200
        channel_id = response.json()["id"]

        # Get channel
        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)

        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.get(f"/api/v1/team/channels/{channel_id}")

        assert response.status_code == 200

        # Send message
        mock_p2p_service.send_message = AsyncMock(return_value=sample_message)

        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            with patch('api.p2p_chat.messages_routes.broadcast_event', new_callable=AsyncMock):
                response = client.post(
                    f"/api/v1/team/channels/{channel_id}/messages",
                    json={"channel_id": channel_id, "content": "Hello!"}
                )

        assert response.status_code == 200
        message_id = response.json()["id"]

        # Mark as read
        with patch('api.p2p_chat.messages_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                f"/api/v1/team/channels/{channel_id}/messages/{message_id}/read"
            )

        assert response.status_code == 200

    def test_invitation_workflow(self, client, mock_p2p_service, sample_channel):
        """Test complete invitation workflow"""
        from api.auth_middleware import get_current_user

        # Create app with user that will receive invitation
        test_app = FastAPI()
        test_app.include_router(router)
        invitee_user = {"user_id": "invitee-123", "username": "invitee", "role": "member"}
        test_app.dependency_overrides[get_current_user] = lambda: invitee_user
        invitee_client = TestClient(test_app)

        mock_p2p_service.get_channel = AsyncMock(return_value=sample_channel)

        # Create invitation (as admin)
        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = client.post(
                "/api/v1/team/channels/channel-789/invite",
                json={"channel_id": "channel-789", "peer_ids": ["invitee-123"]}
            )

        assert response.status_code == 200

        # Accept invitation (as invitee)
        with patch('api.p2p_chat.channels_routes.get_p2p_chat_service', return_value=mock_p2p_service):
            response = invitee_client.post(
                "/api/v1/team/channels/channel-789/invitations/invitee-123/accept"
            )

        assert response.status_code == 200
        assert channel_invitations["channel-789"][0]["status"] == "accepted"
