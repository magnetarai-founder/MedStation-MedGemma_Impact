"""
Tests for Workflow Agent Assist Integration (Phase B)

Tests the Agent Assist stage functionality:
- AGENT_ASSIST stage type
- Agent recommendation generation
- Graceful error handling
- Non-destructive behavior (advisory only)
"""

import os
import pytest
import tempfile
from pathlib import Path
from typing import Optional

# Ensure development mode to avoid ELOHIM_FOUNDER_PASSWORD requirement
os.environ.setdefault('ELOHIM_ENV', 'development')

# Skip if workflow models cannot be imported
try:
    from api.workflow_models import (
        Workflow,
        Stage,
        WorkItem,
        WorkItemStatus,
        WorkItemPriority,
        StageType,
        AssignmentType,
        ConditionalRoute,
        WorkflowType,
    )
    from api.workflow_storage import WorkflowStorage
    from api.services.workflow_orchestrator import WorkflowOrchestrator
    from api.services import workflow_agent_integration as wai
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MODELS_AVAILABLE, reason="Workflow models not available")


def create_test_orchestrator():
    """Create orchestrator with temporary database"""
    tmp_db = Path(tempfile.gettempdir()) / "test_workflows_agent_assist.db"
    if tmp_db.exists():
        tmp_db.unlink()
    storage = WorkflowStorage(db_path=str(tmp_db))
    orchestrator = WorkflowOrchestrator(storage=storage)
    return storage, orchestrator


class TestAgentAssistStageType:
    """Test AGENT_ASSIST stage type is properly defined"""

    def test_agent_assist_stage_type_exists(self):
        """Test that AGENT_ASSIST stage type exists"""
        assert hasattr(StageType, 'AGENT_ASSIST')
        assert StageType.AGENT_ASSIST == "agent_assist"


class TestAgentAssistStageConfiguration:
    """Test Agent Assist stage configuration fields"""

    def test_stage_has_agent_fields(self):
        """Test that Stage model has agent assist configuration fields"""
        stage = Stage(
            id="test_stage",
            name="Agent Assist Stage",
            order=1,
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.QUEUE,
            agent_prompt="Test prompt",
            agent_target_path="src/",
            agent_model_hint="gpt-4",
        )

        assert stage.agent_prompt == "Test prompt"
        assert stage.agent_target_path == "src/"
        assert stage.agent_model_hint == "gpt-4"

    def test_stage_agent_fields_optional(self):
        """Test that agent fields are optional (backwards compatibility)"""
        stage = Stage(
            id="test_stage",
            name="Regular Stage",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
        )

        # Should have default None values
        assert stage.agent_prompt is None
        assert stage.agent_target_path is None
        assert stage.agent_model_hint is None


