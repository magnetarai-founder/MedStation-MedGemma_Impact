"""
Tests for MagnetarCloud Sync Service

Tests cover:
- Sync status endpoint
- Vault sync (upload/download/bidirectional)
- Workflow sync
- Team sync
- Conflict detection and resolution
- Sync trigger
- Air-gap mode blocking
"""

import pytest
import json
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, UTC
from fastapi import status
from fastapi.testclient import TestClient

import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))


# ===== Test Fixtures =====

@pytest.fixture
def mock_user():
    """Create a mock authenticated user dict"""
    return {
        "user_id": "test-user-sync-123",
        "username": "syncuser",
        "device_id": "test-device-sync-456",
        "created_at": "2024-12-01T00:00:00"
    }


@pytest.fixture
def test_client(mock_user, tmp_path):
    """Create a test client with mocked authentication"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    test_db_path = tmp_path / "test_sync.db"

    # Must patch before importing the router to affect initialization
    with patch('api.routes.cloud_sync.SYNC_DB_PATH', test_db_path):
        # Re-import to get fresh module with patched path
        import importlib
        import api.routes.cloud_sync as cloud_sync_module
        importlib.reload(cloud_sync_module)

        app = FastAPI()
        app.include_router(cloud_sync_module.router)

        # Override authentication to return dict
        app.dependency_overrides[get_current_user] = lambda: mock_user

        yield TestClient(app)


@pytest.fixture
def test_client_airgap(mock_user, tmp_path):
    """Create a test client with air-gap mode enabled"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    test_db_path = tmp_path / "test_sync_airgap.db"

    # Patch is_airgap_mode in api.config BEFORE importing the cloud_sync module
    with patch('api.config.is_airgap_mode', return_value=True):
        with patch('api.routes.cloud_sync.SYNC_DB_PATH', test_db_path):
            # Re-import to get fresh module with patched path and airgap mode
            import importlib
            import api.routes.cloud_sync as cloud_sync_module
            importlib.reload(cloud_sync_module)

            app = FastAPI()
            app.include_router(cloud_sync_module.router)
            app.dependency_overrides[get_current_user] = lambda: mock_user

            yield TestClient(app)


# ===== Sync Status Tests =====

class TestSyncStatus:
    """Tests for sync status endpoint"""

    def test_get_sync_status_success(self, test_client, mock_user):
        """Should return sync status for user"""
        response = test_client.get(
            f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "is_syncing" in data["data"]
        assert "pending_uploads" in data["data"]
        assert "pending_downloads" in data["data"]
        assert "conflicts" in data["data"]
        assert "sync_enabled" in data["data"]

    def test_get_sync_status_has_required_fields(self, test_client, mock_user):
        """Sync status should have all required fields with correct types"""
        response = test_client.get(
            f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}"
        )

        data = response.json()["data"]
        assert isinstance(data["is_syncing"], bool)
        assert isinstance(data["pending_uploads"], int)
        assert isinstance(data["pending_downloads"], int)
        assert isinstance(data["conflicts"], int)
        assert isinstance(data["sync_enabled"], bool)

    def test_get_sync_status_requires_user_id(self, test_client):
        """Should require user_id parameter"""
        response = test_client.get("/api/v1/cloud/sync/status")
        assert response.status_code == 422  # Validation error

    def test_sync_status_blocked_in_airgap(self, test_client_airgap, mock_user):
        """Should return 503 in air-gap mode"""
        response = test_client_airgap.get(
            f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}"
        )
        assert response.status_code == 503


# ===== Vault Sync Tests =====

