"""
Tests for Workflow Storage

Tests SQLite persistence for workflows and work items.
"""

import pytest
from datetime import datetime, UTC
from pathlib import Path

from api.workflow_storage import WorkflowStorage, get_workflow_storage
from api.workflow_models import (
    Workflow,
    WorkItem,
    Stage,
    WorkflowTrigger,
    WorkItemStatus,
    WorkItemPriority,
    StageType,
    WorkflowTriggerType,
    WorkflowType,
    AssignmentType,
)


class TestWorkflowStorageInit:
    """Test storage initialization"""

    def test_init_creates_database(self, tmp_path):
        """Test database file is created on init"""
        db_path = tmp_path / "test.db"
        storage = WorkflowStorage(db_path=str(db_path))
        assert db_path.exists()

    def test_init_creates_parent_directories(self, tmp_path):
        """Test nested directories are created"""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        storage = WorkflowStorage(db_path=str(db_path))
        assert db_path.exists()

    def test_init_creates_tables(self, tmp_path):
        """Test database tables are created"""
        import sqlite3
        db_path = tmp_path / "test.db"
        storage = WorkflowStorage(db_path=str(db_path))

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "workflows" in tables
        assert "work_items" in tables
        assert "stage_transitions" in tables
        assert "attachments" in tables
        assert "starred_workflows" in tables


class TestWorkflowCRUD:
    """Test workflow CRUD operations"""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage with temp database"""
        return WorkflowStorage(db_path=str(tmp_path / "test.db"))

    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow"""
        return Workflow(
            id="wf_test_123",
            name="Test Workflow",
            description="A test workflow",
            icon="📋",
            category="testing",
            workflow_type=WorkflowType.LOCAL_AUTOMATION,
            stages=[
                Stage(
                    id="stage_1",
                    name="Start",
                    description="Initial stage",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                    order=0,
                    is_terminal=False
                ),
                Stage(
                    id="stage_2",
                    name="End",
                    description="Final stage",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                    order=1,
                    is_terminal=True
                )
            ],
            triggers=[
                WorkflowTrigger(
                    trigger_type=WorkflowTriggerType.MANUAL,
                    name="Manual Start"
                )
            ],
            created_by="user1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            tags=["test", "sample"]
        )

    def test_save_workflow(self, storage, sample_workflow):
        """Test saving a workflow"""
        storage.save_workflow(sample_workflow, user_id="user1")

        # Verify saved
        workflow = storage.get_workflow("wf_test_123", user_id="user1")
        assert workflow is not None
        assert workflow.id == "wf_test_123"
        assert workflow.name == "Test Workflow"

    def test_save_workflow_with_team(self, storage, sample_workflow):
        """Test saving a team workflow"""
        sample_workflow.workflow_type = WorkflowType.TEAM_WORKFLOW
        sample_workflow.owner_team_id = "team1"
        sample_workflow.visibility = "team"

        storage.save_workflow(sample_workflow, user_id="user1", team_id="team1")

        workflow = storage.get_workflow("wf_test_123", user_id="user1", team_id="team1")
        assert workflow is not None
        assert workflow.visibility == "team"

    def test_get_workflow_returns_none_for_nonexistent(self, storage):
        """Test getting nonexistent workflow returns None"""
        result = storage.get_workflow("nonexistent", user_id="user1")
        assert result is None

    def test_get_workflow_visibility_personal(self, storage, sample_workflow):
        """Test personal workflow visibility"""
        sample_workflow.visibility = "personal"
        storage.save_workflow(sample_workflow, user_id="user1")

        # Owner can see
        assert storage.get_workflow("wf_test_123", user_id="user1") is not None

        # Other user cannot see
        assert storage.get_workflow("wf_test_123", user_id="user2") is None

    def test_get_workflow_visibility_global(self, storage, sample_workflow):
        """Test global workflow visibility"""
        sample_workflow.visibility = "global"
        storage.save_workflow(sample_workflow, user_id="user1")

        # Anyone can see
        assert storage.get_workflow("wf_test_123", user_id="user2") is not None

    def test_list_workflows(self, storage, sample_workflow):
        """Test listing workflows"""
        storage.save_workflow(sample_workflow, user_id="user1")

        workflows = storage.list_workflows(user_id="user1")
        assert len(workflows) >= 1
        assert any(w.id == "wf_test_123" for w in workflows)

    def test_list_workflows_user_isolation(self, storage, sample_workflow):
        """Test user isolation in listing"""
        sample_workflow.visibility = "personal"
        storage.save_workflow(sample_workflow, user_id="user1")

        # User1 sees their workflow
        workflows = storage.list_workflows(user_id="user1")
        assert any(w.id == "wf_test_123" for w in workflows)

        # User2 doesn't see it
        workflows = storage.list_workflows(user_id="user2")
        assert not any(w.id == "wf_test_123" for w in workflows)

    def test_list_workflows_by_category(self, storage, sample_workflow):
        """Test filtering by category"""
        storage.save_workflow(sample_workflow, user_id="user1")

        workflows = storage.list_workflows(user_id="user1", category="testing")
        assert any(w.id == "wf_test_123" for w in workflows)

        workflows = storage.list_workflows(user_id="user1", category="other")
        assert not any(w.id == "wf_test_123" for w in workflows)

    def test_delete_workflow(self, storage, sample_workflow):
        """Test deleting a workflow (soft delete)"""
        storage.save_workflow(sample_workflow, user_id="user1")

        # Delete (soft delete)
        storage.delete_workflow("wf_test_123", user_id="user1")

        # Verify workflow is disabled (soft delete)
        workflow = storage.get_workflow("wf_test_123", user_id="user1")
        assert workflow is not None
        assert workflow.enabled is False


