"""
Comprehensive tests for api/routes/team/permissions.py

Tests team permissions router covering:
- User permissions (feature access)
- Workflow permissions (add, remove, get, check)
- Queue CRUD + permissions
- God Rights (grant, revoke, check, list)
- Vault item permissions

Coverage targets: 90%+ for FastAPI router endpoints
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import uuid

from api.routes.team.permissions import router


# ========== Fixtures ==========

@pytest.fixture
def app():
    """Create test FastAPI app with router"""
    app = FastAPI()
    app.include_router(router, prefix="/api/teams")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_team_manager():
    """Create mock TeamManager"""
    return MagicMock()


@pytest.fixture
def sample_team_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_workflow_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_queue_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_item_id():
    return str(uuid.uuid4())


# ========== User Permissions Tests ==========

class TestUserPermissions:
    """Tests for user permissions endpoint"""

    def test_get_user_permissions_success(self, client):
        """Test successful user permissions retrieval"""
        response = client.get("/api/teams/user/permissions")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["can_access_documents"] is True
        assert data["data"]["can_access_automation"] is True
        assert data["data"]["can_access_vault"] is True

    def test_get_user_permissions_returns_all_true(self, client):
        """Test that all permissions are returned as true (default behavior)"""
        response = client.get("/api/teams/user/permissions")

        assert response.status_code == 200
        data = response.json()["data"]

        # All permissions should be true by default
        for key in data:
            assert data[key] is True


# ========== Workflow Permissions Tests ==========

class TestWorkflowPermissions:
    """Tests for workflow permissions endpoints"""

    def test_add_workflow_permission_success(self, client, sample_team_id, sample_workflow_id):
        """Test adding workflow permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_workflow_permission = AsyncMock(return_value=(True, "Permission added"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                json={
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 201
            assert response.json()["success"] is True

    def test_add_workflow_permission_failure(self, client, sample_team_id, sample_workflow_id):
        """Test adding workflow permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_workflow_permission = AsyncMock(return_value=(False, "Permission denied"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                json={
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 400

    def test_add_workflow_permission_server_error(self, client, sample_team_id, sample_workflow_id):
        """Test server error during add workflow permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_get_tm.side_effect = Exception("Database error")

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                json={
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 500

    def test_remove_workflow_permission_success(self, client, sample_team_id, sample_workflow_id):
        """Test removing workflow permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_workflow_permission = AsyncMock(return_value=(True, "Permission removed"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                content=json.dumps({
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_remove_workflow_permission_failure(self, client, sample_team_id, sample_workflow_id):
        """Test removing workflow permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_workflow_permission = AsyncMock(return_value=(False, "Permission not found"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                content=json.dumps({
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 400

    def test_get_workflow_permissions_success(self, client, sample_team_id, sample_workflow_id):
        """Test getting workflow permissions"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_workflow_permissions = AsyncMock(return_value=[
                {"permission_type": "execute", "grant_type": "user", "grant_value": "user123"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["workflow_id"] == sample_workflow_id
            assert data["data"]["team_id"] == sample_team_id
            assert len(data["data"]["permissions"]) == 1

    def test_get_workflow_permissions_server_error(self, client, sample_team_id, sample_workflow_id):
        """Test server error during get workflow permissions"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_workflow_permissions = AsyncMock(side_effect=Exception("Database error"))
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions"
            )

            assert response.status_code == 500

    def test_check_workflow_permission_success(self, client, sample_team_id, sample_workflow_id):
        """Test checking workflow permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_workflow_permission = AsyncMock(return_value=(True, "Permission granted"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "execute"
                }
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_permission"] is True

    def test_check_workflow_permission_denied(self, client, sample_team_id, sample_workflow_id):
        """Test checking workflow permission when denied"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_workflow_permission = AsyncMock(return_value=(False, "Permission denied"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "execute"
                }
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_permission"] is False


# ========== Queue Tests ==========

class TestQueueEndpoints:
    """Tests for queue CRUD endpoints"""

    def test_create_queue_success(self, client, sample_team_id):
        """Test creating a queue"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            queue_id = str(uuid.uuid4())
            mock_tm = MagicMock()
            mock_tm.create_queue = AsyncMock(return_value=(True, "Queue created", queue_id))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues",
                json={
                    "queue_name": "Test Queue",
                    "queue_type": "task",
                    "description": "Test description",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 201
            assert response.json()["data"]["queue_id"] == queue_id

    def test_create_queue_failure(self, client, sample_team_id):
        """Test creating a queue failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.create_queue = AsyncMock(return_value=(False, "Queue already exists", None))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues",
                json={
                    "queue_name": "Test Queue",
                    "queue_type": "task",
                    "description": "Test description",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 400

    def test_get_queue_success(self, client, sample_team_id, sample_queue_id):
        """Test getting queue details"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_queue = AsyncMock(return_value={
                "queue_id": sample_queue_id,
                "queue_name": "Test Queue",
                "queue_type": "task"
            })
            mock_get_tm.return_value = mock_tm

            response = client.get(f"/api/teams/{sample_team_id}/queues/{sample_queue_id}")

            assert response.status_code == 200
            assert response.json()["data"]["queue_id"] == sample_queue_id

    def test_get_queue_not_found(self, client, sample_team_id, sample_queue_id):
        """Test getting non-existent queue"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_queue = AsyncMock(return_value=None)
            mock_get_tm.return_value = mock_tm

            response = client.get(f"/api/teams/{sample_team_id}/queues/{sample_queue_id}")

            assert response.status_code == 404


class TestQueuePermissions:
    """Tests for queue permission endpoints"""

    def test_add_queue_permission_success(self, client, sample_team_id, sample_queue_id):
        """Test adding queue permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_queue_permission = AsyncMock(return_value=(True, "Permission added"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/permissions",
                json={
                    "access_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 201
            assert response.json()["success"] is True

    def test_add_queue_permission_failure(self, client, sample_team_id, sample_queue_id):
        """Test adding queue permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_queue_permission = AsyncMock(return_value=(False, "Queue not found"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/permissions",
                json={
                    "access_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 400

    def test_remove_queue_permission_success(self, client, sample_team_id, sample_queue_id):
        """Test removing queue permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_queue_permission = AsyncMock(return_value=(True, "Permission removed"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/permissions",
                content=json.dumps({
                    "access_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_remove_queue_permission_failure(self, client, sample_team_id, sample_queue_id):
        """Test removing queue permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_queue_permission = AsyncMock(return_value=(False, "Permission not found"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/permissions",
                content=json.dumps({
                    "access_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 400

    def test_get_queue_permissions_success(self, client, sample_team_id, sample_queue_id):
        """Test getting queue permissions"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_queue_permissions = AsyncMock(return_value=[
                {"access_type": "read", "grant_type": "user", "grant_value": "user123"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/permissions"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["queue_id"] == sample_queue_id
            assert len(data["data"]["permissions"]) == 1

    def test_check_queue_access_has_access(self, client, sample_team_id, sample_queue_id):
        """Test checking queue access when user has access"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_queue_access = AsyncMock(return_value=(True, "Access granted"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/check-access",
                json={
                    "user_id": "user123",
                    "access_type": "read"
                }
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_access"] is True

    def test_check_queue_access_no_access(self, client, sample_team_id, sample_queue_id):
        """Test checking queue access when user has no access"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_queue_access = AsyncMock(return_value=(False, "Access denied"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/queues/{sample_queue_id}/check-access",
                json={
                    "user_id": "user123",
                    "access_type": "write"
                }
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_access"] is False

    def test_get_accessible_queues_success(self, client, sample_team_id, sample_user_id):
        """Test getting accessible queues for a user"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_accessible_queues = AsyncMock(return_value=[
                {"queue_id": "q1", "queue_name": "Queue 1"},
                {"queue_id": "q2", "queue_name": "Queue 2"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/queues/accessible/{sample_user_id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["count"] == 2
            assert len(data["data"]["queues"]) == 2


# ========== God Rights Tests ==========

class TestGodRights:
    """Tests for god rights endpoints"""

    def test_grant_god_rights_success(self, client, sample_user_id):
        """Test granting god rights"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.grant_god_rights = AsyncMock(return_value=(True, "God rights granted"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/grant",
                json={
                    "user_id": sample_user_id,
                    "delegated_by": "admin123",
                    "auth_key": "secret_auth_key"
                }
            )

            assert response.status_code == 201
            assert response.json()["success"] is True

    def test_grant_god_rights_failure(self, client, sample_user_id):
        """Test granting god rights failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.grant_god_rights = AsyncMock(return_value=(False, "Invalid auth key"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/grant",
                json={
                    "user_id": sample_user_id,
                    "delegated_by": "admin123",
                    "auth_key": "wrong_key"
                }
            )

            assert response.status_code == 400

    def test_grant_god_rights_server_error(self, client, sample_user_id):
        """Test server error during grant god rights"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_get_tm.side_effect = Exception("Database error")

            response = client.post(
                "/api/teams/god-rights/grant",
                json={
                    "user_id": sample_user_id,
                    "delegated_by": "admin123",
                    "auth_key": "secret_auth_key"
                }
            )

            assert response.status_code == 500

    def test_revoke_god_rights_success(self, client, sample_user_id):
        """Test revoking god rights"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.revoke_god_rights = AsyncMock(return_value=(True, "God rights revoked"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/revoke",
                json={
                    "user_id": sample_user_id,
                    "revoked_by": "admin123"
                }
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_revoke_god_rights_failure(self, client, sample_user_id):
        """Test revoking god rights failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.revoke_god_rights = AsyncMock(return_value=(False, "User has no god rights"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/revoke",
                json={
                    "user_id": sample_user_id,
                    "revoked_by": "admin123"
                }
            )

            assert response.status_code == 400

    def test_check_god_rights_has_rights(self, client, sample_user_id):
        """Test checking god rights when user has them"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_god_rights = AsyncMock(return_value=(True, "User has god rights"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/check",
                json={"user_id": sample_user_id}
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_god_rights"] is True

    def test_check_god_rights_no_rights(self, client, sample_user_id):
        """Test checking god rights when user doesn't have them"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_god_rights = AsyncMock(return_value=(False, "User has no god rights"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/check",
                json={"user_id": sample_user_id}
            )

            assert response.status_code == 200
            assert response.json()["data"]["has_god_rights"] is False

    def test_get_god_rights_users_success(self, client):
        """Test getting all god rights users"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_god_rights_users = AsyncMock(return_value=[
                {"user_id": "user1", "delegated_by": "admin1"},
                {"user_id": "user2", "delegated_by": "admin2"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get("/api/teams/god-rights/users")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["count"] == 2
            assert len(data["data"]["users"]) == 2

    def test_get_god_rights_users_empty(self, client):
        """Test getting god rights users when none exist"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_god_rights_users = AsyncMock(return_value=[])
            mock_get_tm.return_value = mock_tm

            response = client.get("/api/teams/god-rights/users")

            assert response.status_code == 200
            assert response.json()["data"]["count"] == 0

    def test_get_revoked_god_rights_success(self, client):
        """Test getting revoked god rights"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_revoked_god_rights = AsyncMock(return_value=[
                {"user_id": "user1", "revoked_by": "admin1"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get("/api/teams/god-rights/revoked")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["count"] == 1


# ========== Vault Permissions Tests ==========

class TestVaultPermissions:
    """Tests for vault permissions endpoints"""

    def test_add_vault_permission_success(self, client, sample_team_id, sample_item_id):
        """Test adding vault permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_vault_permission = AsyncMock(return_value=(True, "Permission added"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions",
                json={
                    "permission_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 201
            assert response.json()["success"] is True

    def test_add_vault_permission_failure(self, client, sample_team_id, sample_item_id):
        """Test adding vault permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_vault_permission = AsyncMock(return_value=(False, "Item not found"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions",
                json={
                    "permission_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 400

    def test_add_vault_permission_server_error(self, client, sample_team_id, sample_item_id):
        """Test server error during add vault permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_get_tm.side_effect = Exception("Database error")

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions",
                json={
                    "permission_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 500

    def test_remove_vault_permission_success(self, client, sample_team_id, sample_item_id):
        """Test removing vault permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_vault_permission = AsyncMock(return_value=(True, "Permission removed"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions",
                content=json.dumps({
                    "permission_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_remove_vault_permission_failure(self, client, sample_team_id, sample_item_id):
        """Test removing vault permission failure"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.remove_vault_permission = AsyncMock(return_value=(False, "Permission not found"))
            mock_get_tm.return_value = mock_tm

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions",
                content=json.dumps({
                    "permission_type": "read",
                    "grant_type": "user",
                    "grant_value": "user123"
                }),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 400

    def test_get_vault_permissions_success(self, client, sample_team_id, sample_item_id):
        """Test getting vault permissions"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_vault_permissions = AsyncMock(return_value=[
                {"permission_type": "read", "grant_type": "user", "grant_value": "user123"}
            ])
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["item_id"] == sample_item_id
            assert data["data"]["team_id"] == sample_team_id
            assert len(data["data"]["permissions"]) == 1

    def test_get_vault_permissions_server_error(self, client, sample_team_id, sample_item_id):
        """Test server error during get vault permissions"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_vault_permissions = AsyncMock(side_effect=Exception("Database error"))
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/permissions"
            )

            assert response.status_code == 500

    def test_check_vault_permission_has_permission(self, client, sample_team_id, sample_item_id):
        """Test checking vault permission when user has it"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_vault_permission = AsyncMock(return_value=(True, "Permission granted"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "read"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["has_permission"] is True
            assert data["data"]["reason"] == "Permission granted"

    def test_check_vault_permission_no_permission(self, client, sample_team_id, sample_item_id):
        """Test checking vault permission when user doesn't have it"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_vault_permission = AsyncMock(return_value=(False, "No matching permission"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "write"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["has_permission"] is False
            assert data["data"]["reason"] == "No matching permission"

    def test_check_vault_permission_server_error(self, client, sample_team_id, sample_item_id):
        """Test server error during check vault permission"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.check_vault_permission = AsyncMock(side_effect=Exception("Database error"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/vault/items/{sample_item_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "read"
                }
            )

            assert response.status_code == 500


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_in_team_id(self, client):
        """Test handling unicode in team_id path parameter"""
        # This should still work - FastAPI handles URL encoding
        team_id = "team-日本語"
        workflow_id = str(uuid.uuid4())

        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_workflow_permissions = AsyncMock(return_value=[])
            mock_get_tm.return_value = mock_tm

            response = client.get(f"/api/teams/{team_id}/workflows/{workflow_id}/permissions")

            assert response.status_code == 200

    def test_empty_permissions_list(self, client, sample_team_id, sample_workflow_id):
        """Test handling empty permissions list"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_workflow_permissions = AsyncMock(return_value=[])
            mock_get_tm.return_value = mock_tm

            response = client.get(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions"
            )

            assert response.status_code == 200
            assert response.json()["data"]["permissions"] == []

    def test_very_long_grant_value(self, client, sample_team_id, sample_workflow_id):
        """Test handling very long grant_value"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.add_workflow_permission = AsyncMock(return_value=(True, "Permission added"))
            mock_get_tm.return_value = mock_tm

            long_value = "x" * 1000  # Very long grant value
            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                json={
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": long_value,
                    "created_by": "test_user"
                }
            )

            assert response.status_code == 201


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for permission flows"""

    def test_workflow_permission_lifecycle(self, client, sample_team_id, sample_workflow_id):
        """Test full workflow permission lifecycle"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()

            # Add permission
            mock_tm.add_workflow_permission = AsyncMock(return_value=(True, "Permission added"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                json={
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }
            )
            assert response.status_code == 201

            # Check permission
            mock_tm.check_workflow_permission = AsyncMock(return_value=(True, "Permission granted"))

            response = client.post(
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/check-permission",
                json={
                    "user_id": "user123",
                    "permission_type": "execute"
                }
            )
            assert response.status_code == 200
            assert response.json()["data"]["has_permission"] is True

            # Remove permission
            mock_tm.remove_workflow_permission = AsyncMock(return_value=(True, "Permission removed"))

            response = client.request(
                "DELETE",
                f"/api/teams/{sample_team_id}/workflows/{sample_workflow_id}/permissions",
                content=json.dumps({
                    "permission_type": "execute",
                    "grant_type": "user",
                    "grant_value": "user123",
                    "created_by": "test_user"
                }),
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200

    def test_god_rights_lifecycle(self, client, sample_user_id):
        """Test full god rights lifecycle"""
        with patch('api.services.team.get_team_manager') as mock_get_tm:
            mock_tm = MagicMock()

            # Grant god rights
            mock_tm.grant_god_rights = AsyncMock(return_value=(True, "God rights granted"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/api/teams/god-rights/grant",
                json={
                    "user_id": sample_user_id,
                    "delegated_by": "admin123",
                    "auth_key": "secret"
                }
            )
            assert response.status_code == 201

            # Check god rights
            mock_tm.check_god_rights = AsyncMock(return_value=(True, "User has god rights"))

            response = client.post(
                "/api/teams/god-rights/check",
                json={"user_id": sample_user_id}
            )
            assert response.status_code == 200
            assert response.json()["data"]["has_god_rights"] is True

            # Revoke god rights
            mock_tm.revoke_god_rights = AsyncMock(return_value=(True, "God rights revoked"))

            response = client.post(
                "/api/teams/god-rights/revoke",
                json={
                    "user_id": sample_user_id,
                    "revoked_by": "admin123"
                }
            )
            assert response.status_code == 200

            # Verify in revoked list
            mock_tm.get_revoked_god_rights = AsyncMock(return_value=[
                {"user_id": sample_user_id, "revoked_by": "admin123"}
            ])

            response = client.get("/api/teams/god-rights/revoked")
            assert response.status_code == 200
            assert response.json()["data"]["count"] == 1