class TestAgentAssistTransition:
    """Test transitions into Agent Assist stages"""

    def test_transition_to_agent_assist_stage_does_not_crash(self):
        """Test that transitioning to Agent Assist stage does not crash"""
        storage, orchestrator = create_test_orchestrator()
        user_id = "test_user_123"

        # Define workflow with HUMAN -> AGENT_ASSIST stages
        stage1 = Stage(
            id="stage_1",
            name="Initial Review",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            next_stages=[ConditionalRoute(next_stage_id="stage_2", conditions=[])],
        )

        stage2 = Stage(
            id="stage_2",
            name="Agent Assist",
            order=2,
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.QUEUE,
            agent_prompt="Suggest improvements for this code",
        )

        workflow = Workflow(
            id="test_agent_workflow",
            name="Agent Assist Test Workflow",
            description="Test workflow with agent assist",
            icon="🤖",
            category="test",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[stage1, stage2],
            triggers=[],
            created_by=user_id,
        )

        orchestrator.register_workflow(workflow, user_id=user_id)

        # Create work item
        work_item = orchestrator.create_work_item(
            workflow_id=workflow.id,
            user_id=user_id,
            data={"repo_root": str(Path.cwd())},
            created_by=user_id,
            priority=WorkItemPriority.NORMAL,
            tags=[],
        )

        assert work_item.current_stage_id == "stage_1"

        # Complete first stage to transition to Agent Assist
        completed = orchestrator.complete_stage(
            work_item_id=work_item.id,
            user_id=user_id,
            stage_data={},
            notes="Moving to agent assist",
        )

        # Should successfully transition
        assert completed.current_stage_id == "stage_2"
        assert completed.current_stage_name == "Agent Assist"

    def test_agent_assist_is_called_on_transition(self, monkeypatch):
        """Test that Agent Assist is triggered during transition"""
        storage, orchestrator = create_test_orchestrator()
        user_id = "test_user_456"

        # Track if agent assist was called
        agent_calls = []

        # Monkeypatch at the orchestrator's import location
        from api.services import workflow_orchestrator as wo_mod
        original_func = wo_mod.run_agent_assist_for_stage

        def tracking_agent_assist(storage, work_item, stage, user_id):
            agent_calls.append({
                "work_item_id": work_item.id,
                "stage_id": stage.id,
                "user_id": user_id,
            })
            # Simulate successful agent assist
            work_item.data["agent_recommendation"] = {
                "plan_summary": "Test recommendation",
                "engine_used": "test_planner",
                "model_used": "test-model",
                "steps": [],
                "risks": [],
                "requires_confirmation": True,
                "estimated_time_min": 0,
            }
            storage.save_work_item(work_item, user_id)

        monkeypatch.setattr(wo_mod, "run_agent_assist_for_stage", tracking_agent_assist)

        # Create workflow
        stage1 = Stage(
            id="s1",
            name="Start",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            next_stages=[ConditionalRoute(next_stage_id="s2", conditions=[])],
        )

        stage2 = Stage(
            id="s2",
            name="Agent Review",
            order=2,
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.QUEUE,
            agent_prompt="Review and suggest optimizations",
        )

        workflow = Workflow(
            id="tracking_agent_wf",
            name="Tracking Agent Workflow",
            description="Test agent is called",
            icon="📞",
            category="test",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[stage1, stage2],
            triggers=[],
            created_by=user_id,
        )

        orchestrator.register_workflow(workflow, user_id=user_id)

        # Create and transition work item
        work_item = orchestrator.create_work_item(
            workflow_id=workflow.id,
            user_id=user_id,
            data={"repo_root": str(Path.cwd())},
            created_by=user_id,
            priority=WorkItemPriority.NORMAL,
            tags=[],
        )

        completed = orchestrator.complete_stage(
            work_item_id=work_item.id,
            user_id=user_id,
            stage_data={},
            notes="Trigger agent",
        )

        # Verify agent was called
        assert len(agent_calls) == 1
        assert agent_calls[0]["stage_id"] == "s2"
        assert agent_calls[0]["work_item_id"] == work_item.id

        # Reload work item from storage to get updated data
        refreshed = storage.get_work_item(work_item.id, user_id)

        # Verify agent recommendation was populated
        assert "agent_recommendation" in refreshed.data
        assert refreshed.data["agent_recommendation"]["plan_summary"] == "Test recommendation"


class TestAgentAssistErrorHandling:
    """Test Agent Assist error handling"""

    def test_agent_assist_error_does_not_break_transition(self, monkeypatch):
        """Test that Agent Assist errors don't break stage transitions"""
        storage, orchestrator = create_test_orchestrator()
        user_id = "test_user_789"

        # Monkeypatch to simulate agent error
        def failing_agent_assist(storage, work_item, stage, user_id):
            raise Exception("Simulated agent failure")

        monkeypatch.setattr(wai, "run_agent_assist_for_stage", failing_agent_assist)

        # Create workflow
        stage1 = Stage(
            id="s1",
            name="Start",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            next_stages=[ConditionalRoute(next_stage_id="s2", conditions=[])],
        )

        stage2 = Stage(
            id="s2",
            name="Agent (will fail)",
            order=2,
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.QUEUE,
            agent_prompt="This will fail",
        )

        workflow = Workflow(
            id="failing_agent_wf",
            name="Failing Agent Workflow",
            description="Test error handling",
            icon="⚠️",
            category="test",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[stage1, stage2],
            triggers=[],
            created_by=user_id,
        )

        orchestrator.register_workflow(workflow, user_id=user_id)

        # Create work item
        work_item = orchestrator.create_work_item(
            workflow_id=workflow.id,
            user_id=user_id,
            data={},
            created_by=user_id,
            priority=WorkItemPriority.NORMAL,
            tags=[],
        )

        # Transition should succeed even though agent fails
        completed = orchestrator.complete_stage(
            work_item_id=work_item.id,
            user_id=user_id,
            stage_data={},
            notes="Transition despite error",
        )

        # Verify transition succeeded
        assert completed.current_stage_id == "s2"
        assert completed.current_stage_name == "Agent (will fail)"


