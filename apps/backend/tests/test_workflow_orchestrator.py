"""
Comprehensive tests for api/services/workflow_orchestrator.py

Tests the core workflow orchestration engine including:
- State machine for work item lifecycle
- Stage transitions with conditional routing
- SLA tracking and overdue detection
- Queue management and assignment

Coverage targets:
- WorkflowOrchestrator class initialization
- Workflow registration and retrieval
- Work item creation and lifecycle
- Conditional routing evaluation
- Automation stage execution
- Queue and SLA management
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from api.services.workflow_orchestrator import WorkflowOrchestrator
from api.services.workflow_orchestrator_routing import evaluate_conditions
from api.services.workflow_orchestrator_utils import (
    priority_score,
    find_stage,
    apply_auto_assignment,
)
from api.services.workflow_automation import (
    execute_automation_stage,
    run_local_ai_automation,
    run_custom_automation,
)
from api.workflow_models import (
    WorkItem,
    Workflow,
    Stage,
    StageTransition,
    WorkItemStatus,
    WorkItemPriority,
    StageType,
    AssignmentType,
    ConditionOperator,
    RoutingCondition,
    ConditionalRoute,
    AutomationConfig,
)


# ========== Fixtures ==========

@pytest.fixture
def mock_storage():
    """Create a mock storage layer"""
    storage = MagicMock()
    storage.list_workflows.return_value = []
    storage.list_work_items.return_value = []
    storage.get_workflow.return_value = None
    storage.get_work_item.return_value = None
    storage.save_workflow.return_value = None
    storage.save_work_item.return_value = None
    return storage


@pytest.fixture
def orchestrator():
    """Create orchestrator without storage"""
    return WorkflowOrchestrator()


@pytest.fixture
def orchestrator_with_storage(mock_storage):
    """Create orchestrator with mock storage"""
    return WorkflowOrchestrator(storage=mock_storage)


@pytest.fixture
def sample_stage():
    """Create a sample stage"""
    return Stage(
        id="stage_1",
        name="Initial Review",
        description="First review stage",
        order=1,
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.ROLE,
        role_name="reviewer",
        sla_minutes=60,
    )


@pytest.fixture
def sample_stage_with_conditions():
    """Create a stage with conditional routing"""
    return Stage(
        id="stage_1",
        name="Decision Stage",
        order=1,
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.QUEUE,
        next_stages=[
            ConditionalRoute(
                next_stage_id="stage_approved",
                conditions=[
                    RoutingCondition(
                        field="approved",
                        operator=ConditionOperator.IS_TRUE,
                        value=True
                    )
                ],
                description="Route to approval"
            ),
            ConditionalRoute(
                next_stage_id="stage_rejected",
                conditions=[
                    RoutingCondition(
                        field="approved",
                        operator=ConditionOperator.IS_FALSE,
                        value=False
                    )
                ],
                description="Route to rejection"
            ),
        ]
    )


@pytest.fixture
def sample_workflow(sample_stage):
    """Create a sample workflow"""
    return Workflow(
        id="workflow_1",
        name="Test Workflow",
        description="A test workflow",
        category="test",
        stages=[sample_stage],
        triggers=[],
        enabled=True,
        created_by="test_user",
    )


@pytest.fixture
def multi_stage_workflow():
    """Create a multi-stage workflow"""
    stage1 = Stage(
        id="stage_1",
        name="Review",
        order=1,
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.ROLE,
        role_name="reviewer",
        next_stages=[
            ConditionalRoute(next_stage_id="stage_2")
        ]
    )
    stage2 = Stage(
        id="stage_2",
        name="Approval",
        order=2,
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.ROLE,
        role_name="approver",
        next_stages=[
            ConditionalRoute(next_stage_id="stage_3")
        ]
    )
    stage3 = Stage(
        id="stage_3",
        name="Complete",
        order=3,
        stage_type=StageType.HUMAN,
        assignment_type=AssignmentType.QUEUE,
    )
    return Workflow(
        id="multi_workflow",
        name="Multi-Stage Workflow",
        stages=[stage1, stage2, stage3],
        triggers=[],
        enabled=True,
        created_by="test_user",
    )


@pytest.fixture
def sample_user_id():
    """Sample user ID"""
    return "user_123"


# ========== Initialization Tests ==========

class TestWorkflowOrchestratorInit:
    """Tests for WorkflowOrchestrator initialization"""

    def test_init_without_storage(self):
        """Test initialization without storage"""
        orchestrator = WorkflowOrchestrator()

        assert orchestrator.storage is None
        assert orchestrator.active_work_items == {}
        assert orchestrator.workflows == {}

    def test_init_with_storage(self, mock_storage):
        """Test initialization with storage"""
        orchestrator = WorkflowOrchestrator(storage=mock_storage)

        assert orchestrator.storage == mock_storage

    def test_load_workflows_from_storage(self, mock_storage, sample_workflow, sample_user_id):
        """Test loading workflows from storage"""
        mock_storage.list_workflows.return_value = [sample_workflow]
        orchestrator = WorkflowOrchestrator(storage=mock_storage)

        orchestrator._load_workflows_from_storage(sample_user_id)

        assert sample_workflow.id in orchestrator.workflows
        mock_storage.list_workflows.assert_called_with(user_id=sample_user_id)

    def test_load_workflows_no_storage(self, sample_user_id):
        """Test loading workflows without storage does nothing"""
        orchestrator = WorkflowOrchestrator()

        orchestrator._load_workflows_from_storage(sample_user_id)

        assert orchestrator.workflows == {}

    def test_load_active_work_items_from_storage(self, mock_storage, sample_user_id):
        """Test loading active work items from storage"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        mock_storage.list_work_items.return_value = [work_item]
        orchestrator = WorkflowOrchestrator(storage=mock_storage)

        orchestrator._load_active_work_items_from_storage(sample_user_id)

        assert work_item.id in orchestrator.active_work_items