class TestWorkItemCRUD:
    """Test work item CRUD operations"""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage with temp database"""
        return WorkflowStorage(db_path=str(tmp_path / "test.db"))

    @pytest.fixture
    def sample_work_item(self):
        """Create sample work item"""
        return WorkItem(
            id="wi_test_123",
            workflow_id="wf_test",
            workflow_name="Test Workflow",
            current_stage_id="stage_1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            priority=WorkItemPriority.NORMAL,
            data={"key": "value"},
            created_by="user1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            tags=["urgent"]
        )

    def test_save_work_item(self, storage, sample_work_item):
        """Test saving a work item"""
        storage.save_work_item(sample_work_item, user_id="user1")

        # Verify saved
        work_item = storage.get_work_item("wi_test_123", user_id="user1")
        assert work_item is not None
        assert work_item.id == "wi_test_123"
        assert work_item.status == WorkItemStatus.PENDING

    def test_save_work_item_update(self, storage, sample_work_item):
        """Test updating a work item"""
        storage.save_work_item(sample_work_item, user_id="user1")

        # Update
        sample_work_item.status = WorkItemStatus.IN_PROGRESS
        sample_work_item.assigned_to = "user2"
        storage.save_work_item(sample_work_item, user_id="user1")

        # Verify update
        work_item = storage.get_work_item("wi_test_123", user_id="user1")
        assert work_item.status == WorkItemStatus.IN_PROGRESS
        assert work_item.assigned_to == "user2"

    def test_get_work_item_returns_none_for_nonexistent(self, storage):
        """Test getting nonexistent work item"""
        result = storage.get_work_item("nonexistent", user_id="user1")
        assert result is None

    def test_get_work_item_by_id(self, storage, sample_work_item):
        """Test getting work item by ID without user isolation"""
        storage.save_work_item(sample_work_item, user_id="user1")

        # Should work without user_id (admin access)
        work_item = storage.get_work_item_by_id("wi_test_123")
        assert work_item is not None
        assert work_item.id == "wi_test_123"

    def test_list_work_items(self, storage, sample_work_item):
        """Test listing work items"""
        storage.save_work_item(sample_work_item, user_id="user1")

        work_items = storage.list_work_items(user_id="user1")
        assert len(work_items) >= 1
        assert any(w.id == "wi_test_123" for w in work_items)

    def test_list_work_items_by_workflow(self, storage, sample_work_item):
        """Test filtering by workflow"""
        storage.save_work_item(sample_work_item, user_id="user1")

        work_items = storage.list_work_items(user_id="user1", workflow_id="wf_test")
        assert any(w.id == "wi_test_123" for w in work_items)

        work_items = storage.list_work_items(user_id="user1", workflow_id="other")
        assert not any(w.id == "wi_test_123" for w in work_items)

    def test_list_work_items_by_status(self, storage, sample_work_item):
        """Test filtering by status"""
        storage.save_work_item(sample_work_item, user_id="user1")

        work_items = storage.list_work_items(user_id="user1", status=WorkItemStatus.PENDING)
        assert any(w.id == "wi_test_123" for w in work_items)

        work_items = storage.list_work_items(user_id="user1", status=WorkItemStatus.COMPLETED)
        assert not any(w.id == "wi_test_123" for w in work_items)

    def test_list_work_items_with_limit(self, storage, sample_work_item):
        """Test limit parameter"""
        # Create multiple items
        for i in range(5):
            item = WorkItem(
                id=f"wi_{i}",
                workflow_id="wf_test",
                workflow_name="Test",
                current_stage_id="stage_1",
                current_stage_name="Start",
                status=WorkItemStatus.PENDING,
                priority=WorkItemPriority.NORMAL,
                data={},
                created_by="user1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            storage.save_work_item(item, user_id="user1")

        # Get with limit
        items = storage.list_work_items(user_id="user1", limit=2)
        assert len(items) == 2


class TestStarredWorkflows:
    """Test starred workflows functionality"""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage with temp database"""
        return WorkflowStorage(db_path=str(tmp_path / "test.db"))

    @pytest.fixture
    def sample_workflow(self, storage):
        """Create and save a workflow"""
        workflow = Workflow(
            id="wf_star_test",
            name="Star Test",
            workflow_type=WorkflowType.LOCAL_AUTOMATION,
            stages=[Stage(id="s1", name="S1", stage_type=StageType.HUMAN, assignment_type=AssignmentType.QUEUE, order=0)],
            triggers=[],
            created_by="user1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        storage.save_workflow(workflow, user_id="user1")
        return workflow

    def test_star_workflow(self, storage, sample_workflow):
        """Test starring a workflow"""
        storage.star_workflow("wf_star_test", user_id="user1")

        starred = storage.get_starred_workflows(user_id="user1")
        assert "wf_star_test" in starred

    def test_unstar_workflow(self, storage, sample_workflow):
        """Test unstarring a workflow"""
        storage.star_workflow("wf_star_test", user_id="user1")
        storage.unstar_workflow("wf_star_test", user_id="user1")

        starred = storage.get_starred_workflows(user_id="user1")
        assert "wf_star_test" not in starred

    def test_is_workflow_starred(self, storage, sample_workflow):
        """Test checking if workflow is starred"""
        assert not storage.is_workflow_starred("wf_star_test", user_id="user1")

        storage.star_workflow("wf_star_test", user_id="user1")
        assert storage.is_workflow_starred("wf_star_test", user_id="user1")

    def test_starred_limit(self, storage):
        """Test max 5 starred workflows limit"""
        # Create and star 6 workflows
        for i in range(6):
            workflow = Workflow(
                id=f"wf_star_{i}",
                name=f"Star {i}",
                workflow_type=WorkflowType.LOCAL_AUTOMATION,
                stages=[Stage(id="s1", name="S1", stage_type=StageType.HUMAN, assignment_type=AssignmentType.QUEUE, order=0)],
                triggers=[],
                created_by="user1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            storage.save_workflow(workflow, user_id="user1")
            storage.star_workflow(f"wf_star_{i}", user_id="user1")

        starred = storage.get_starred_workflows(user_id="user1")
        assert len(starred) <= 5


class TestWorkflowStorageSingleton:
    """Test singleton pattern"""

    def test_get_workflow_storage_returns_same_instance(self):
        """Test singleton returns same instance"""
        # Reset singleton
        import api.workflow_storage as module
        module._workflow_storage = None

        storage1 = get_workflow_storage()
        storage2 = get_workflow_storage()

        assert storage1 is storage2

    def test_singleton_uses_default_path(self):
        """Test singleton uses config paths"""
        import api.workflow_storage as module
        module._workflow_storage = None

        storage = get_workflow_storage()
        assert storage.db_path is not None
        assert "workflows.db" in str(storage.db_path)