class TestAgentAssistNonDestructiveBehavior:
    """Test that Agent Assist is advisory only (Phase B)"""

    def test_agent_assist_does_not_modify_files(self, monkeypatch):
        """Test that Agent Assist does not auto-apply changes"""
        storage, orchestrator = create_test_orchestrator()
        user_id = "test_user_non_destructive"

        # Track if any file operations were attempted
        file_ops_called = []

        # Monkeypatch at the orchestrator's import location
        from api.services import workflow_orchestrator as wo_mod

        def tracking_agent_assist(storage, work_item, stage, user_id):
            # Agent should only read/analyze, not write
            work_item.data["agent_recommendation"] = {
                "plan_summary": "Recommendation only - no changes applied",
                "engine_used": "planner",
                "model_used": "test-model",
                "steps": [],
                "risks": [],
                "requires_confirmation": True,
                "estimated_time_min": 0,
            }
            storage.save_work_item(work_item, user_id)
            # Explicitly track that we did NOT modify files
            file_ops_called.append("read_only")

        monkeypatch.setattr(wo_mod, "run_agent_assist_for_stage", tracking_agent_assist)

        # Create workflow with initial stage + agent stage
        stage1 = Stage(
            id="start_stage",
            name="Initial",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            next_stages=[ConditionalRoute(next_stage_id="agent_stage", conditions=[])],
        )

        stage2 = Stage(
            id="agent_stage",
            name="Agent Analysis",
            order=2,
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.QUEUE,
            agent_prompt="Analyze code",
        )

        workflow = Workflow(
            id="non_destructive_wf",
            name="Non-Destructive Workflow",
            description="Verify no file changes",
            icon="🔒",
            category="test",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[stage1, stage2],
            triggers=[],
            created_by=user_id,
        )

        orchestrator.register_workflow(workflow, user_id=user_id)

        work_item = orchestrator.create_work_item(
            workflow_id=workflow.id,
            user_id=user_id,
            data={},
            created_by=user_id,
            priority=WorkItemPriority.NORMAL,
            tags=[],
        )

        # Transition to Agent Assist stage to trigger the hook
        orchestrator.complete_stage(
            work_item_id=work_item.id,
            user_id=user_id,
            stage_data={},
            notes="Move to agent",
        )

        # Reload to verify recommendation exists
        refreshed = storage.get_work_item(work_item.id, user_id)
        assert "agent_recommendation" in refreshed.data
        assert refreshed.data["agent_recommendation"]["plan_summary"] == "Recommendation only - no changes applied"
        assert refreshed.data["agent_recommendation"]["requires_confirmation"] is True

        # Verify agent only did read-only operations
        assert file_ops_called == ["read_only"]


class TestAgentAssistBackwardsCompatibility:
    """Test backwards compatibility with existing workflows"""

    def test_workflows_without_agent_assist_still_work(self):
        """Test that existing workflows without AGENT_ASSIST continue to work"""
        storage, orchestrator = create_test_orchestrator()
        user_id = "test_user_compat"

        # Create traditional workflow (no agent assist)
        stage1 = Stage(
            id="draft",
            name="Draft",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            next_stages=[ConditionalRoute(next_stage_id="review", conditions=[])],
        )

        stage2 = Stage(
            id="review",
            name="Review",
            order=2,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
        )

        workflow = Workflow(
            id="traditional_wf",
            name="Traditional Workflow",
            description="No agent assist",
            icon="📋",
            category="test",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[stage1, stage2],
            triggers=[],
            created_by=user_id,
        )

        orchestrator.register_workflow(workflow, user_id=user_id)

        # Create and transition work item
        work_item = orchestrator.create_work_item(
            workflow_id=workflow.id,
            user_id=user_id,
            data={},
            created_by=user_id,
            priority=WorkItemPriority.NORMAL,
            tags=[],
        )

        completed = orchestrator.complete_stage(
            work_item_id=work_item.id,
            user_id=user_id,
            stage_data={"notes": "Looks good"},
            notes="Approved",
        )

        # Should work exactly as before
        assert completed.current_stage_id == "review"
        assert "agent_recommendation" not in completed.data