# ========== Workflow Registration Tests ==========

class TestWorkflowRegistration:
    """Tests for workflow registration"""

    def test_register_workflow_without_storage(self, orchestrator, sample_workflow, sample_user_id):
        """Test registering workflow without storage"""
        orchestrator.register_workflow(sample_workflow, sample_user_id)

        assert sample_workflow.id in orchestrator.workflows

    def test_register_workflow_with_storage(self, orchestrator_with_storage, mock_storage, sample_workflow, sample_user_id):
        """Test registering workflow with storage"""
        orchestrator_with_storage.register_workflow(sample_workflow, sample_user_id)

        mock_storage.save_workflow.assert_called_once_with(
            sample_workflow, user_id=sample_user_id, team_id=None
        )

    def test_register_workflow_with_team(self, orchestrator_with_storage, mock_storage, sample_workflow, sample_user_id):
        """Test registering workflow with team ID"""
        team_id = "team_456"
        orchestrator_with_storage.register_workflow(sample_workflow, sample_user_id, team_id=team_id)

        mock_storage.save_workflow.assert_called_once_with(
            sample_workflow, user_id=sample_user_id, team_id=team_id
        )

    def test_get_workflow_from_memory(self, orchestrator, sample_workflow, sample_user_id):
        """Test getting workflow from memory"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.get_workflow(sample_workflow.id, sample_user_id)

        assert result == sample_workflow

    def test_get_workflow_from_storage(self, orchestrator_with_storage, mock_storage, sample_workflow, sample_user_id):
        """Test getting workflow from storage"""
        mock_storage.get_workflow.return_value = sample_workflow

        result = orchestrator_with_storage.get_workflow(sample_workflow.id, sample_user_id)

        assert result == sample_workflow

    def test_get_workflow_not_found(self, orchestrator, sample_user_id):
        """Test getting non-existent workflow"""
        result = orchestrator.get_workflow("nonexistent", sample_user_id)

        assert result is None


# ========== List Workflows Tests ==========

class TestListWorkflows:
    """Tests for listing workflows"""

    def test_list_workflows_from_storage(self, orchestrator_with_storage, mock_storage, sample_workflow, sample_user_id):
        """Test listing workflows from storage"""
        mock_storage.list_workflows.return_value = [sample_workflow]

        result = orchestrator_with_storage.list_workflows(sample_user_id)

        assert len(result) == 1
        assert result[0] == sample_workflow

    def test_list_workflows_with_filters(self, orchestrator_with_storage, mock_storage, sample_user_id):
        """Test listing workflows with filters"""
        mock_storage.list_workflows.return_value = []

        orchestrator_with_storage.list_workflows(
            sample_user_id,
            category="test",
            enabled_only=True,
            team_id="team_1",
            workflow_type="local"
        )

        mock_storage.list_workflows.assert_called_with(
            user_id=sample_user_id,
            category="test",
            enabled_only=True,
            team_id="team_1",
            workflow_type="local"
        )

    def test_list_workflows_in_memory_with_category_filter(self, orchestrator, sample_workflow, sample_user_id):
        """Test listing workflows from memory with category filter"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.list_workflows(sample_user_id, category="test")

        assert len(result) == 1

    def test_list_workflows_in_memory_enabled_only(self, orchestrator, sample_workflow, sample_user_id):
        """Test listing only enabled workflows"""
        disabled_workflow = Workflow(
            id="disabled",
            name="Disabled Workflow",
            stages=[],
            triggers=[],
            enabled=False,
            created_by="test_user",
        )
        orchestrator.workflows[sample_workflow.id] = sample_workflow
        orchestrator.workflows[disabled_workflow.id] = disabled_workflow

        result = orchestrator.list_workflows(sample_user_id, enabled_only=True)

        assert len(result) == 1
        assert result[0].id == sample_workflow.id


