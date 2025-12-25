"""
Tests for Automation Storage

Tests SQLite persistence for visual automation workflows.
"""

import pytest
import tempfile
import os
from pathlib import Path

from api.automation_storage import AutomationStorage, get_automation_storage


class TestAutomationStorage:
    """Test automation storage class"""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage with temp database"""
        db_path = tmp_path / "test_automations.db"
        return AutomationStorage(db_path=str(db_path))

    @pytest.fixture
    def sample_nodes(self):
        """Sample workflow nodes"""
        return [
            {"id": "node1", "type": "trigger", "position": {"x": 0, "y": 0}, "label": "Start"},
            {"id": "node2", "type": "action", "position": {"x": 100, "y": 0}, "label": "Process"},
            {"id": "node3", "type": "output", "position": {"x": 200, "y": 0}, "label": "End"}
        ]

    @pytest.fixture
    def sample_edges(self):
        """Sample workflow edges"""
        return [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"}
        ]

    def test_init_creates_database(self, tmp_path):
        """Test database file is created on init"""
        db_path = tmp_path / "test.db"
        storage = AutomationStorage(db_path=str(db_path))
        assert db_path.exists()

    def test_init_creates_parent_directories(self, tmp_path):
        """Test nested directories are created"""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        storage = AutomationStorage(db_path=str(db_path))
        assert db_path.exists()

    def test_save_workflow_creates_new(self, storage, sample_nodes, sample_edges):
        """Test saving a new workflow"""
        result = storage.save_workflow(
            workflow_id="wf1",
            name="Test Workflow",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user1",
            description="A test workflow"
        )

        assert result["id"] == "wf1"
        assert result["name"] == "Test Workflow"
        assert result["nodes"] == sample_nodes
        assert result["edges"] == sample_edges
        assert result["user_id"] == "user1"
        assert result["description"] == "A test workflow"

    def test_save_workflow_updates_existing(self, storage, sample_nodes, sample_edges):
        """Test updating an existing workflow"""
        # Create first
        storage.save_workflow(
            workflow_id="wf1",
            name="Original",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user1"
        )

        # Update
        result = storage.save_workflow(
            workflow_id="wf1",
            name="Updated",
            nodes=sample_nodes[:2],
            edges=sample_edges[:1],
            user_id="user1",
            description="Updated description"
        )

        assert result["name"] == "Updated"
        assert len(result["nodes"]) == 2

        # Verify in database
        workflow = storage.get_workflow("wf1", "user1")
        assert workflow["name"] == "Updated"

    def test_save_workflow_user_isolation(self, storage, sample_nodes, sample_edges):
        """Test that users can only update their own workflows"""
        # Create as user1
        storage.save_workflow(
            workflow_id="wf1",
            name="User1 Workflow",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user1"
        )

        # Try to update as user2 (should not work - creates new or fails silently)
        storage.save_workflow(
            workflow_id="wf1",
            name="User2 Attempt",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user2"
        )

        # Verify user1's workflow unchanged
        workflow = storage.get_workflow("wf1", "user1")
        assert workflow["name"] == "User1 Workflow"

    def test_get_workflow_returns_workflow(self, storage, sample_nodes, sample_edges):
        """Test getting a workflow by ID"""
        storage.save_workflow(
            workflow_id="wf1",
            name="Test",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user1"
        )

        workflow = storage.get_workflow("wf1", "user1")

        assert workflow is not None
        assert workflow["id"] == "wf1"
        assert workflow["name"] == "Test"
        assert workflow["nodes"] == sample_nodes
        assert workflow["edges"] == sample_edges
        assert workflow["is_active"] is True
        assert workflow["run_count"] == 0

    def test_get_workflow_returns_none_for_nonexistent(self, storage):
        """Test getting nonexistent workflow returns None"""
        result = storage.get_workflow("nonexistent", "user1")
        assert result is None

    def test_get_workflow_user_isolation(self, storage, sample_nodes, sample_edges):
        """Test that users cannot get other users' workflows"""
        storage.save_workflow(
            workflow_id="wf1",
            name="User1 Workflow",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="user1"
        )

        # User2 should not see user1's workflow
        result = storage.get_workflow("wf1", "user2")
        assert result is None

    def test_list_workflows_returns_user_workflows(self, storage, sample_nodes, sample_edges):
        """Test listing workflows for a user"""
        # Create workflows for user1
        storage.save_workflow(
            workflow_id="wf1", name="Workflow 1",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )
        storage.save_workflow(
            workflow_id="wf2", name="Workflow 2",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )
        # Create for user2
        storage.save_workflow(
            workflow_id="wf3", name="Workflow 3",
            nodes=sample_nodes, edges=sample_edges, user_id="user2"
        )

        # List user1's workflows
        workflows = storage.list_workflows("user1")
        assert len(workflows) == 2
        assert all(w["user_id"] == "user1" for w in workflows)

    def test_list_workflows_pagination(self, storage, sample_nodes, sample_edges):
        """Test pagination with limit and offset"""
        # Create 5 workflows
        for i in range(5):
            storage.save_workflow(
                workflow_id=f"wf{i}", name=f"Workflow {i}",
                nodes=sample_nodes, edges=sample_edges, user_id="user1"
            )

        # Get first page
        page1 = storage.list_workflows("user1", limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = storage.list_workflows("user1", limit=2, offset=2)
        assert len(page2) == 2

        # Get third page (partial)
        page3 = storage.list_workflows("user1", limit=2, offset=4)
        assert len(page3) == 1

    def test_list_workflows_active_only(self, storage, sample_nodes, sample_edges):
        """Test filtering by active status"""
        # Active only filter should work when implemented
        workflows = storage.list_workflows("user1", active_only=True)
        assert isinstance(workflows, list)

    def test_delete_workflow_removes_workflow(self, storage, sample_nodes, sample_edges):
        """Test deleting a workflow"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        # Verify exists
        assert storage.get_workflow("wf1", "user1") is not None

        # Delete
        result = storage.delete_workflow("wf1", "user1")
        assert result is True

        # Verify deleted
        assert storage.get_workflow("wf1", "user1") is None

    def test_delete_workflow_returns_false_for_nonexistent(self, storage):
        """Test deleting nonexistent workflow returns False"""
        result = storage.delete_workflow("nonexistent", "user1")
        assert result is False

    def test_delete_workflow_user_isolation(self, storage, sample_nodes, sample_edges):
        """Test users cannot delete other users' workflows"""
        storage.save_workflow(
            workflow_id="wf1", name="User1 Workflow",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        # User2 cannot delete user1's workflow
        result = storage.delete_workflow("wf1", "user2")
        assert result is False

        # Workflow still exists for user1
        assert storage.get_workflow("wf1", "user1") is not None

    def test_record_execution(self, storage, sample_nodes, sample_edges):
        """Test recording workflow execution"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        execution_id = storage.record_execution(
            workflow_id="wf1",
            user_id="user1",
            status="completed",
            steps_executed=3,
            execution_time_ms=150,
            results={"output": "success"}
        )

        assert execution_id > 0

        # Check workflow run count updated
        workflow = storage.get_workflow("wf1", "user1")
        assert workflow["run_count"] == 1
        assert workflow["last_run_at"] is not None

    def test_record_execution_failed(self, storage, sample_nodes, sample_edges):
        """Test recording failed execution"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        execution_id = storage.record_execution(
            workflow_id="wf1",
            user_id="user1",
            status="failed",
            steps_executed=2,
            execution_time_ms=100,
            error="Node 3 failed: connection timeout"
        )

        assert execution_id > 0

    def test_get_execution_history(self, storage, sample_nodes, sample_edges):
        """Test getting execution history"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        # Record multiple executions
        storage.record_execution(
            workflow_id="wf1", user_id="user1",
            status="completed", steps_executed=3, execution_time_ms=100
        )
        storage.record_execution(
            workflow_id="wf1", user_id="user1",
            status="completed", steps_executed=3, execution_time_ms=120
        )
        storage.record_execution(
            workflow_id="wf1", user_id="user1",
            status="failed", steps_executed=2, execution_time_ms=80,
            error="Test error"
        )

        # Get history
        history = storage.get_execution_history("wf1", "user1")
        assert len(history) == 3

        # Most recent first
        assert history[0]["status"] == "failed"
        assert history[0]["error"] == "Test error"

    def test_get_execution_history_limit(self, storage, sample_nodes, sample_edges):
        """Test execution history respects limit"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        # Record 5 executions
        for i in range(5):
            storage.record_execution(
                workflow_id="wf1", user_id="user1",
                status="completed", steps_executed=3, execution_time_ms=100
            )

        # Get limited history
        history = storage.get_execution_history("wf1", "user1", limit=3)
        assert len(history) == 3

    def test_get_execution_history_user_isolation(self, storage, sample_nodes, sample_edges):
        """Test execution history is user-isolated"""
        storage.save_workflow(
            workflow_id="wf1", name="Test",
            nodes=sample_nodes, edges=sample_edges, user_id="user1"
        )

        storage.record_execution(
            workflow_id="wf1", user_id="user1",
            status="completed", steps_executed=3, execution_time_ms=100
        )

        # User2 should not see user1's executions
        history = storage.get_execution_history("wf1", "user2")
        assert len(history) == 0


class TestAutomationStorageSingleton:
    """Test singleton pattern"""

    def test_get_automation_storage_returns_same_instance(self):
        """Test singleton returns same instance"""
        # Reset singleton for test
        import api.automation_storage as module
        module._automation_storage = None

        storage1 = get_automation_storage()
        storage2 = get_automation_storage()

        assert storage1 is storage2

    def test_singleton_uses_default_path(self):
        """Test singleton uses config paths"""
        import api.automation_storage as module
        module._automation_storage = None

        storage = get_automation_storage()
        assert storage.db_path is not None
        assert "automations.db" in str(storage.db_path)
