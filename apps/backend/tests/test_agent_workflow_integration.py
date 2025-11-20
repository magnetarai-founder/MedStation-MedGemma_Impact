"""
Tests for Phase E: Agent ↔ Workflow Integration
Tests bidirectional integration between agent and workflow systems
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from api.workflow_models import (
    Workflow,
    WorkItem,
    Stage,
    WorkflowTrigger,
    WorkflowTriggerType,
    StageType,
    AssignmentType,
    WorkItemStatus,
    WorkflowType,
)
from api.workflow_storage import WorkflowStorage
from api.services.workflow_triggers import handle_agent_event
from api.services.workflow_agent_integration import run_agent_assist_for_stage


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


class TestAgentToWorkflow:
    """Tests for Agent → Workflow event flow (Phase E.1)"""

    def test_agent_apply_creates_workflow_item(self, storage, test_user_id):
        """Test that agent.apply.success creates work items via triggers"""
        # Create workflow with agent event trigger
        workflow = Workflow(
            name="Code Review Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="review_stage",
                    name="Review Code",
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

        # Simulate agent apply success event
        agent_event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
            "files": ["src/main.py"],
            "patch_id": "patch_123",
            "summary": "Fixed bug in main.py",
            "session_id": "session_abc",
            "engine_used": "aider",
        }

        # Fire the event
        work_item_ids = handle_agent_event(
            event=agent_event,
            storage=storage,
            user_id=test_user_id,
        )

        # Verify work item created
        assert len(work_item_ids) == 1
        work_item = storage.get_work_item(work_item_ids[0], user_id=test_user_id)
        assert work_item is not None
        assert work_item.workflow_id == workflow.id
        assert work_item.data["agent_event"]["patch_id"] == "patch_123"
        assert work_item.data["agent_event"]["files"] == ["src/main.py"]


class TestWorkflowToAgent:
    """Tests for Workflow → Agent flow (Phase E.2)"""

    def test_agent_assist_stage_advisory_only(self, storage, test_user_id):
        """Test Agent Assist stage without auto-apply (Phase B behavior)"""
        # Create workflow with Agent Assist stage (no auto-apply)
        workflow = Workflow(
            name="Test Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="agent_stage",
                    name="Agent Assist",
                    stage_type=StageType.AGENT_ASSIST,
                    assignment_type=AssignmentType.QUEUE,
                    agent_prompt="Review this code",
                    agent_auto_apply=False,  # Advisory only
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )
        storage.save_workflow(workflow, user_id=test_user_id)

        # Create work item
        work_item = WorkItem(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            current_stage_id="agent_stage",
            current_stage_name="Agent Assist",
            status=WorkItemStatus.PENDING,
            data={"repo_root": "/path/to/repo"},
            created_by=test_user_id,
        )
        storage.save_work_item(work_item, user_id=test_user_id)

        # Mock the agent planning logic
        with patch("api.agent.orchestration.planning.generate_plan_logic") as mock_plan:
            with patch("api.agent.orchestration.context_bundle.build_context_bundle") as mock_ctx:
                # Mock responses
                mock_ctx.return_value = Mock(
                    file_tree="",
                    recent_changes=[],
                    relevant_snippets=[],
                )
                mock_plan.return_value = Mock(
                    steps=[
                        Mock(
                            description="Step 1",
                            risk_level="low",
                            estimated_files=["file1.py"],
                        )
                    ],
                    risks=["No major risks"],
                    requires_confirmation=True,
                    estimated_time_min=10,
                    model_used="test-model",
                )

                # Run agent assist
                run_agent_assist_for_stage(
                    storage=storage,
                    work_item=work_item,
                    stage=workflow.stages[0],
                    user_id=test_user_id,
                )

        # Retrieve work item and verify
        updated_item = storage.get_work_item(work_item.id, user_id=test_user_id)
        assert updated_item is not None
        assert "agent_recommendation" in updated_item.data
        assert "agent_auto_apply_result" not in updated_item.data  # No auto-apply

    def test_agent_assist_with_auto_apply(self, storage, test_user_id):
        """Test Agent Assist stage with auto-apply enabled (Phase E)"""
        # Create workflow with Agent Assist stage WITH auto-apply
        workflow = Workflow(
            name="Test Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="agent_stage",
                    name="Agent Assist",
                    stage_type=StageType.AGENT_ASSIST,
                    assignment_type=AssignmentType.QUEUE,
                    agent_prompt="Fix this bug",
                    agent_auto_apply=True,  # Auto-apply enabled
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )
        storage.save_workflow(workflow, user_id=test_user_id)

        # Create work item
        work_item = WorkItem(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            current_stage_id="agent_stage",
            current_stage_name="Agent Assist",
            status=WorkItemStatus.PENDING,
            data={"repo_root": "/path/to/repo"},
            created_by=test_user_id,
        )
        storage.save_work_item(work_item, user_id=test_user_id)

        # Mock the agent planning and apply logic
        with patch("api.agent.orchestration.planning.generate_plan_logic") as mock_plan:
            with patch("api.agent.orchestration.context_bundle.build_context_bundle") as mock_ctx:
                with patch("api.agent.orchestration.apply.apply_plan_logic") as mock_apply:
                    # Mock responses
                    mock_ctx.return_value = Mock(
                        file_tree="",
                        recent_changes=[],
                        relevant_snippets=[],
                    )
                    mock_plan.return_value = Mock(
                        steps=[Mock(description="Step 1", risk_level="low", estimated_files=["file1.py"])],
                        risks=[],
                        requires_confirmation=False,
                        estimated_time_min=5,
                        model_used="test-model",
                    )
                    # Mock successful apply
                    mock_apply.return_value = (
                        [Mock(path="file1.py", patch_text="diff", summary="Applied")],
                        "patch_xyz",
                        "aider",
                    )

                    # Run agent assist
                    run_agent_assist_for_stage(
                        storage=storage,
                        work_item=work_item,
                        stage=workflow.stages[0],
                        user_id=test_user_id,
                    )

        # Retrieve work item and verify auto-apply happened
        updated_item = storage.get_work_item(work_item.id, user_id=test_user_id)
        assert updated_item is not None
        assert "agent_recommendation" in updated_item.data
        assert "agent_auto_apply_result" in updated_item.data
        assert updated_item.data["agent_auto_apply_result"]["success"] is True
        assert updated_item.data["agent_auto_apply_result"]["patch_id"] == "patch_xyz"

    def test_agent_assist_auto_apply_error_handling(self, storage, test_user_id):
        """Test that auto-apply errors are handled gracefully"""
        # Create workflow with auto-apply
        workflow = Workflow(
            name="Test Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="agent_stage",
                    name="Agent Assist",
                    stage_type=StageType.AGENT_ASSIST,
                    assignment_type=AssignmentType.QUEUE,
                    agent_prompt="Fix bug",
                    agent_auto_apply=True,
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )
        storage.save_workflow(workflow, user_id=test_user_id)

        # Create work item
        work_item = WorkItem(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            current_stage_id="agent_stage",
            current_stage_name="Agent Assist",
            status=WorkItemStatus.PENDING,
            data={"repo_root": "/path/to/repo"},
            created_by=test_user_id,
        )
        storage.save_work_item(work_item, user_id=test_user_id)

        # Mock agent logic with apply failure
        with patch("api.agent.orchestration.planning.generate_plan_logic") as mock_plan:
            with patch("api.agent.orchestration.context_bundle.build_context_bundle") as mock_ctx:
                with patch("api.agent.orchestration.apply.apply_plan_logic") as mock_apply:
                    mock_ctx.return_value = Mock(file_tree="", recent_changes=[], relevant_snippets=[])
                    mock_plan.return_value = Mock(
                        steps=[Mock(description="Step 1", risk_level="low", estimated_files=[])],
                        risks=[],
                        requires_confirmation=False,
                        estimated_time_min=5,
                        model_used="test-model",
                    )
                    # Mock apply failure
                    mock_apply.side_effect = Exception("Apply failed")

                    # Run agent assist - should not crash
                    run_agent_assist_for_stage(
                        storage=storage,
                        work_item=work_item,
                        stage=workflow.stages[0],
                        user_id=test_user_id,
                    )

        # Verify error was recorded
        updated_item = storage.get_work_item(work_item.id, user_id=test_user_id)
        assert updated_item is not None
        assert "agent_auto_apply_result" in updated_item.data
        assert updated_item.data["agent_auto_apply_result"]["success"] is False
        assert "error" in updated_item.data["agent_auto_apply_result"]


class TestEndToEndIntegration:
    """End-to-end integration tests"""

    def test_full_loop_agent_triggers_workflow_triggers_agent(
        self, storage, test_user_id
    ):
        """Test complete loop: Agent creates WorkItem, WorkItem triggers Agent"""
        # Create workflow that triggers on agent events and has agent assist stage
        workflow = Workflow(
            name="Full Loop Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[
                Stage(
                    id="agent_review_stage",
                    name="Agent Review",
                    stage_type=StageType.AGENT_ASSIST,
                    assignment_type=AssignmentType.QUEUE,
                    agent_prompt="Review the patch",
                    agent_auto_apply=False,  # Advisory only for safety
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

        # Step 1: Agent applies patch, triggers workflow
        agent_event = {
            "type": "agent.apply.success",
            "user_id": test_user_id,
            "repo_root": "/path/to/repo",
            "files": ["src/main.py"],
            "patch_id": "patch_original",
            "summary": "Original patch",
        }

        work_item_ids = handle_agent_event(
            event=agent_event,
            storage=storage,
            user_id=test_user_id,
        )

        assert len(work_item_ids) == 1

        # Step 2: WorkItem enters agent assist stage
        work_item = storage.get_work_item(work_item_ids[0], user_id=test_user_id)

        # Mock agent assist
        with patch("api.agent.orchestration.planning.generate_plan_logic") as mock_plan:
            with patch("api.agent.orchestration.context_bundle.build_context_bundle") as mock_ctx:
                mock_ctx.return_value = Mock(file_tree="", recent_changes=[], relevant_snippets=[])
                mock_plan.return_value = Mock(
                    steps=[Mock(description="Review step", risk_level="low", estimated_files=[])],
                    risks=[],
                    requires_confirmation=True,
                    estimated_time_min=5,
                    model_used="test-model",
                )

                run_agent_assist_for_stage(
                    storage=storage,
                    work_item=work_item,
                    stage=workflow.stages[0],
                    user_id=test_user_id,
                )

        # Verify full loop completed
        final_item = storage.get_work_item(work_item.id, user_id=test_user_id)
        assert final_item is not None
        # Has original agent event
        assert final_item.data["agent_event"]["patch_id"] == "patch_original"
        # Has agent recommendation from second agent call
        assert "agent_recommendation" in final_item.data