class TestVaultSync:
    """Tests for vault synchronization"""

    def test_vault_sync_empty_changes(self, test_client, mock_user):
        """Should handle sync with no local changes"""
        response = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "local_changes": [],
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "remote_changes" in data["data"]
        assert "conflicts" in data["data"]
        assert data["data"]["conflicts"] == []

    def test_vault_sync_upload_changes(self, test_client, mock_user):
        """Should accept local changes for upload"""
        response = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "local_changes": [
                    {
                        "resource_id": "file-001",
                        "resource_type": "file",
                        "operation": "create",
                        "data": {"name": "test.txt", "content": "hello"},
                        "modified_at": "2025-12-27T12:00:00Z",
                        "version": 1
                    }
                ],
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["new_sync_version"] >= 1

    def test_vault_sync_multiple_changes(self, test_client, mock_user):
        """Should handle multiple changes in single sync"""
        changes = [
            {
                "resource_id": f"file-{i}",
                "resource_type": "file",
                "operation": "create",
                "data": {"name": f"file{i}.txt"},
                "modified_at": "2025-12-27T12:00:00Z",
                "version": 1
            }
            for i in range(5)
        ]

        response = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "local_changes": changes,
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_vault_sync_requires_local_changes(self, test_client, mock_user):
        """Should require local_changes field"""
        response = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "last_sync_version": 0
            }
        )
        assert response.status_code == 422

    def test_vault_sync_requires_last_sync_version(self, test_client, mock_user):
        """Should require last_sync_version field"""
        response = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "local_changes": []
            }
        )
        assert response.status_code == 422


# ===== Workflow Sync Tests =====

