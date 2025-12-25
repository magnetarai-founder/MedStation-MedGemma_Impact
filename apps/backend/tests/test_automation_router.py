"""
Tests for Automation Router

Tests REST API endpoints for automation workflow management.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.automation_router import router
from api.auth_middleware import get_current_user
from api.automation_storage import AutomationStorage, get_automation_storage


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {"user_id": "test_user_123", "email": "test@example.com"}


@pytest.fixture
def mock_storage(tmp_path):
    """Create mock storage with temp database"""
    return AutomationStorage(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def app(mock_user):
    """Create FastAPI app with automation router and mocked dependencies"""
    app = FastAPI()

    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    app.include_router(router)
    return app


@pytest.fixture
def client(app, mock_storage):
    """Create test client with patched storage"""
    with patch("api.automation_router.get_automation_storage", return_value=mock_storage):
        yield TestClient(app)


@pytest.fixture
def sample_workflow_request():
    """Sample workflow save request"""
    return {
        "workflow_id": "wf_test_123",
        "name": "Test Automation Workflow",
        "nodes": [
            {"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "label": "Start"},
            {"id": "n2", "type": "action", "position": {"x": 100, "y": 0}, "label": "Process"},
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }


@pytest.fixture
def sample_run_request():
    """Sample workflow run request"""
    return {
        "workflow_id": "wf_run_123",
        "name": "Run Test Workflow",
        "nodes": [
            {"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "label": "Trigger"},
            {"id": "n2", "type": "action", "position": {"x": 100, "y": 0}, "label": "Action"},
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }


class TestSaveWorkflow:
    """Test save workflow endpoint"""

    def test_save_workflow_success(self, client, sample_workflow_request):
        """Test saving a workflow"""
        response = client.post("/api/v1/automation/save", json=sample_workflow_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert data["workflow_id"] == "wf_test_123"
        assert "saved_at" in data

    def test_save_workflow_persists_to_storage(self, client, mock_storage, sample_workflow_request):
        """Test that workflow is actually persisted"""
        client.post("/api/v1/automation/save", json=sample_workflow_request)

        # Verify in storage
        workflow = mock_storage.get_workflow("wf_test_123", "test_user_123")
        assert workflow is not None
        assert workflow["name"] == "Test Automation Workflow"


class TestListWorkflows:
    """Test list workflows endpoint"""

    def test_list_workflows_empty(self, client):
        """Test listing workflows when none exist"""
        response = client.get("/api/v1/automation/workflows")

        assert response.status_code == 200
        data = response.json()
        assert data["workflows"] == []
        assert data["count"] == 0

    def test_list_workflows_returns_user_workflows(self, client, mock_storage):
        """Test listing workflows returns user's workflows"""
        # Pre-populate storage
        mock_storage.save_workflow(
            workflow_id="wf1", name="Workflow 1",
            nodes=[], edges=[], user_id="test_user_123"
        )
        mock_storage.save_workflow(
            workflow_id="wf2", name="Workflow 2",
            nodes=[], edges=[], user_id="test_user_123"
        )

        response = client.get("/api/v1/automation/workflows")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["workflows"]) == 2

    def test_list_workflows_pagination(self, client, mock_storage):
        """Test list workflows with pagination"""
        # Pre-populate
        for i in range(5):
            mock_storage.save_workflow(
                workflow_id=f"wf{i}", name=f"Workflow {i}",
                nodes=[], edges=[], user_id="test_user_123"
            )

        response = client.get("/api/v1/automation/workflows?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2


class TestGetWorkflow:
    """Test get workflow endpoint"""

    def test_get_workflow_success(self, client, mock_storage):
        """Test getting an existing workflow"""
        mock_storage.save_workflow(
            workflow_id="wf_get_test", name="Get Test",
            nodes=[{"id": "n1"}], edges=[], user_id="test_user_123"
        )

        response = client.get("/api/v1/automation/workflows/wf_get_test")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf_get_test"
        assert data["name"] == "Get Test"

    def test_get_workflow_not_found(self, client):
        """Test getting nonexistent workflow returns 404"""
        response = client.get("/api/v1/automation/workflows/nonexistent")

        assert response.status_code == 404

    def test_get_workflow_user_isolation(self, client, mock_storage):
        """Test user cannot access other user's workflow"""
        mock_storage.save_workflow(
            workflow_id="wf_other", name="Other User",
            nodes=[], edges=[], user_id="other_user"
        )

        response = client.get("/api/v1/automation/workflows/wf_other")

        assert response.status_code == 404


class TestDeleteWorkflow:
    """Test delete workflow endpoint"""

    def test_delete_workflow_success(self, client, mock_storage):
        """Test deleting an existing workflow"""
        mock_storage.save_workflow(
            workflow_id="wf_delete", name="To Delete",
            nodes=[], edges=[], user_id="test_user_123"
        )

        response = client.delete("/api/v1/automation/workflows/wf_delete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["workflow_id"] == "wf_delete"

        # Verify deleted
        assert mock_storage.get_workflow("wf_delete", "test_user_123") is None

    def test_delete_workflow_not_found(self, client):
        """Test deleting nonexistent workflow returns 404"""
        response = client.delete("/api/v1/automation/workflows/nonexistent")

        assert response.status_code == 404


class TestRunWorkflow:
    """Test run workflow endpoint"""

    def test_run_workflow_success(self, client, sample_run_request):
        """Test running a workflow"""
        response = client.post("/api/v1/automation/run", json=sample_run_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["workflow_id"] == "wf_run_123"
        assert data["workflow_name"] == "Run Test Workflow"
        assert data["steps_executed"] == 2
        assert "execution_time_ms" in data
        assert "results" in data

    def test_run_workflow_no_trigger_fails(self, client):
        """Test workflow with no trigger node fails"""
        request = {
            "workflow_id": "wf_no_trigger",
            "name": "No Trigger",
            "nodes": [
                {"id": "n1", "type": "action", "position": {"x": 0, "y": 0}, "label": "Action"}
            ],
            "edges": [
                {"source": "n2", "target": "n1"}  # n2 doesn't exist, so n1 has incoming edge
            ]
        }

        response = client.post("/api/v1/automation/run", json=request)

        assert response.status_code == 400
        assert "No trigger node" in response.json()["detail"]


class TestGetExecutions:
    """Test get execution history endpoint"""

    def test_get_executions_success(self, client, mock_storage):
        """Test getting execution history"""
        # Create workflow and record executions
        mock_storage.save_workflow(
            workflow_id="wf_exec", name="Exec Test",
            nodes=[], edges=[], user_id="test_user_123"
        )
        mock_storage.record_execution(
            workflow_id="wf_exec", user_id="test_user_123",
            status="completed", steps_executed=3, execution_time_ms=100
        )

        response = client.get("/api/v1/automation/workflows/wf_exec/executions")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "wf_exec"
        assert data["count"] == 1
        assert len(data["executions"]) == 1

    def test_get_executions_empty(self, client):
        """Test getting executions when none exist"""
        response = client.get("/api/v1/automation/workflows/wf_no_exec/executions")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
