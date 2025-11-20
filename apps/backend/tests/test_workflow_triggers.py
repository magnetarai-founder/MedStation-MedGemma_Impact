"""
Tests for Phase D: Workflow Triggers
Tests ON_AGENT_EVENT and ON_FILE_PATTERN trigger functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from api.workflow_models import (
    Workflow,
    Stage,
    WorkflowTrigger,
    WorkflowTriggerType,
    StageType,
    AssignmentType,
    WorkItemStatus,
    WorkflowType,
)
from api.workflow_storage import WorkflowStorage
from api.services.workflow_triggers import handle_agent_event, handle_file_event


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db):
    """Create a WorkflowStorage instance with temp DB"""
    return WorkflowStorage(db_path=temp_db)


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "test_user_123"


@pytest.fixture
def workflow_with_agent_trigger(storage, test_user_id):
    """Create a workflow with an ON_AGENT_EVENT trigger"""
    workflow = Workflow(
        name="Agent Patch Review",
        description="Review patches from agent",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=[
            Stage(
                id="review_stage",
                name="Review Patch",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.ROLE,
                role_name="reviewer",
            )
        ],
        triggers=[
            WorkflowTrigger(
                trigger_type=WorkflowTriggerType.ON_AGENT_EVENT,
                agent_event_type="agent.apply.success",
                enabled=True,
            )
        ],
        created_by=test_user_id,
    )
    storage.save_workflow(workflow, user_id=test_user_id)
    return workflow


@pytest.fixture
def workflow_with_file_trigger(storage, test_user_id):
    """Create a workflow with an ON_FILE_PATTERN trigger"""
    workflow = Workflow(
        name="File Change Review",
        description="Review file changes",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=[
            Stage(
                id="review_stage",
                name="Review File Change",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.ROLE,
                role_name="reviewer",
            )
        ],
        triggers=[
            WorkflowTrigger(
                trigger_type=WorkflowTriggerType.ON_FILE_PATTERN,
                file_pattern="src/",
                pattern_repo_root="/path/to/repo",
                enabled=True,
            )
        ],
        created_by=test_user_id,
    )
    storage.save_workflow(workflow, user_id=test_user_id)
    return workflow


class TestAgentEventTriggers:
    """Tests for ON_AGENT_EVENT triggers"""

    def test_agent_event_creates_work_item(
        self, storage, workflow_with_agent_trigger, test_user_id
    ):
        """Test that agent.apply.success event creates a work item"""
        event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
            "files": ["src/main.py", "tests/test_main.py"],
            "patch_id": "patch_123",
            "summary": "Implemented feature X",
            "session_id": "session_abc",
        }

        # Fire the event
        work_item_ids = handle_agent_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # Verify work item was created
        assert len(work_item_ids) == 1
        work_item_id = work_item_ids[0]

        # Retrieve the work item
        work_item = storage.get_work_item(work_item_id, user_id=test_user_id)
        assert work_item is not None
        assert work_item.workflow_id == workflow_with_agent_trigger.id
        assert work_item.status == WorkItemStatus.PENDING
        assert work_item.current_stage_id == "review_stage"
        assert work_item.data["agent_event"]["type"] == "agent.apply.success"
        assert work_item.data["agent_event"]["patch_id"] == "patch_123"
        assert work_item.data["triggered_by"] == "agent_event"

    def test_agent_event_no_matching_workflow(self, storage, test_user_id):
        """Test that non-matching event types don't create work items"""
        event = {
            "type": "agent.plan.complete",  # Different event type
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
        }

        work_item_ids = handle_agent_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # No work items should be created
        assert len(work_item_ids) == 0

    def test_agent_event_disabled_trigger(
        self, storage, workflow_with_agent_trigger, test_user_id
    ):
        """Test that disabled triggers don't fire"""
        # Disable the trigger
        workflow = workflow_with_agent_trigger
        workflow.triggers[0].enabled = False
        storage.save_workflow(workflow, user_id=test_user_id)

        event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
        }

        work_item_ids = handle_agent_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # No work items should be created
        assert len(work_item_ids) == 0

    def test_agent_event_template_workflow_skipped(
        self, storage, workflow_with_agent_trigger, test_user_id
    ):
        """Test that template workflows don't create work items from triggers"""
        # Mark workflow as template
        workflow = workflow_with_agent_trigger
        workflow.is_template = True
        storage.save_workflow(workflow, user_id=test_user_id)

        event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
        }

        work_item_ids = handle_agent_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # No work items should be created for templates
        assert len(work_item_ids) == 0

    def test_agent_event_invalid_event(self, storage, test_user_id):
        """Test graceful handling of invalid events"""
        # Missing 'type' field
        invalid_event = {
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
        }

        work_item_ids = handle_agent_event(
            event=invalid_event,
            storage=storage,
            user_id=test_user_id,
        )

        # Should return empty list, not crash
        assert len(work_item_ids) == 0

    def test_multiple_workflows_match_same_event(self, storage, test_user_id):
        """Test that multiple workflows can trigger from same event"""
        # Create two workflows with same trigger
        workflow1 = Workflow(
            name="Workflow 1",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="stage1",
                    name="Stage 1",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[
                WorkflowTrigger(
                    trigger_type=WorkflowTriggerType.ON_AGENT_EVENT,
                    agent_event_type="agent.apply.success",
                    enabled=True,
                )
            ],
            created_by=test_user_id,
        )
        workflow2 = Workflow(
            name="Workflow 2",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="stage2",
                    name="Stage 2",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[
                WorkflowTrigger(
                    trigger_type=WorkflowTriggerType.ON_AGENT_EVENT,
                    agent_event_type="agent.apply.success",
                    enabled=True,
                )
            ],
            created_by=test_user_id,
        )

        storage.save_workflow(workflow1, user_id=test_user_id)
        storage.save_workflow(workflow2, user_id=test_user_id)

        event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
        }

        work_item_ids = handle_agent_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # Both workflows should create work items
        assert len(work_item_ids) == 2


class TestFilePatternTriggers:
    """Tests for ON_FILE_PATTERN triggers"""

    def test_file_event_creates_work_item(
        self, storage, workflow_with_file_trigger, test_user_id
    ):
        """Test that file pattern match creates work item"""
        event = {
            "type": "file.modified",
            "file_path": "src/main.py",
            "repo_root": "/path/to/repo",
            "operation": "modify",
        }

        work_item_ids = handle_file_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # Verify work item was created
        assert len(work_item_ids) == 1
        work_item = storage.get_work_item(work_item_ids[0], user_id=test_user_id)
        assert work_item is not None
        assert work_item.data["file_event"]["file_path"] == "src/main.py"
        assert work_item.data["triggered_by"] == "file_pattern"

    def test_file_event_no_pattern_match(
        self, storage, workflow_with_file_trigger, test_user_id
    ):
        """Test that non-matching file paths don't create work items"""
        event = {
            "type": "file.modified",
            "file_path": "docs/README.md",  # Doesn't match "src/"
            "repo_root": "/path/to/repo",
            "operation": "modify",
        }

        work_item_ids = handle_file_event(
            event=event,
            storage=storage,
            user_id=test_user_id,
        )

        # No work items should be created
        assert len(work_item_ids) == 0

    def test_file_event_invalid_event(self, storage, test_user_id):
        """Test graceful handling of invalid file events"""
        invalid_event = {
            "file_path": "src/main.py",  # Missing 'type'
        }

        work_item_ids = handle_file_event(
            event=invalid_event,
            storage=storage,
            user_id=test_user_id,
        )

        # Should return empty list, not crash
        assert len(work_item_ids) == 0