class TestWorkflowSync:
    """Tests for workflow synchronization"""

    def test_workflow_sync_empty(self, test_client, mock_user):
        """Should handle empty workflow sync"""
        response = test_client.post(
            f"/api/v1/cloud/sync/workflows?user_id={mock_user['user_id']}",
            json={
                "local_changes": [],
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_workflow_sync_upload(self, test_client, mock_user):
        """Should sync workflow changes"""
        response = test_client.post(
            f"/api/v1/cloud/sync/workflows?user_id={mock_user['user_id']}",
            json={
                "local_changes": [
                    {
                        "resource_id": "workflow-001",
                        "resource_type": "workflow",
                        "operation": "create",
                        "data": {"name": "My Workflow", "steps": []},
                        "modified_at": "2025-12-27T12:00:00Z",
                        "version": 1
                    }
                ],
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200


# ===== Team Sync Tests =====

class TestTeamSync:
    """Tests for team synchronization"""

    def test_team_sync_empty(self, test_client, mock_user):
        """Should handle empty team sync"""
        response = test_client.post(
            f"/api/v1/cloud/sync/teams?user_id={mock_user['user_id']}",
            json={
                "local_changes": [],
                "last_sync_version": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ===== Conflict Tests =====

class TestConflicts:
    """Tests for conflict detection and resolution"""

    def test_get_conflicts_returns_list(self, test_client, mock_user):
        """Should return a list of conflicts (may be empty or populated)"""
        response = test_client.get(
            f"/api/v1/cloud/sync/conflicts?user_id={mock_user['user_id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # data["data"] is directly a list of conflicts
        assert isinstance(data["data"], list)
        # Each conflict should have the right structure if present
        for conflict in data["data"]:
            assert "conflict_id" in conflict
            assert "resource_type" in conflict
            assert "resource_id" in conflict

    def test_resolve_conflict_not_found(self, test_client, mock_user):
        """Should return 404 for non-existent conflict"""
        response = test_client.post(
            f"/api/v1/cloud/sync/conflicts/nonexistent-id/resolve?user_id={mock_user['user_id']}",
            json={"resolution": "local_wins"}
        )

        assert response.status_code == 404

    def test_resolve_conflict_invalid_resolution(self, test_client, mock_user):
        """Should reject invalid resolution strategy"""
        response = test_client.post(
            f"/api/v1/cloud/sync/conflicts/some-id/resolve?user_id={mock_user['user_id']}",
            json={"resolution": "invalid_strategy"}
        )

        assert response.status_code == 422


# ===== Sync Trigger Tests =====

class TestSyncTrigger:
    """Tests for manual sync trigger"""

    def test_trigger_sync_all_resources(self, test_client, mock_user):
        """Should trigger sync for all resources"""
        response = test_client.post(
            f"/api/v1/cloud/sync/trigger?user_id={mock_user['user_id']}",
            json={"direction": "bidirectional"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_trigger_sync_specific_resources(self, test_client, mock_user):
        """Should trigger sync for specific resources"""
        response = test_client.post(
            f"/api/v1/cloud/sync/trigger?user_id={mock_user['user_id']}",
            json={
                "direction": "upload",
                "resources": ["vault", "workflows"]
            }
        )

        assert response.status_code == 200

    def test_trigger_sync_download_only(self, test_client, mock_user):
        """Should support download-only sync"""
        response = test_client.post(
            f"/api/v1/cloud/sync/trigger?user_id={mock_user['user_id']}",
            json={"direction": "download"}
        )

        assert response.status_code == 200


# ===== Air-Gap Mode Tests =====

class TestAirGapMode:
    """Tests for air-gap mode blocking"""

    def test_sync_blocked_in_airgap(self, test_client_airgap, mock_user):
        """All sync operations should be blocked in air-gap mode"""
        endpoints = [
            ("GET", f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}", None),
            ("POST", f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
             {"local_changes": [], "last_sync_version": 0}),
            ("POST", f"/api/v1/cloud/sync/workflows?user_id={mock_user['user_id']}",
             {"local_changes": [], "last_sync_version": 0}),
            ("POST", f"/api/v1/cloud/sync/trigger?user_id={mock_user['user_id']}",
             {"direction": "bidirectional"}),
        ]

        for method, url, body in endpoints:
            if method == "GET":
                response = test_client_airgap.get(url)
            else:
                response = test_client_airgap.post(url, json=body)

            assert response.status_code == 503, f"Expected 503 for {method} {url}"


# ===== Integration Tests =====

class TestSyncIntegration:
    """Integration tests for complete sync workflows"""

    def test_full_sync_cycle(self, test_client, mock_user):
        """Test complete sync cycle: status -> sync -> status"""
        # 1. Get initial status
        status_resp = test_client.get(
            f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}"
        )
        assert status_resp.status_code == 200
        initial_status = status_resp.json()["data"]

        # 2. Sync some changes
        sync_resp = test_client.post(
            f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
            json={
                "local_changes": [
                    {
                        "resource_id": "integration-test-file",
                        "resource_type": "file",
                        "operation": "create",
                        "data": {"name": "integration.txt"},
                        "modified_at": "2025-12-27T12:00:00Z",
                        "version": 1
                    }
                ],
                "last_sync_version": 0
            }
        )
        assert sync_resp.status_code == 200

        # 3. Check updated status
        final_status_resp = test_client.get(
            f"/api/v1/cloud/sync/status?user_id={mock_user['user_id']}"
        )
        assert final_status_resp.status_code == 200
        final_status = final_status_resp.json()["data"]

        # last_sync_at should be updated
        assert final_status["last_sync_at"] is not None

    def test_sync_version_increments(self, test_client, mock_user):
        """Sync version should increment with each sync"""
        versions = []

        for i in range(3):
            response = test_client.post(
                f"/api/v1/cloud/sync/vault?user_id={mock_user['user_id']}",
                json={
                    "local_changes": [
                        {
                            "resource_id": f"version-test-{i}",
                            "resource_type": "file",
                            "operation": "create",
                            "data": {"name": f"v{i}.txt"},
                            "modified_at": "2025-12-27T12:00:00Z",
                            "version": 1
                        }
                    ],
                    "last_sync_version": versions[-1] if versions else 0
                }
            )

            assert response.status_code == 200
            new_version = response.json()["data"]["new_sync_version"]
            versions.append(new_version)

        # Versions should be increasing
        assert versions[0] < versions[1] < versions[2]