# ========== Work Item Creation Tests ==========

class TestWorkItemCreation:
    """Tests for work item creation"""

    def test_create_work_item_success(self, orchestrator, sample_workflow, sample_user_id):
        """Test creating a work item"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={"key": "value"},
            created_by=sample_user_id,
        )

        assert result.workflow_id == sample_workflow.id
        assert result.status == WorkItemStatus.PENDING
        assert result.data == {"key": "value"}
        assert result.id in orchestrator.active_work_items

    def test_create_work_item_with_priority(self, orchestrator, sample_workflow, sample_user_id):
        """Test creating work item with priority"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={},
            created_by=sample_user_id,
            priority=WorkItemPriority.URGENT,
        )

        assert result.priority == WorkItemPriority.URGENT

    def test_create_work_item_with_tags(self, orchestrator, sample_workflow, sample_user_id):
        """Test creating work item with tags"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={},
            created_by=sample_user_id,
            tags=["tag1", "tag2"],
        )

        assert result.tags == ["tag1", "tag2"]

    def test_create_work_item_workflow_not_found(self, orchestrator, sample_user_id):
        """Test creating work item with non-existent workflow"""
        with pytest.raises(ValueError, match="Workflow not found"):
            orchestrator.create_work_item(
                workflow_id="nonexistent",
                user_id=sample_user_id,
                data={},
                created_by=sample_user_id,
            )

    def test_create_work_item_no_stages(self, orchestrator, sample_user_id):
        """Test creating work item with workflow that has no stages"""
        empty_workflow = Workflow(
            id="empty",
            name="Empty Workflow",
            stages=[],
            triggers=[],
            created_by="test_user",
        )
        orchestrator.workflows[empty_workflow.id] = empty_workflow

        with pytest.raises(ValueError, match="Workflow has no stages"):
            orchestrator.create_work_item(
                workflow_id=empty_workflow.id,
                user_id=sample_user_id,
                data={},
                created_by=sample_user_id,
            )

    def test_create_work_item_with_sla(self, orchestrator, sample_workflow, sample_stage, sample_user_id):
        """Test work item gets SLA from stage"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={},
            created_by=sample_user_id,
        )

        # sample_stage has sla_minutes=60
        assert result.sla_due_at is not None

    def test_create_work_item_records_transition(self, orchestrator, sample_workflow, sample_user_id):
        """Test work item creation records initial transition"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={},
            created_by=sample_user_id,
        )

        assert len(result.history) == 1
        assert result.history[0].from_stage_id is None


# ========== Work Item Lifecycle Tests ==========

class TestWorkItemLifecycle:
    """Tests for work item lifecycle operations"""

    def test_claim_work_item_success(self, orchestrator, sample_user_id):
        """Test claiming a work item"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.claim_work_item(work_item.id, sample_user_id)

        assert result.status == WorkItemStatus.CLAIMED
        assert result.assigned_to == sample_user_id
        assert result.claimed_at is not None

    def test_claim_work_item_not_found(self, orchestrator, sample_user_id):
        """Test claiming non-existent work item"""
        with pytest.raises(ValueError, match="Work item not found"):
            orchestrator.claim_work_item("nonexistent", sample_user_id)

    def test_claim_work_item_already_claimed(self, orchestrator, sample_user_id):
        """Test claiming already claimed work item"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.CLAIMED,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        with pytest.raises(ValueError, match="cannot be claimed"):
            orchestrator.claim_work_item(work_item.id, sample_user_id)

    def test_start_work_success(self, orchestrator, sample_user_id):
        """Test starting work on an item"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.CLAIMED,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.start_work(work_item.id, sample_user_id)

        assert result.status == WorkItemStatus.IN_PROGRESS

    def test_start_work_not_assigned(self, orchestrator, sample_user_id):
        """Test starting work when not assigned to user"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.CLAIMED,
            assigned_to="other_user",
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        with pytest.raises(ValueError, match="not assigned to user"):
            orchestrator.start_work(work_item.id, sample_user_id)


# ========== Stage Completion Tests ==========

class TestStageCompletion:
    """Tests for stage completion and transitions"""

    def test_complete_stage_transition_to_next(self, orchestrator, multi_stage_workflow, sample_user_id):
        """Test completing stage and transitioning to next"""
        orchestrator.workflows[multi_stage_workflow.id] = multi_stage_workflow

        work_item = WorkItem(
            workflow_id=multi_stage_workflow.id,
            workflow_name=multi_stage_workflow.name,
            current_stage_id="stage_1",
            current_stage_name="Review",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
            data={},
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={"reviewed": True},
            notes="Reviewed and approved"
        )

        assert result.current_stage_id == "stage_2"
        assert result.status == WorkItemStatus.PENDING
        assert result.data.get("reviewed") is True

    def test_complete_final_stage(self, orchestrator, sample_workflow, sample_user_id):
        """Test completing final stage marks workflow complete"""
        # Modify workflow to have no next stages
        sample_workflow.stages[0].next_stages = []
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        work_item = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="stage_1",
            current_stage_name="Initial Review",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
            data={},
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={},
        )

        assert result.status == WorkItemStatus.COMPLETED
        assert result.completed_at is not None

    def test_complete_stage_work_item_not_found(self, orchestrator, sample_user_id):
        """Test completing stage for non-existent work item"""
        with pytest.raises(ValueError, match="Work item not found"):
            orchestrator.complete_stage(
                "nonexistent",
                sample_user_id,
                stage_data={},
            )


# ========== Conditional Routing Tests ==========

class TestConditionalRouting:
    """Tests for conditional routing evaluation (uses standalone evaluate_conditions function)"""

    def test_evaluate_equals_condition_true(self):
        """Test EQUALS condition evaluates correctly"""
        conditions = [
            RoutingCondition(
                field="status",
                operator=ConditionOperator.EQUALS,
                value="approved"
            )
        ]

        result = evaluate_conditions(conditions, {"status": "approved"})

        assert result is True

    def test_evaluate_equals_condition_false(self):
        """Test EQUALS condition fails correctly"""
        conditions = [
            RoutingCondition(
                field="status",
                operator=ConditionOperator.EQUALS,
                value="approved"
            )
        ]

        result = evaluate_conditions(conditions, {"status": "rejected"})

        assert result is False

    def test_evaluate_not_equals_condition(self):
        """Test NOT_EQUALS condition"""
        conditions = [
            RoutingCondition(
                field="status",
                operator=ConditionOperator.NOT_EQUALS,
                value="rejected"
            )
        ]

        result = evaluate_conditions(conditions, {"status": "approved"})

        assert result is True

    def test_evaluate_greater_than_condition(self):
        """Test GREATER_THAN condition"""
        conditions = [
            RoutingCondition(
                field="amount",
                operator=ConditionOperator.GREATER_THAN,
                value=100
            )
        ]

        assert evaluate_conditions(conditions, {"amount": 150}) is True
        assert evaluate_conditions(conditions, {"amount": 50}) is False

    def test_evaluate_less_than_condition(self):
        """Test LESS_THAN condition"""
        conditions = [
            RoutingCondition(
                field="amount",
                operator=ConditionOperator.LESS_THAN,
                value=100
            )
        ]

        assert evaluate_conditions(conditions, {"amount": 50}) is True
        assert evaluate_conditions(conditions, {"amount": 150}) is False

    def test_evaluate_contains_condition(self):
        """Test CONTAINS condition"""
        conditions = [
            RoutingCondition(
                field="description",
                operator=ConditionOperator.CONTAINS,
                value="urgent"
            )
        ]

        assert evaluate_conditions(conditions, {"description": "This is urgent!"}) is True
        assert evaluate_conditions(conditions, {"description": "Normal task"}) is False

    def test_evaluate_not_contains_condition(self):
        """Test NOT_CONTAINS condition"""
        conditions = [
            RoutingCondition(
                field="description",
                operator=ConditionOperator.NOT_CONTAINS,
                value="spam"
            )
        ]

        assert evaluate_conditions(conditions, {"description": "Valid content"}) is True
        assert evaluate_conditions(conditions, {"description": "This is spam"}) is False

    def test_evaluate_is_true_condition(self):
        """Test IS_TRUE condition"""
        conditions = [
            RoutingCondition(
                field="approved",
                operator=ConditionOperator.IS_TRUE,
                value=True
            )
        ]

        assert evaluate_conditions(conditions, {"approved": True}) is True
        assert evaluate_conditions(conditions, {"approved": False}) is False

    def test_evaluate_is_false_condition(self):
        """Test IS_FALSE condition"""
        conditions = [
            RoutingCondition(
                field="rejected",
                operator=ConditionOperator.IS_FALSE,
                value=False
            )
        ]

        assert evaluate_conditions(conditions, {"rejected": False}) is True
        assert evaluate_conditions(conditions, {"rejected": True}) is False

    def test_evaluate_multiple_conditions_all_must_pass(self):
        """Test AND logic for multiple conditions"""
        conditions = [
            RoutingCondition(field="status", operator=ConditionOperator.EQUALS, value="approved"),
            RoutingCondition(field="amount", operator=ConditionOperator.GREATER_THAN, value=100),
        ]

        assert evaluate_conditions(conditions, {"status": "approved", "amount": 150}) is True
        assert evaluate_conditions(conditions, {"status": "approved", "amount": 50}) is False
        assert evaluate_conditions(conditions, {"status": "rejected", "amount": 150}) is False

    def test_evaluate_missing_field(self):
        """Test condition with missing field"""
        conditions = [
            RoutingCondition(
                field="nonexistent",
                operator=ConditionOperator.EQUALS,
                value="value"
            )
        ]

        result = evaluate_conditions(conditions, {})

        assert result is False


# ========== Assignment Tests ==========

class TestAssignment:
    """Tests for auto-assignment logic (uses standalone apply_auto_assignment function)"""

    def test_auto_assign_specific_user(self):
        """Test auto-assignment to specific user"""
        stage = Stage(
            id="s1",
            name="Review",
            order=1,
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.SPECIFIC_USER,
            assigned_user_id="specific_user",
        )
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Review",
            status=WorkItemStatus.PENDING,
            created_by="creator",
        )

        result = apply_auto_assignment(work_item, stage)

        assert result is True
        assert work_item.assigned_to == "specific_user"
        assert work_item.status == WorkItemStatus.CLAIMED

    def test_auto_assign_automation(self):
        """Test auto-assignment to automation"""
        stage = Stage(
            id="s1",
            name="Auto Process",
            order=1,
            stage_type=StageType.AUTOMATION,
            assignment_type=AssignmentType.AUTOMATION,
        )
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Auto Process",
            status=WorkItemStatus.PENDING,
            created_by="creator",
        )

        result = apply_auto_assignment(work_item, stage)

        assert result is True
        assert work_item.assigned_to == "system"
        assert work_item.status == WorkItemStatus.IN_PROGRESS


# ========== Queue Management Tests ==========

class TestQueueManagement:
    """Tests for queue management"""

    def test_get_queue_for_role(self, orchestrator, sample_workflow, sample_user_id):
        """Test getting queue for a role"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        work_item = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="stage_1",
            current_stage_name="Initial Review",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.get_queue_for_role(
            sample_workflow.id,
            "reviewer",
            sample_user_id
        )

        assert len(result) == 1
        assert result[0].id == work_item.id

    def test_get_queue_for_role_empty(self, orchestrator, sample_workflow, sample_user_id):
        """Test getting queue for role with no matching items"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.get_queue_for_role(
            sample_workflow.id,
            "nonexistent_role",
            sample_user_id
        )

        assert len(result) == 0

    def test_get_my_active_work(self, orchestrator, sample_user_id):
        """Test getting user's active work items"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.get_my_active_work(sample_user_id)

        assert len(result) == 1
        assert result[0].id == work_item.id

    def test_get_my_active_work_excludes_others(self, orchestrator, sample_user_id):
        """Test active work excludes other users' items"""
        my_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
        )
        other_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to="other_user",
            created_by="other_user",
        )
        orchestrator.active_work_items[my_item.id] = my_item
        orchestrator.active_work_items[other_item.id] = other_item

        result = orchestrator.get_my_active_work(sample_user_id)

        assert len(result) == 1
        assert result[0].id == my_item.id


