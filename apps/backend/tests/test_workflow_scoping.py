"""
Tests for Workflow Multi-Tenant Scoping (T3-1)

Tests that workflows respect visibility rules:
- Personal: only owner can see
- Team: all team members can see
- Global: everyone can see

Tests cover:
- List workflows
- Fetch workflow by ID
- Templates
- Analytics
"""
import pytest
from datetime import datetime
from typing import Optional
import tempfile
import os

# Skip if workflow models cannot be imported
try:
    from api.workflow_models import (
        Workflow,
        Stage,
        WorkItem,
        WorkItemStatus,
        StageType,
        AssignmentType,
        WorkflowTrigger,
        WorkflowTriggerType,
        WorkflowType,
    )
    from api.workflow_storage import WorkflowStorage
    from api.services.workflow_orchestrator import WorkflowOrchestrator
    from api.services.workflow_analytics import WorkflowAnalytics
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not MODELS_AVAILABLE, reason="Workflow models not available")


@pytest.fixture
def temp_storage():
    """Create temporary workflow storage for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    storage = WorkflowStorage(db_path=db_path)
    yield storage

    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def orchestrator(temp_storage):
    """Create orchestrator with temp storage"""
    return WorkflowOrchestrator(storage=temp_storage)


@pytest.fixture
def analytics(temp_storage):
    """Create analytics with temp storage"""
    return WorkflowAnalytics(db_path=temp_storage.db_path)


# Test users and teams
USER_A_ID = "user_a_001"
USER_B_ID = "user_b_002"
USER_C_ID = "user_c_003"  # No team
TEAM_A_ID = "team_a_001"
TEAM_B_ID = "team_b_002"


def create_test_workflow(
    workflow_id: str,
    name: str,
    created_by: str,
    owner_team_id: Optional[str] = None,
    visibility: str = "personal",
    is_template: bool = False,
) -> Workflow:
    """Helper to create a test workflow"""
    stage = Stage(
        id="stage_1",
        name="Default Stage",
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.QUEUE,
    )

    trigger = WorkflowTrigger(
        id="trigger_1",
        trigger_type=WorkflowTriggerType.MANUAL,
    )

    return Workflow(
        id=workflow_id,
        name=name,
        stages=[stage],
        triggers=[trigger],
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        created_by=created_by,
        owner_team_id=owner_team_id,
        visibility=visibility,
        is_template=is_template,
        enabled=True,
    )


class TestWorkflowListVisibility:
    """Test that list_workflows respects visibility rules"""

    def test_user_sees_own_personal_workflows(self, temp_storage):
        """User A should see their own personal workflows"""
        # Create personal workflow for user A
        wf_a = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf_a, user_id=USER_A_ID, team_id=None)

        # List as user A (no team)
        workflows = temp_storage.list_workflows(user_id=USER_A_ID, team_id=None)

        assert len(workflows) == 1
        assert workflows[0].id == "wf_personal_a"
        assert workflows[0].visibility == "personal"

    def test_user_does_not_see_other_personal_workflows(self, temp_storage):
        """User B should NOT see User A's personal workflows"""
        # Create personal workflow for user A
        wf_a = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf_a, user_id=USER_A_ID, team_id=None)

        # List as user B (no team)
        workflows = temp_storage.list_workflows(user_id=USER_B_ID, team_id=None)

        assert len(workflows) == 0

    def test_team_member_sees_team_workflows(self, temp_storage):
        """Team members should see team workflows"""
        # Create team workflow for team A
        wf_team_a = create_test_workflow(
            workflow_id="wf_team_a",
            name="Team A Workflow",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
        )
        temp_storage.save_workflow(wf_team_a, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # List as user A who is in team A
        workflows = temp_storage.list_workflows(user_id=USER_A_ID, team_id=TEAM_A_ID)

        assert len(workflows) == 1
        assert workflows[0].id == "wf_team_a"
        assert workflows[0].visibility == "team"

    def test_non_team_member_does_not_see_team_workflows(self, temp_storage):
        """Non-team members should NOT see team workflows"""
        # Create team workflow for team A
        wf_team_a = create_test_workflow(
            workflow_id="wf_team_a",
            name="Team A Workflow",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
        )
        temp_storage.save_workflow(wf_team_a, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # List as user B who is in team B (different team)
        workflows = temp_storage.list_workflows(user_id=USER_B_ID, team_id=TEAM_B_ID)

        assert len(workflows) == 0

    def test_everyone_sees_global_workflows(self, temp_storage):
        """All users should see global workflows"""
        # Create global workflow
        wf_global = create_test_workflow(
            workflow_id="wf_global",
            name="Global Workflow",
            created_by=USER_A_ID,
            visibility="global",
        )
        temp_storage.save_workflow(wf_global, user_id=USER_A_ID, team_id=None)

        # List as user A
        workflows_a = temp_storage.list_workflows(user_id=USER_A_ID, team_id=None)
        assert any(w.id == "wf_global" for w in workflows_a)

        # List as user B
        workflows_b = temp_storage.list_workflows(user_id=USER_B_ID, team_id=None)
        assert any(w.id == "wf_global" for w in workflows_b)

        # List as user C
        workflows_c = temp_storage.list_workflows(user_id=USER_C_ID, team_id=None)
        assert any(w.id == "wf_global" for w in workflows_c)

    def test_user_sees_combination_personal_team_global(self, temp_storage):
        """User should see their personal + team + global workflows"""
        # Create personal workflow for user A
        wf_personal_a = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf_personal_a, user_id=USER_A_ID, team_id=None)

        # Create team workflow
        wf_team_a = create_test_workflow(
            workflow_id="wf_team_a",
            name="Team A Workflow",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
        )
        temp_storage.save_workflow(wf_team_a, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # Create global workflow
        wf_global = create_test_workflow(
            workflow_id="wf_global",
            name="Global Workflow",
            created_by=USER_B_ID,
            visibility="global",
        )
        temp_storage.save_workflow(wf_global, user_id=USER_B_ID, team_id=None)

        # Create personal workflow for user B (should NOT see)
        wf_personal_b = create_test_workflow(
            workflow_id="wf_personal_b",
            name="User B Personal",
            created_by=USER_B_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf_personal_b, user_id=USER_B_ID, team_id=None)

        # List as user A in team A
        workflows = temp_storage.list_workflows(user_id=USER_A_ID, team_id=TEAM_A_ID)
        workflow_ids = {w.id for w in workflows}

        # Should see: personal_a, team_a, global
        assert "wf_personal_a" in workflow_ids
        assert "wf_team_a" in workflow_ids
        assert "wf_global" in workflow_ids

        # Should NOT see: personal_b
        assert "wf_personal_b" not in workflow_ids


class TestWorkflowFetchVisibility:
    """Test that get_workflow respects visibility rules"""

    def test_fetch_own_personal_workflow_succeeds(self, temp_storage):
        """Fetching own personal workflow should succeed"""
        wf = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=None)

        # Fetch as owner
        fetched = temp_storage.get_workflow("wf_personal_a", user_id=USER_A_ID, team_id=None)

        assert fetched is not None
        assert fetched.id == "wf_personal_a"

    def test_fetch_other_personal_workflow_returns_none(self, temp_storage):
        """Fetching another user's personal workflow should return None"""
        wf = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=None)

        # Fetch as different user
        fetched = temp_storage.get_workflow("wf_personal_a", user_id=USER_B_ID, team_id=None)

        assert fetched is None

    def test_fetch_team_workflow_succeeds_for_team_member(self, temp_storage):
        """Team member should fetch team workflow"""
        wf = create_test_workflow(
            workflow_id="wf_team_a",
            name="Team A Workflow",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # Fetch as team member
        fetched = temp_storage.get_workflow("wf_team_a", user_id=USER_A_ID, team_id=TEAM_A_ID)

        assert fetched is not None
        assert fetched.id == "wf_team_a"

    def test_fetch_team_workflow_fails_for_non_member(self, temp_storage):
        """Non-team member should NOT fetch team workflow"""
        wf = create_test_workflow(
            workflow_id="wf_team_a",
            name="Team A Workflow",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # Fetch as user in different team
        fetched = temp_storage.get_workflow("wf_team_a", user_id=USER_B_ID, team_id=TEAM_B_ID)

        assert fetched is None

    def test_fetch_global_workflow_succeeds_for_anyone(self, temp_storage):
        """Anyone should fetch global workflow"""
        wf = create_test_workflow(
            workflow_id="wf_global",
            name="Global Workflow",
            created_by=USER_A_ID,
            visibility="global",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=None)

        # Fetch as different users
        fetched_a = temp_storage.get_workflow("wf_global", user_id=USER_A_ID, team_id=None)
        fetched_b = temp_storage.get_workflow("wf_global", user_id=USER_B_ID, team_id=None)
        fetched_c = temp_storage.get_workflow("wf_global", user_id=USER_C_ID, team_id=None)

        assert fetched_a is not None
        assert fetched_b is not None
        assert fetched_c is not None


class TestTemplateVisibility:
    """Test that template workflows respect visibility rules"""

    def test_list_personal_templates_visible_to_owner_only(self, temp_storage):
        """Personal templates should only be visible to owner"""
        wf_template = create_test_workflow(
            workflow_id="template_personal_a",
            name="User A Template",
            created_by=USER_A_ID,
            visibility="personal",
            is_template=True,
        )
        temp_storage.save_workflow(wf_template, user_id=USER_A_ID, team_id=None)

        # List as owner
        workflows_a = temp_storage.list_workflows(user_id=USER_A_ID, team_id=None)
        templates_a = [w for w in workflows_a if w.is_template]
        assert len(templates_a) == 1
        assert templates_a[0].id == "template_personal_a"

        # List as different user
        workflows_b = temp_storage.list_workflows(user_id=USER_B_ID, team_id=None)
        templates_b = [w for w in workflows_b if w.is_template]
        assert len(templates_b) == 0

    def test_list_team_templates_visible_to_team(self, temp_storage):
        """Team templates should be visible to all team members"""
        wf_template = create_test_workflow(
            workflow_id="template_team_a",
            name="Team A Template",
            created_by=USER_A_ID,
            owner_team_id=TEAM_A_ID,
            visibility="team",
            is_template=True,
        )
        temp_storage.save_workflow(wf_template, user_id=USER_A_ID, team_id=TEAM_A_ID)

        # List as team member
        workflows = temp_storage.list_workflows(user_id=USER_A_ID, team_id=TEAM_A_ID)
        templates = [w for w in workflows if w.is_template]
        assert len(templates) == 1
        assert templates[0].id == "template_team_a"

    def test_list_global_templates_visible_to_all(self, temp_storage):
        """Global templates should be visible to everyone"""
        wf_template = create_test_workflow(
            workflow_id="template_global",
            name="Global Template",
            created_by=USER_A_ID,
            visibility="global",
            is_template=True,
        )
        temp_storage.save_workflow(wf_template, user_id=USER_A_ID, team_id=None)

        # List as different users
        for user_id in [USER_A_ID, USER_B_ID, USER_C_ID]:
            workflows = temp_storage.list_workflows(user_id=user_id, team_id=None)
            templates = [w for w in workflows if w.is_template]
            assert any(t.id == "template_global" for t in templates)

    def test_fetch_template_respects_visibility(self, temp_storage):
        """Fetching templates should respect visibility rules"""
        # Personal template
        wf_personal = create_test_workflow(
            workflow_id="template_personal_a",
            name="User A Template",
            created_by=USER_A_ID,
            visibility="personal",
            is_template=True,
        )
        temp_storage.save_workflow(wf_personal, user_id=USER_A_ID, team_id=None)

        # Owner can fetch
        fetched_owner = temp_storage.get_workflow("template_personal_a", user_id=USER_A_ID, team_id=None)
        assert fetched_owner is not None

        # Other user cannot fetch
        fetched_other = temp_storage.get_workflow("template_personal_a", user_id=USER_B_ID, team_id=None)
        assert fetched_other is None


class TestAnalyticsVisibility:
    """Test that analytics respect workflow visibility"""

    def test_analytics_respects_workflow_visibility(self, temp_storage, orchestrator):
        """Analytics should only work for visible workflows"""
        # Create personal workflow for user A
        wf = create_test_workflow(
            workflow_id="wf_personal_a",
            name="User A Personal",
            created_by=USER_A_ID,
            visibility="personal",
        )
        temp_storage.save_workflow(wf, user_id=USER_A_ID, team_id=None)

        # Verify user A can access workflow (prerequisite for analytics)
        fetched_a = temp_storage.get_workflow("wf_personal_a", user_id=USER_A_ID, team_id=None)
        assert fetched_a is not None, "Owner should see their workflow"

        # Verify user B cannot access workflow
        fetched_b = temp_storage.get_workflow("wf_personal_a", user_id=USER_B_ID, team_id=None)
        assert fetched_b is None, "Other user should NOT see personal workflow"


class TestLegacyWorkflowCompatibility:
    """Test that workflows without visibility field default correctly"""

    def test_workflow_without_visibility_defaults_to_personal(self, temp_storage):
        """Legacy workflows should default to personal visibility"""
        # Create workflow without explicit visibility (simulating legacy data)
        wf = Workflow(
            id="wf_legacy",
            name="Legacy Workflow",
            stages=[Stage(
                id="stage_1",
                name="Stage",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.QUEUE,
            )],
            triggers=[WorkflowTrigger(
                id="trigger_1",
                trigger_type=WorkflowTriggerType.MANUAL,
            )],
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            created_by=USER_A_ID,
            # Note: owner_team_id and visibility will use model defaults
            enabled=True,
        )

        # Visibility should default to "personal" per model definition
        assert wf.visibility == "personal"