# ========== SLA Tracking Tests ==========

class TestSLATracking:
    """Tests for SLA tracking"""

    def test_check_overdue_items_detects_overdue(self, orchestrator, sample_user_id):
        """Test detecting overdue items"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
            sla_due_at=datetime.now(UTC) - timedelta(hours=1),  # Past due
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.check_overdue_items(sample_user_id)

        assert len(result) == 1
        assert result[0].is_overdue is True

    def test_check_overdue_items_skips_on_time(self, orchestrator, sample_user_id):
        """Test on-time items are not marked overdue"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
            sla_due_at=datetime.now(UTC) + timedelta(hours=1),  # Still in time
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.check_overdue_items(sample_user_id)

        assert len(result) == 0

    def test_check_overdue_items_skips_completed(self, orchestrator, sample_user_id):
        """Test completed items are not checked"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.COMPLETED,
            created_by=sample_user_id,
            sla_due_at=datetime.now(UTC) - timedelta(hours=1),  # Past due
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.check_overdue_items(sample_user_id)

        assert len(result) == 0


# ========== Statistics Tests ==========

class TestStatistics:
    """Tests for workflow statistics"""

    def test_get_workflow_statistics(self, orchestrator, sample_workflow, sample_user_id):
        """Test getting workflow statistics"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        # Create various work items
        pending = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        completed = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.COMPLETED,
            created_by=sample_user_id,
        )
        in_progress = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.IN_PROGRESS,
            created_by=sample_user_id,
        )
        overdue = WorkItem(
            workflow_id=sample_workflow.id,
            workflow_name=sample_workflow.name,
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
            is_overdue=True,
        )
        orchestrator.active_work_items[pending.id] = pending
        orchestrator.active_work_items[completed.id] = completed
        orchestrator.active_work_items[in_progress.id] = in_progress
        orchestrator.active_work_items[overdue.id] = overdue

        result = orchestrator.get_workflow_statistics(sample_workflow.id, sample_user_id)

        assert result["total_items"] == 4
        assert result["completed"] == 1
        assert result["pending"] == 2  # pending + overdue
        assert result["active"] == 1
        assert result["overdue"] == 1
        assert result["completion_rate"] == 25.0

    def test_get_workflow_statistics_empty(self, orchestrator, sample_workflow, sample_user_id):
        """Test statistics for empty workflow"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.get_workflow_statistics(sample_workflow.id, sample_user_id)

        assert result["total_items"] == 0
        assert result["completion_rate"] == 0


# ========== Utility Tests ==========

class TestUtilities:
    """Tests for utility functions (uses standalone find_stage and priority_score)"""

    def test_find_stage(self, sample_workflow):
        """Test finding stage by ID"""
        result = find_stage(sample_workflow, "stage_1")

        assert result is not None
        assert result.name == "Initial Review"

    def test_find_stage_not_found(self, sample_workflow):
        """Test finding non-existent stage"""
        result = find_stage(sample_workflow, "nonexistent")

        assert result is None

    def test_priority_score(self):
        """Test priority scoring"""
        assert priority_score(WorkItemPriority.LOW) == 1
        assert priority_score(WorkItemPriority.NORMAL) == 2
        assert priority_score(WorkItemPriority.HIGH) == 3
        assert priority_score(WorkItemPriority.URGENT) == 4


# ========== Automation Tests ==========

class TestAutomation:
    """Tests for automation stage execution"""

    def test_execute_automation_stage_no_config(self, orchestrator, sample_user_id):
        """Test automation stage with no config"""
        stage = Stage(
            id="s1",
            name="Auto",
            order=1,
            stage_type=StageType.AUTOMATION,
            assignment_type=AssignmentType.AUTOMATION,
            automation=None,
        )
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Auto",
            status=WorkItemStatus.IN_PROGRESS,
            created_by=sample_user_id,
            data={},
        )

        # Should not raise - call module function directly
        execute_automation_stage(work_item, stage, sample_user_id)

    def test_run_local_ai_automation(self, orchestrator, sample_user_id):
        """Test local AI automation execution"""
        automation = AutomationConfig(
            type="local_ai",
            ai_model="llama3",
            ai_prompt_template="Summarize: {content}",
        )
        stage = Stage(
            id="s1",
            name="AI Analysis",
            order=1,
            stage_type=StageType.AUTOMATION,
            assignment_type=AssignmentType.AUTOMATION,
            automation=automation,
        )
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="AI Analysis",
            status=WorkItemStatus.IN_PROGRESS,
            created_by=sample_user_id,
            data={"content": "Test content to summarize"},
        )

        run_local_ai_automation(work_item, stage, sample_user_id)

        assert "ai_automation" in work_item.data
        assert work_item.data["ai_automation"]["model"] == "llama3"
        assert work_item.data["ai_automation"]["status"] == "pending"

    def test_run_custom_automation(self, orchestrator, sample_user_id):
        """Test custom script automation execution"""
        automation = AutomationConfig(
            type="custom",
            custom_script_path="/scripts/process.py",
        )
        stage = Stage(
            id="s1",
            name="Custom Process",
            order=1,
            stage_type=StageType.AUTOMATION,
            assignment_type=AssignmentType.AUTOMATION,
            automation=automation,
        )
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Custom Process",
            status=WorkItemStatus.IN_PROGRESS,
            created_by=sample_user_id,
            data={},
        )

        run_custom_automation(work_item, stage, sample_user_id)

        assert "custom_automation" in work_item.data
        assert work_item.data["custom_automation"]["script"] == "/scripts/process.py"


# ========== List Work Items Tests ==========

class TestListWorkItems:
    """Tests for listing work items"""

    def test_list_work_items_basic(self, orchestrator, sample_user_id):
        """Test basic work item listing"""
        work_item = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.list_work_items(sample_user_id)

        assert len(result) == 1

    def test_list_work_items_with_workflow_filter(self, orchestrator, sample_user_id):
        """Test listing with workflow filter"""
        work_item1 = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        work_item2 = WorkItem(
            workflow_id="wf2",
            workflow_name="Test 2",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[work_item1.id] = work_item1
        orchestrator.active_work_items[work_item2.id] = work_item2

        result = orchestrator.list_work_items(sample_user_id, workflow_id="wf1")

        assert len(result) == 1
        assert result[0].workflow_id == "wf1"

    def test_list_work_items_with_status_filter(self, orchestrator, sample_user_id):
        """Test listing with status filter"""
        pending = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.PENDING,
            created_by=sample_user_id,
        )
        completed = WorkItem(
            workflow_id="wf1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Stage 1",
            status=WorkItemStatus.COMPLETED,
            created_by=sample_user_id,
        )
        orchestrator.active_work_items[pending.id] = pending
        orchestrator.active_work_items[completed.id] = completed

        result = orchestrator.list_work_items(sample_user_id, status=WorkItemStatus.PENDING)

        assert len(result) == 1
        assert result[0].status == WorkItemStatus.PENDING

    def test_list_work_items_with_limit(self, orchestrator, sample_user_id):
        """Test listing with limit"""
        for i in range(10):
            work_item = WorkItem(
                workflow_id="wf1",
                workflow_name="Test",
                current_stage_id="s1",
                current_stage_name="Stage 1",
                status=WorkItemStatus.PENDING,
                created_by=sample_user_id,
            )
            orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.list_work_items(sample_user_id, limit=5)

        assert len(result) == 5


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_work_item_with_unicode_data(self, orchestrator, sample_workflow, sample_user_id):
        """Test work item with unicode data"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data={"title": "日本語テスト", "description": "测试中文"},
            created_by=sample_user_id,
        )

        assert result.data["title"] == "日本語テスト"

    def test_work_item_with_nested_data(self, orchestrator, sample_workflow, sample_user_id):
        """Test work item with nested data"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        nested_data = {
            "user": {
                "name": "Test",
                "roles": ["admin", "user"]
            },
            "items": [{"id": 1}, {"id": 2}]
        }

        result = orchestrator.create_work_item(
            workflow_id=sample_workflow.id,
            user_id=sample_user_id,
            data=nested_data,
            created_by=sample_user_id,
        )

        assert result.data["user"]["name"] == "Test"
        assert len(result.data["items"]) == 2

    def test_concurrent_work_items_same_workflow(self, orchestrator, sample_workflow, sample_user_id):
        """Test multiple concurrent work items in same workflow"""
        orchestrator.workflows[sample_workflow.id] = sample_workflow

        items = []
        for i in range(5):
            item = orchestrator.create_work_item(
                workflow_id=sample_workflow.id,
                user_id=sample_user_id,
                data={"index": i},
                created_by=sample_user_id,
            )
            items.append(item)

        assert len(items) == 5
        assert len(set(item.id for item in items)) == 5  # All unique IDs

    def test_transition_resets_assignment(self, orchestrator, multi_stage_workflow, sample_user_id):
        """Test transitioning to new stage resets assignment"""
        orchestrator.workflows[multi_stage_workflow.id] = multi_stage_workflow

        work_item = WorkItem(
            workflow_id=multi_stage_workflow.id,
            workflow_name=multi_stage_workflow.name,
            current_stage_id="stage_1",
            current_stage_name="Review",
            status=WorkItemStatus.IN_PROGRESS,
            assigned_to=sample_user_id,
            created_by=sample_user_id,
            data={},
        )
        orchestrator.active_work_items[work_item.id] = work_item

        result = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={},
        )

        # Assignment should be reset for new stage
        assert result.assigned_to is None
        assert result.claimed_at is None


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for full workflow lifecycle"""

    def test_full_workflow_lifecycle(self, orchestrator, multi_stage_workflow, sample_user_id):
        """Test complete workflow lifecycle"""
        # Register workflow
        orchestrator.register_workflow(multi_stage_workflow, sample_user_id)

        # Create work item
        work_item = orchestrator.create_work_item(
            workflow_id=multi_stage_workflow.id,
            user_id=sample_user_id,
            data={"request": "Process this"},
            created_by=sample_user_id,
        )
        assert work_item.current_stage_id == "stage_1"
        assert work_item.status == WorkItemStatus.PENDING

        # Claim work item
        work_item = orchestrator.claim_work_item(work_item.id, sample_user_id)
        assert work_item.status == WorkItemStatus.CLAIMED

        # Start work
        work_item = orchestrator.start_work(work_item.id, sample_user_id)
        assert work_item.status == WorkItemStatus.IN_PROGRESS

        # Complete stage 1
        work_item = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={"reviewed": True},
        )
        assert work_item.current_stage_id == "stage_2"

        # Claim and complete stage 2
        work_item = orchestrator.claim_work_item(work_item.id, sample_user_id)
        work_item = orchestrator.start_work(work_item.id, sample_user_id)
        work_item = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={"approved": True},
        )
        assert work_item.current_stage_id == "stage_3"

        # Complete final stage
        work_item = orchestrator.claim_work_item(work_item.id, sample_user_id)
        work_item = orchestrator.start_work(work_item.id, sample_user_id)
        work_item = orchestrator.complete_stage(
            work_item.id,
            sample_user_id,
            stage_data={},
        )

        # Workflow should be complete
        assert work_item.status == WorkItemStatus.COMPLETED
        assert work_item.completed_at is not None
        assert len(work_item.history) == 4  # 3 transitions + initial

