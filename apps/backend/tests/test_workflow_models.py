"""
Comprehensive tests for api/workflow_models.py
Tests all enums, Pydantic models, validation, and serialization.
"""

import pytest
from datetime import datetime, UTC, timedelta
import uuid
import json

from api.workflow_models import (
    # Enums
    WorkflowTriggerType,
    StageType,
    WorkItemStatus,
    WorkItemPriority,
    AssignmentType,
    ConditionOperator,
    FieldType,
    WorkflowType,
    NotificationEvent,
    # Form models
    FormFieldOption,
    FormField,
    FormDefinition,
    # Routing models
    RoutingCondition,
    ConditionalRoute,
    # Automation
    AutomationConfig,
    # Stage
    Stage,
    # Workflow
    WorkflowTrigger,
    Workflow,
    # Work item related
    StageTransition,
    WorkItemAttachment,
    WorkItem,
    # Queue
    QueueFilter,
    Queue,
    # Notification
    Notification,
    # Roles
    WorkflowRole,
    UserRoleAssignment,
    # Metrics
    WorkflowMetrics,
    StageMetrics,
    # P2P sync
    WorkflowSyncMessage,
    WorkItemConflict,
    # API models
    CreateWorkItemRequest,
    ClaimWorkItemRequest,
    CompleteStageRequest,
    CreateWorkflowRequest,
)


# ============================================
# ENUM TESTS
# ============================================

class TestWorkflowTriggerType:
    """Tests for WorkflowTriggerType enum"""

    def test_all_trigger_types_exist(self):
        """All expected trigger types exist"""
        expected = ["MANUAL", "FORM_SUBMISSION", "SCHEDULE", "WEBHOOK", "EMAIL",
                    "FILE_UPLOAD", "EVENT", "ON_AGENT_EVENT", "ON_FILE_PATTERN"]
        for name in expected:
            assert hasattr(WorkflowTriggerType, name)

    def test_trigger_type_values(self):
        """Trigger type values are correct"""
        assert WorkflowTriggerType.MANUAL.value == "manual"
        assert WorkflowTriggerType.FORM_SUBMISSION.value == "form"
        assert WorkflowTriggerType.SCHEDULE.value == "schedule"
        assert WorkflowTriggerType.WEBHOOK.value == "webhook"
        assert WorkflowTriggerType.ON_AGENT_EVENT.value == "on_agent_event"

    def test_trigger_type_is_str_enum(self):
        """WorkflowTriggerType inherits from str"""
        assert isinstance(WorkflowTriggerType.MANUAL, str)
        assert WorkflowTriggerType.MANUAL == "manual"

    def test_trigger_type_count(self):
        """Correct number of trigger types"""
        assert len(WorkflowTriggerType) == 9


class TestStageType:
    """Tests for StageType enum"""

    def test_all_stage_types_exist(self):
        """All expected stage types exist"""
        expected = ["HUMAN", "AUTOMATION", "HYBRID", "AI", "APPROVAL",
                    "AGENT_ASSIST", "CODE_REVIEW", "TEST_ENRICHMENT", "DOC_UPDATE"]
        for name in expected:
            assert hasattr(StageType, name)

    def test_stage_type_values(self):
        """Stage type values are correct"""
        assert StageType.HUMAN.value == "human"
        assert StageType.AUTOMATION.value == "automation"
        assert StageType.AI.value == "ai"
        assert StageType.CODE_REVIEW.value == "code_review"

    def test_stage_type_count(self):
        """Correct number of stage types"""
        assert len(StageType) == 9


class TestWorkItemStatus:
    """Tests for WorkItemStatus enum"""

    def test_all_status_values_exist(self):
        """All expected status values exist"""
        expected = ["PENDING", "CLAIMED", "IN_PROGRESS", "WAITING",
                    "COMPLETED", "CANCELLED", "FAILED"]
        for name in expected:
            assert hasattr(WorkItemStatus, name)

    def test_status_values(self):
        """Status values are correct"""
        assert WorkItemStatus.PENDING.value == "pending"
        assert WorkItemStatus.IN_PROGRESS.value == "in_progress"
        assert WorkItemStatus.COMPLETED.value == "completed"

    def test_status_count(self):
        """Correct number of statuses"""
        assert len(WorkItemStatus) == 7


class TestWorkItemPriority:
    """Tests for WorkItemPriority enum"""

    def test_all_priorities_exist(self):
        """All expected priorities exist"""
        expected = ["LOW", "NORMAL", "HIGH", "URGENT"]
        for name in expected:
            assert hasattr(WorkItemPriority, name)

    def test_priority_values(self):
        """Priority values are correct"""
        assert WorkItemPriority.LOW.value == "low"
        assert WorkItemPriority.URGENT.value == "urgent"

    def test_priority_count(self):
        """Correct number of priorities"""
        assert len(WorkItemPriority) == 4


class TestAssignmentType:
    """Tests for AssignmentType enum"""

    def test_all_assignment_types_exist(self):
        """All expected assignment types exist"""
        expected = ["ROLE", "SPECIFIC_USER", "QUEUE", "AUTOMATION", "ROUND_ROBIN"]
        for name in expected:
            assert hasattr(AssignmentType, name)

    def test_assignment_values(self):
        """Assignment type values are correct"""
        assert AssignmentType.ROLE.value == "role"
        assert AssignmentType.SPECIFIC_USER.value == "user"
        assert AssignmentType.ROUND_ROBIN.value == "round_robin"

    def test_assignment_type_count(self):
        """Correct number of assignment types"""
        assert len(AssignmentType) == 5


class TestConditionOperator:
    """Tests for ConditionOperator enum"""

    def test_all_operators_exist(self):
        """All expected operators exist"""
        expected = ["EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN",
                    "CONTAINS", "NOT_CONTAINS", "IS_TRUE", "IS_FALSE"]
        for name in expected:
            assert hasattr(ConditionOperator, name)

    def test_operator_values(self):
        """Operator values are correct"""
        assert ConditionOperator.EQUALS.value == "=="
        assert ConditionOperator.NOT_EQUALS.value == "!="
        assert ConditionOperator.GREATER_THAN.value == ">"
        assert ConditionOperator.LESS_THAN.value == "<"
        assert ConditionOperator.CONTAINS.value == "contains"
        assert ConditionOperator.IS_TRUE.value == "is_true"

    def test_operator_count(self):
        """Correct number of operators"""
        assert len(ConditionOperator) == 8


class TestFieldType:
    """Tests for FieldType enum"""

    def test_all_field_types_exist(self):
        """All expected field types exist"""
        expected = ["TEXT", "TEXTAREA", "NUMBER", "DATE", "TIME", "DATETIME",
                    "SELECT", "MULTISELECT", "CHECKBOX", "RADIO", "FILE_UPLOAD",
                    "EMAIL", "PHONE", "URL"]
        for name in expected:
            assert hasattr(FieldType, name)

    def test_field_type_values(self):
        """Field type values are correct"""
        assert FieldType.TEXT.value == "text"
        assert FieldType.FILE_UPLOAD.value == "file_upload"
        assert FieldType.DATETIME.value == "datetime"

    def test_field_type_count(self):
        """Correct number of field types"""
        assert len(FieldType) == 14


class TestWorkflowType:
    """Tests for WorkflowType enum"""

    def test_all_workflow_types_exist(self):
        """All expected workflow types exist"""
        assert hasattr(WorkflowType, "LOCAL_AUTOMATION")
        assert hasattr(WorkflowType, "TEAM_WORKFLOW")

    def test_workflow_type_values(self):
        """Workflow type values are correct"""
        assert WorkflowType.LOCAL_AUTOMATION.value == "local"
        assert WorkflowType.TEAM_WORKFLOW.value == "team"

    def test_workflow_type_count(self):
        """Correct number of workflow types"""
        assert len(WorkflowType) == 2


class TestNotificationEvent:
    """Tests for NotificationEvent enum"""

    def test_all_events_exist(self):
        """All expected notification events exist"""
        expected = ["WORK_ITEM_ASSIGNED", "WORK_ITEM_CLAIMED", "WORK_ITEM_COMPLETED",
                    "WORK_ITEM_OVERDUE", "STAGE_ENTERED", "APPROVAL_REQUESTED", "COMMENT_ADDED"]
        for name in expected:
            assert hasattr(NotificationEvent, name)

    def test_event_values(self):
        """Event values are correct"""
        assert NotificationEvent.WORK_ITEM_ASSIGNED.value == "work_item_assigned"
        assert NotificationEvent.APPROVAL_REQUESTED.value == "approval_requested"

    def test_event_count(self):
        """Correct number of events"""
        assert len(NotificationEvent) == 7


# ============================================
# FORM MODEL TESTS
# ============================================

class TestFormFieldOption:
    """Tests for FormFieldOption model"""

    def test_create_option(self):
        """Create form field option"""
        opt = FormFieldOption(value="opt1", label="Option 1")
        assert opt.value == "opt1"
        assert opt.label == "Option 1"

    def test_option_serialization(self):
        """Option serializes to dict"""
        opt = FormFieldOption(value="v", label="L")
        data = opt.model_dump()
        assert data == {"value": "v", "label": "L"}


class TestFormField:
    """Tests for FormField model"""

    def test_create_minimal_field(self):
        """Create form field with minimal params"""
        field = FormField(name="email", label="Email", type=FieldType.EMAIL)
        assert field.name == "email"
        assert field.label == "Email"
        assert field.type == FieldType.EMAIL
        assert field.required is False  # Default
        assert field.id  # Auto-generated

    def test_create_field_with_validation(self):
        """Create form field with validation"""
        field = FormField(
            name="age",
            label="Age",
            type=FieldType.NUMBER,
            required=True,
            min_value=0,
            max_value=150,
            help_text="Enter your age"
        )
        assert field.required is True
        assert field.min_value == 0
        assert field.max_value == 150
        assert field.help_text == "Enter your age"

    def test_field_with_options(self):
        """Create select field with options"""
        options = [
            FormFieldOption(value="us", label="United States"),
            FormFieldOption(value="uk", label="United Kingdom"),
        ]
        field = FormField(
            name="country",
            label="Country",
            type=FieldType.SELECT,
            options=options
        )
        assert len(field.options) == 2
        assert field.options[0].value == "us"

    def test_field_with_conditional_display(self):
        """Create field with conditional display"""
        field = FormField(
            name="other_reason",
            label="Other Reason",
            type=FieldType.TEXT,
            show_if={"reason": "other"}
        )
        assert field.show_if == {"reason": "other"}

    def test_field_id_auto_generated(self):
        """Field ID is auto-generated UUID"""
        field = FormField(name="test", label="Test", type=FieldType.TEXT)
        # Should be valid UUID
        uuid.UUID(field.id)

    def test_field_with_custom_id(self):
        """Field can have custom ID"""
        field = FormField(id="custom-id", name="test", label="Test", type=FieldType.TEXT)
        assert field.id == "custom-id"


class TestFormDefinition:
    """Tests for FormDefinition model"""

    def test_create_form(self):
        """Create form definition"""
        fields = [
            FormField(name="name", label="Name", type=FieldType.TEXT, required=True),
            FormField(name="email", label="Email", type=FieldType.EMAIL, required=True),
        ]
        form = FormDefinition(name="Contact Form", fields=fields)
        assert form.name == "Contact Form"
        assert len(form.fields) == 2
        assert form.submit_button_text == "Submit"  # Default

    def test_form_with_description(self):
        """Create form with description"""
        form = FormDefinition(
            name="Survey",
            description="Please fill out this survey",
            fields=[],
            submit_button_text="Send Survey"
        )
        assert form.description == "Please fill out this survey"
        assert form.submit_button_text == "Send Survey"

    def test_form_id_auto_generated(self):
        """Form ID is auto-generated"""
        form = FormDefinition(name="Test", fields=[])
        uuid.UUID(form.id)


# ============================================
# ROUTING MODEL TESTS
# ============================================

class TestRoutingCondition:
    """Tests for RoutingCondition model"""

    def test_create_condition(self):
        """Create routing condition"""
        cond = RoutingCondition(
            field="priority",
            operator=ConditionOperator.EQUALS,
            value="high"
        )
        assert cond.field == "priority"
        assert cond.operator == ConditionOperator.EQUALS
        assert cond.value == "high"

    def test_condition_with_numeric_value(self):
        """Condition with numeric comparison"""
        cond = RoutingCondition(
            field="amount",
            operator=ConditionOperator.GREATER_THAN,
            value=1000
        )
        assert cond.value == 1000


class TestConditionalRoute:
    """Tests for ConditionalRoute model"""

    def test_create_route(self):
        """Create conditional route"""
        route = ConditionalRoute(
            next_stage_id="stage-2",
            conditions=[
                RoutingCondition(field="approved", operator=ConditionOperator.IS_TRUE, value=None)
            ]
        )
        assert route.next_stage_id == "stage-2"
        assert len(route.conditions) == 1
        assert route.notify is True  # Default

    def test_default_route(self):
        """Create default route (no conditions)"""
        route = ConditionalRoute(
            next_stage_id="default-stage",
            conditions=None,
            description="Default path"
        )
        assert route.conditions is None
        assert route.description == "Default path"


# ============================================
# AUTOMATION CONFIG TESTS
# ============================================

class TestAutomationConfig:
    """Tests for AutomationConfig model"""

    def test_n8n_automation(self):
        """Create n8n automation config"""
        config = AutomationConfig(
            type="n8n",
            n8n_workflow_id="wf-123",
            n8n_webhook_url="http://n8n.local/webhook/abc"
        )
        assert config.type == "n8n"
        assert config.n8n_workflow_id == "wf-123"
        assert config.timeout_seconds == 300  # Default

    def test_local_ai_automation(self):
        """Create local AI automation config"""
        config = AutomationConfig(
            type="local_ai",
            ai_model="llama3",
            ai_prompt_template="Analyze: {input}",
            timeout_seconds=600
        )
        assert config.type == "local_ai"
        assert config.ai_model == "llama3"
        assert config.timeout_seconds == 600

    def test_custom_automation(self):
        """Create custom script automation config"""
        config = AutomationConfig(
            type="custom",
            custom_script_path="/scripts/process.py",
            parameters={"key": "value"}
        )
        assert config.type == "custom"
        assert config.custom_script_path == "/scripts/process.py"
        assert config.parameters == {"key": "value"}


# ============================================
# STAGE MODEL TESTS
# ============================================

class TestStage:
    """Tests for Stage model"""

    def test_create_human_stage(self):
        """Create human work stage"""
        stage = Stage(
            name="Review",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.ROLE,
            role_name="reviewer"
        )
        assert stage.name == "Review"
        assert stage.stage_type == StageType.HUMAN
        assert stage.assignment_type == AssignmentType.ROLE
        assert stage.role_name == "reviewer"
        assert stage.id  # Auto-generated

    def test_stage_with_form(self):
        """Create stage with data collection form"""
        form = FormDefinition(name="Review Form", fields=[])
        stage = Stage(
            name="Data Entry",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            form=form
        )
        assert stage.form is not None
        assert stage.form.name == "Review Form"

    def test_stage_with_automation(self):
        """Create automation stage"""
        automation = AutomationConfig(type="local_ai", ai_model="qwen")
        stage = Stage(
            name="AI Processing",
            stage_type=StageType.AI,
            assignment_type=AssignmentType.AUTOMATION,
            automation=automation,
            auto_advance=True
        )
        assert stage.stage_type == StageType.AI
        assert stage.automation.ai_model == "qwen"
        assert stage.auto_advance is True

    def test_stage_with_sla(self):
        """Create stage with SLA"""
        stage = Stage(
            name="Urgent Review",
            stage_type=StageType.APPROVAL,
            assignment_type=AssignmentType.SPECIFIC_USER,
            assigned_user_id="user-123",
            sla_minutes=60,
            notify_on_overdue=True
        )
        assert stage.sla_minutes == 60
        assert stage.notify_on_overdue is True

    def test_stage_with_ai_assistance(self):
        """Create stage with AI assistance"""
        stage = Stage(
            name="Code Review",
            stage_type=StageType.CODE_REVIEW,
            assignment_type=AssignmentType.ROLE,
            role_name="developer",
            ai_suggestions_enabled=True,
            ai_suggestion_prompt="Review this code for security issues",
            agent_prompt="Focus on OWASP vulnerabilities",
            agent_target_path="src/auth/"
        )
        assert stage.ai_suggestions_enabled is True
        assert stage.agent_target_path == "src/auth/"

    def test_stage_with_routing(self):
        """Create stage with conditional routing"""
        routes = [
            ConditionalRoute(
                next_stage_id="approved-stage",
                conditions=[
                    RoutingCondition(field="approved", operator=ConditionOperator.IS_TRUE, value=None)
                ]
            ),
            ConditionalRoute(
                next_stage_id="rejected-stage",
                conditions=None  # Default route
            )
        ]
        stage = Stage(
            name="Approval",
            stage_type=StageType.APPROVAL,
            assignment_type=AssignmentType.ROLE,
            next_stages=routes
        )
        assert len(stage.next_stages) == 2

    def test_stage_defaults(self):
        """Stage has correct defaults"""
        stage = Stage(
            name="Test",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE
        )
        assert stage.requires_approval is False
        assert stage.auto_advance is False
        assert stage.notify_on_arrival is True
        assert stage.notify_on_overdue is True
        assert stage.ai_suggestions_enabled is False
        assert stage.order == 0


# ============================================
# WORKFLOW TRIGGER TESTS
# ============================================

class TestWorkflowTrigger:
    """Tests for WorkflowTrigger model"""

    def test_manual_trigger(self):
        """Create manual trigger"""
        trigger = WorkflowTrigger(trigger_type=WorkflowTriggerType.MANUAL)
        assert trigger.trigger_type == WorkflowTriggerType.MANUAL
        assert trigger.enabled is True  # Default

    def test_schedule_trigger(self):
        """Create scheduled trigger"""
        trigger = WorkflowTrigger(
            trigger_type=WorkflowTriggerType.SCHEDULE,
            cron_expression="0 9 * * 1-5"  # 9am weekdays
        )
        assert trigger.trigger_type == WorkflowTriggerType.SCHEDULE
        assert trigger.cron_expression == "0 9 * * 1-5"

    def test_webhook_trigger(self):
        """Create webhook trigger"""
        trigger = WorkflowTrigger(
            trigger_type=WorkflowTriggerType.WEBHOOK,
            webhook_url="/api/webhook/wf-123"
        )
        assert trigger.webhook_url == "/api/webhook/wf-123"

    def test_email_trigger(self):
        """Create email trigger"""
        trigger = WorkflowTrigger(
            trigger_type=WorkflowTriggerType.EMAIL,
            email_address="intake@example.com",
            email_filter={"subject_contains": "URGENT"}
        )
        assert trigger.email_address == "intake@example.com"
        assert trigger.email_filter == {"subject_contains": "URGENT"}

    def test_agent_event_trigger(self):
        """Create agent event trigger"""
        trigger = WorkflowTrigger(
            trigger_type=WorkflowTriggerType.ON_AGENT_EVENT,
            agent_event_type="agent.apply.success"
        )
        assert trigger.agent_event_type == "agent.apply.success"

    def test_file_pattern_trigger(self):
        """Create file pattern trigger"""
        trigger = WorkflowTrigger(
            trigger_type=WorkflowTriggerType.ON_FILE_PATTERN,
            file_pattern="*.py",
            pattern_repo_root="/projects/myapp"
        )
        assert trigger.file_pattern == "*.py"
        assert trigger.pattern_repo_root == "/projects/myapp"


# ============================================
# WORKFLOW MODEL TESTS
# ============================================

class TestWorkflow:
    """Tests for Workflow model"""

    def test_create_minimal_workflow(self):
        """Create workflow with minimal params"""
        stages = [Stage(name="Start", stage_type=StageType.HUMAN, assignment_type=AssignmentType.QUEUE)]
        triggers = [WorkflowTrigger(trigger_type=WorkflowTriggerType.MANUAL)]

        wf = Workflow(
            name="Test Workflow",
            stages=stages,
            triggers=triggers,
            created_by="user-1"
        )
        assert wf.name == "Test Workflow"
        assert len(wf.stages) == 1
        assert len(wf.triggers) == 1
        assert wf.created_by == "user-1"
        assert wf.id  # Auto-generated

    def test_workflow_defaults(self):
        """Workflow has correct defaults"""
        wf = Workflow(
            name="Test",
            stages=[],
            triggers=[],
            created_by="user"
        )
        assert wf.enabled is True
        assert wf.allow_manual_creation is True
        assert wf.require_approval_to_start is False
        assert wf.is_template is False
        assert wf.workflow_type == WorkflowType.TEAM_WORKFLOW
        assert wf.visibility == "personal"
        assert wf.version == 1
        assert wf.tags == []

    def test_workflow_with_team_scope(self):
        """Create workflow with team scope"""
        wf = Workflow(
            name="Team Workflow",
            stages=[],
            triggers=[],
            created_by="user",
            owner_team_id="team-123",
            visibility="team"
        )
        assert wf.owner_team_id == "team-123"
        assert wf.visibility == "team"

    def test_workflow_timestamps(self):
        """Workflow has timestamps"""
        wf = Workflow(name="Test", stages=[], triggers=[], created_by="user")
        assert wf.created_at is not None
        assert wf.updated_at is not None
        assert isinstance(wf.created_at, datetime)

    def test_workflow_with_metadata(self):
        """Create workflow with full metadata"""
        wf = Workflow(
            name="Healthcare Intake",
            description="Patient intake workflow",
            icon="🏥",
            category="Healthcare",
            stages=[],
            triggers=[],
            created_by="admin",
            tags=["healthcare", "patient"]
        )
        assert wf.description == "Patient intake workflow"
        assert wf.icon == "🏥"
        assert wf.category == "Healthcare"
        assert "healthcare" in wf.tags


# ============================================
# WORK ITEM RELATED MODEL TESTS
# ============================================

class TestStageTransition:
    """Tests for StageTransition model"""

    def test_create_transition(self):
        """Create stage transition"""
        trans = StageTransition(
            from_stage_id="stage-1",
            to_stage_id="stage-2",
            transitioned_by="user-1",
            notes="Approved",
            duration_seconds=3600
        )
        assert trans.from_stage_id == "stage-1"
        assert trans.to_stage_id == "stage-2"
        assert trans.duration_seconds == 3600
        assert trans.transitioned_at is not None

    def test_initial_transition(self):
        """First stage transition has no from_stage"""
        trans = StageTransition(
            from_stage_id=None,
            to_stage_id="stage-1"
        )
        assert trans.from_stage_id is None

    def test_terminal_transition(self):
        """Terminal transition has no to_stage"""
        trans = StageTransition(
            from_stage_id="final-stage",
            to_stage_id=None,
            notes="Workflow completed"
        )
        assert trans.to_stage_id is None


class TestWorkItemAttachment:
    """Tests for WorkItemAttachment model"""

    def test_create_attachment(self):
        """Create attachment"""
        att = WorkItemAttachment(
            filename="document.pdf",
            file_path="/uploads/doc.pdf",
            file_size=102400,
            mime_type="application/pdf",
            uploaded_by="user-1"
        )
        assert att.filename == "document.pdf"
        assert att.file_size == 102400
        assert att.mime_type == "application/pdf"
        assert att.id  # Auto-generated
        assert att.uploaded_at is not None


class TestWorkItem:
    """Tests for WorkItem model"""

    def test_create_work_item(self):
        """Create work item"""
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test Workflow",
            current_stage_id="stage-1",
            current_stage_name="Triage",
            status=WorkItemStatus.PENDING,
            created_by="user-1"
        )
        assert item.workflow_id == "wf-1"
        assert item.current_stage_id == "stage-1"
        assert item.status == WorkItemStatus.PENDING
        assert item.priority == WorkItemPriority.NORMAL  # Default
        assert item.id  # Auto-generated

    def test_work_item_with_data(self):
        """Create work item with data payload"""
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Intake",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            data={"patient_name": "John Doe", "age": 45}
        )
        assert item.data["patient_name"] == "John Doe"
        assert item.data["age"] == 45

    def test_work_item_with_history(self):
        """Create work item with history"""
        history = [
            StageTransition(from_stage_id=None, to_stage_id="stage-1"),
            StageTransition(from_stage_id="stage-1", to_stage_id="stage-2", duration_seconds=1800)
        ]
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="stage-2",
            current_stage_name="Review",
            status=WorkItemStatus.IN_PROGRESS,
            created_by="user",
            history=history
        )
        assert len(item.history) == 2
        assert item.history[1].duration_seconds == 1800

    def test_work_item_with_attachments(self):
        """Create work item with attachments"""
        attachments = [
            WorkItemAttachment(
                filename="file.pdf",
                file_path="/path",
                file_size=1000,
                mime_type="application/pdf",
                uploaded_by="user"
            )
        ]
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            attachments=attachments
        )
        assert len(item.attachments) == 1

    def test_work_item_sla_tracking(self):
        """Work item SLA tracking"""
        due = datetime.now(UTC) + timedelta(hours=4)
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            sla_due_at=due,
            is_overdue=False
        )
        assert item.sla_due_at == due
        assert item.is_overdue is False

    def test_work_item_claimed(self):
        """Work item can be claimed"""
        now = datetime.now(UTC)
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.CLAIMED,
            created_by="creator",
            assigned_to="worker",
            claimed_at=now
        )
        assert item.assigned_to == "worker"
        assert item.claimed_at == now
        assert item.status == WorkItemStatus.CLAIMED


# ============================================
# QUEUE MODEL TESTS
# ============================================

class TestQueueFilter:
    """Tests for QueueFilter model"""

    def test_create_filter(self):
        """Create queue filter"""
        f = QueueFilter(
            field="priority",
            operator=ConditionOperator.EQUALS,
            value="urgent"
        )
        assert f.field == "priority"
        assert f.operator == ConditionOperator.EQUALS
        assert f.value == "urgent"


class TestQueue:
    """Tests for Queue model"""

    def test_create_queue(self):
        """Create queue"""
        q = Queue(name="Triage Queue", stage_id="stage-1")
        assert q.name == "Triage Queue"
        assert q.stage_id == "stage-1"
        assert q.sort_by == "priority"  # Default
        assert q.sort_order == "desc"  # Default

    def test_queue_with_filters(self):
        """Create queue with filters"""
        filters = [
            QueueFilter(field="priority", operator=ConditionOperator.EQUALS, value="urgent")
        ]
        q = Queue(
            name="Urgent Queue",
            stage_id="stage-1",
            filters=filters,
            sort_by="sla",
            sort_order="asc"
        )
        assert len(q.filters) == 1
        assert q.sort_by == "sla"

    def test_queue_auto_assignment(self):
        """Queue with auto-assignment"""
        q = Queue(
            name="Auto Queue",
            stage_id="stage-1",
            role_name="worker",
            enable_auto_assignment=True,
            max_items_per_user=5
        )
        assert q.enable_auto_assignment is True
        assert q.max_items_per_user == 5


# ============================================
# NOTIFICATION MODEL TESTS
# ============================================

class TestNotification:
    """Tests for Notification model"""

    def test_create_notification(self):
        """Create notification"""
        notif = Notification(
            user_id="user-1",
            event=NotificationEvent.WORK_ITEM_ASSIGNED,
            work_item_id="item-1",
            work_item_reference="WI-001",
            title="New Assignment",
            message="You have been assigned a work item"
        )
        assert notif.user_id == "user-1"
        assert notif.event == NotificationEvent.WORK_ITEM_ASSIGNED
        assert notif.read is False  # Default
        assert notif.id  # Auto-generated

    def test_notification_with_action(self):
        """Notification with action URL"""
        notif = Notification(
            user_id="user-1",
            event=NotificationEvent.APPROVAL_REQUESTED,
            work_item_id="item-1",
            work_item_reference="WI-002",
            title="Approval Needed",
            message="Please review",
            action_url="/workflow/item-1/approve"
        )
        assert notif.action_url == "/workflow/item-1/approve"


# ============================================
# ROLE MODEL TESTS
# ============================================

class TestWorkflowRole:
    """Tests for WorkflowRole model"""

    def test_create_role(self):
        """Create workflow role"""
        role = WorkflowRole(
            name="Reviewer",
            description="Reviews submitted items"
        )
        assert role.name == "Reviewer"
        assert role.can_create_work_items is True  # Default
        assert role.can_claim_from_queue is True  # Default
        assert role.can_reassign is False  # Default
        assert role.id  # Auto-generated

    def test_role_with_permissions(self):
        """Role with custom permissions"""
        role = WorkflowRole(
            name="Admin",
            can_create_work_items=True,
            can_claim_from_queue=True,
            can_reassign=True,
            can_cancel=True,
            can_view_all=True
        )
        assert role.can_reassign is True
        assert role.can_cancel is True
        assert role.can_view_all is True

    def test_role_with_stage_access(self):
        """Role with specific stage access"""
        role = WorkflowRole(
            name="Limited",
            accessible_stage_ids=["stage-1", "stage-2"]
        )
        assert len(role.accessible_stage_ids) == 2


class TestUserRoleAssignment:
    """Tests for UserRoleAssignment model"""

    def test_create_assignment(self):
        """Create role assignment"""
        assign = UserRoleAssignment(
            user_id="user-1",
            role_id="role-1",
            role_name="Reviewer",
            assigned_by="admin"
        )
        assert assign.user_id == "user-1"
        assert assign.role_id == "role-1"
        assert assign.workflow_id is None  # Global role
        assert assign.id  # Auto-generated

    def test_workflow_specific_assignment(self):
        """Role assignment for specific workflow"""
        assign = UserRoleAssignment(
            user_id="user-1",
            role_id="role-1",
            role_name="Case Manager",
            workflow_id="wf-legal",
            assigned_by="admin"
        )
        assert assign.workflow_id == "wf-legal"


# ============================================
# METRICS MODEL TESTS
# ============================================

class TestWorkflowMetrics:
    """Tests for WorkflowMetrics model"""

    def test_create_metrics(self):
        """Create workflow metrics"""
        now = datetime.now(UTC)
        metrics = WorkflowMetrics(
            workflow_id="wf-1",
            workflow_name="Test",
            period_start=now - timedelta(days=30),
            period_end=now
        )
        assert metrics.workflow_id == "wf-1"
        assert metrics.total_items_created == 0  # Default
        assert metrics.stage_metrics == {}  # Default

    def test_metrics_with_data(self):
        """Metrics with populated data"""
        now = datetime.now(UTC)
        metrics = WorkflowMetrics(
            workflow_id="wf-1",
            workflow_name="Healthcare Intake",
            total_items_created=100,
            total_items_completed=85,
            total_items_cancelled=5,
            total_items_active=10,
            avg_completion_time_minutes=240.5,
            sla_compliance_rate=0.92,
            slowest_stage_id="stage-review",
            slowest_stage_avg_minutes=120.0,
            period_start=now - timedelta(days=30),
            period_end=now,
            stage_metrics={
                "stage-1": {"avg_time": 30, "items": 100},
                "stage-2": {"avg_time": 120, "items": 95}
            }
        )
        assert metrics.total_items_completed == 85
        assert metrics.sla_compliance_rate == 0.92
        assert len(metrics.stage_metrics) == 2


class TestStageMetrics:
    """Tests for StageMetrics model"""

    def test_create_stage_metrics(self):
        """Create stage metrics"""
        metrics = StageMetrics(
            stage_id="stage-1",
            stage_name="Triage",
            items_entered=100,
            items_completed=95,
            items_currently_in_stage=5,
            avg_time_in_stage_minutes=45.5,
            sla_violations=3,
            sla_compliance_rate=0.97
        )
        assert metrics.stage_id == "stage-1"
        assert metrics.items_entered == 100
        assert metrics.sla_compliance_rate == 0.97


# ============================================
# P2P SYNC MODEL TESTS
# ============================================

class TestWorkflowSyncMessage:
    """Tests for WorkflowSyncMessage model"""

    def test_create_sync_message(self):
        """Create sync message"""
        msg = WorkflowSyncMessage(
            message_type="work_item_created",
            sender_peer_id="peer-1",
            sender_user_id="user-1",
            work_item_id="item-1",
            payload={"status": "pending"}
        )
        assert msg.message_type == "work_item_created"
        assert msg.sender_peer_id == "peer-1"
        assert msg.message_id  # Auto-generated

    def test_sync_message_with_vector_clock(self):
        """Sync message with CRDT vector clock"""
        msg = WorkflowSyncMessage(
            message_type="stage_transition",
            sender_peer_id="peer-1",
            sender_user_id="user-1",
            work_item_id="item-1",
            payload={"from_stage": "s1", "to_stage": "s2"},
            vector_clock={"peer-1": 5, "peer-2": 3}
        )
        assert msg.vector_clock == {"peer-1": 5, "peer-2": 3}

    def test_sync_message_with_team(self):
        """Sync message with team isolation"""
        msg = WorkflowSyncMessage(
            message_type="workflow_updated",
            sender_peer_id="peer-1",
            sender_user_id="user-1",
            workflow_id="wf-1",
            payload={"name": "Updated Workflow"},
            team_id="team-1",
            signature="hmac-signature"
        )
        assert msg.team_id == "team-1"
        assert msg.signature == "hmac-signature"

    def test_all_message_types_valid(self):
        """All expected message types are accepted"""
        valid_types = [
            "work_item_created",
            "work_item_claimed",
            "work_item_completed",
            "stage_transition",
            "queue_update",
            "workflow_updated"
        ]
        for msg_type in valid_types:
            msg = WorkflowSyncMessage(
                message_type=msg_type,
                sender_peer_id="peer",
                sender_user_id="user",
                payload={}
            )
            assert msg.message_type == msg_type


class TestWorkItemConflict:
    """Tests for WorkItemConflict model"""

    def test_create_conflict(self):
        """Create work item conflict"""
        now = datetime.now(UTC)
        conflict = WorkItemConflict(
            work_item_id="item-1",
            conflicting_field="status",
            local_value="completed",
            remote_value="in_progress",
            local_timestamp=now,
            remote_timestamp=now - timedelta(minutes=5)
        )
        assert conflict.work_item_id == "item-1"
        assert conflict.conflicting_field == "status"
        assert conflict.resolution is None

    def test_conflict_with_resolution(self):
        """Conflict with resolution"""
        now = datetime.now(UTC)
        conflict = WorkItemConflict(
            work_item_id="item-1",
            conflicting_field="assigned_to",
            local_value="user-1",
            remote_value="user-2",
            local_timestamp=now,
            remote_timestamp=now - timedelta(seconds=30),
            resolution="local_wins"
        )
        assert conflict.resolution == "local_wins"


# ============================================
# API REQUEST MODEL TESTS
# ============================================

class TestCreateWorkItemRequest:
    """Tests for CreateWorkItemRequest model"""

    def test_create_request(self):
        """Create work item request"""
        req = CreateWorkItemRequest(
            workflow_id="wf-1",
            data={"patient_name": "John"}
        )
        assert req.workflow_id == "wf-1"
        assert req.data == {"patient_name": "John"}
        assert req.priority is None  # Optional

    def test_create_request_with_priority(self):
        """Request with priority and tags"""
        req = CreateWorkItemRequest(
            workflow_id="wf-1",
            data={"urgent": True},
            priority=WorkItemPriority.URGENT,
            tags=["critical", "priority"]
        )
        assert req.priority == WorkItemPriority.URGENT
        assert "critical" in req.tags


class TestClaimWorkItemRequest:
    """Tests for ClaimWorkItemRequest model"""

    def test_claim_request(self):
        """Create claim request"""
        req = ClaimWorkItemRequest(
            work_item_id="item-1",
            user_id="user-1"
        )
        assert req.work_item_id == "item-1"
        assert req.user_id == "user-1"


class TestCompleteStageRequest:
    """Tests for CompleteStageRequest model"""

    def test_complete_request(self):
        """Create complete stage request"""
        req = CompleteStageRequest(
            work_item_id="item-1",
            stage_id="stage-1",
            data={"approved": True}
        )
        assert req.work_item_id == "item-1"
        assert req.stage_id == "stage-1"
        assert req.data == {"approved": True}
        assert req.next_stage_id is None  # Optional

    def test_complete_request_with_routing(self):
        """Complete request with explicit next stage"""
        req = CompleteStageRequest(
            work_item_id="item-1",
            stage_id="stage-1",
            data={"decision": "approve"},
            next_stage_id="approval-stage",
            notes="Approved by manager"
        )
        assert req.next_stage_id == "approval-stage"
        assert req.notes == "Approved by manager"


class TestCreateWorkflowRequest:
    """Tests for CreateWorkflowRequest model"""

    def test_create_workflow_request(self):
        """Create workflow request"""
        req = CreateWorkflowRequest(
            name="New Workflow",
            stages=[{"name": "Start", "stage_type": "human", "assignment_type": "queue"}],
            triggers=[{"trigger_type": "manual"}]
        )
        assert req.name == "New Workflow"
        assert len(req.stages) == 1
        assert len(req.triggers) == 1

    def test_create_workflow_request_with_metadata(self):
        """Create workflow request with full metadata"""
        req = CreateWorkflowRequest(
            name="Healthcare Workflow",
            description="Patient intake process",
            icon="🏥",
            category="Healthcare",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            stages=[],
            triggers=[]
        )
        assert req.description == "Patient intake process"
        assert req.workflow_type == WorkflowType.TEAM_WORKFLOW


# ============================================
# SERIALIZATION TESTS
# ============================================

class TestModelSerialization:
    """Tests for model serialization"""

    def test_workflow_to_json(self):
        """Workflow can be serialized to JSON"""
        wf = Workflow(
            name="Test",
            stages=[
                Stage(
                    name="Stage 1",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE
                )
            ],
            triggers=[WorkflowTrigger(trigger_type=WorkflowTriggerType.MANUAL)],
            created_by="user"
        )
        data = wf.model_dump(mode='json')
        # Should be JSON-serializable
        json_str = json.dumps(data)
        assert "Test" in json_str
        assert "Stage 1" in json_str

    def test_work_item_to_json(self):
        """Work item can be serialized to JSON"""
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            data={"key": "value"}
        )
        data = item.model_dump(mode='json')
        json_str = json.dumps(data)
        assert "pending" in json_str
        assert "key" in json_str

    def test_nested_model_serialization(self):
        """Nested models serialize correctly"""
        form = FormDefinition(
            name="Test Form",
            fields=[
                FormField(
                    name="email",
                    label="Email",
                    type=FieldType.EMAIL,
                    required=True
                )
            ]
        )
        stage = Stage(
            name="Data Collection",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            form=form
        )
        data = stage.model_dump(mode='json')
        assert data["form"]["name"] == "Test Form"
        assert data["form"]["fields"][0]["type"] == "email"


# ============================================
# EDGE CASES
# ============================================

class TestEdgeCases:
    """Edge case tests"""

    def test_unicode_in_workflow_name(self):
        """Workflow handles unicode"""
        wf = Workflow(
            name="日本語ワークフロー 🇯🇵",
            stages=[],
            triggers=[],
            created_by="user"
        )
        assert "日本語" in wf.name
        assert "🇯🇵" in wf.name

    def test_empty_data_payload(self):
        """Work item with empty data"""
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            data={}
        )
        assert item.data == {}

    def test_large_data_payload(self):
        """Work item with large data payload"""
        large_data = {f"field_{i}": f"value_{i}" for i in range(100)}
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test",
            current_stage_id="s1",
            current_stage_name="Start",
            status=WorkItemStatus.PENDING,
            created_by="user",
            data=large_data
        )
        assert len(item.data) == 100

    def test_special_chars_in_strings(self):
        """Models handle special characters"""
        form_field = FormField(
            name="test_field",
            label="Test <Field> & \"Quotes\"",
            type=FieldType.TEXT
        )
        assert '&' in form_field.label
        assert '"' in form_field.label

    def test_uuid_uniqueness(self):
        """Auto-generated IDs are unique"""
        items = [
            WorkItem(
                workflow_id="wf-1",
                workflow_name="Test",
                current_stage_id="s1",
                current_stage_name="Start",
                status=WorkItemStatus.PENDING,
                created_by="user"
            )
            for _ in range(10)
        ]
        ids = [item.id for item in items]
        assert len(set(ids)) == 10  # All unique


# ============================================
# INTEGRATION TESTS
# ============================================

class TestIntegration:
    """Integration tests"""

    def test_complete_workflow_structure(self):
        """Test complete workflow with all components"""
        # Create form
        form = FormDefinition(
            name="Patient Intake",
            fields=[
                FormField(name="name", label="Patient Name", type=FieldType.TEXT, required=True),
                FormField(name="dob", label="Date of Birth", type=FieldType.DATE, required=True),
                FormField(
                    name="insurance",
                    label="Insurance Type",
                    type=FieldType.SELECT,
                    options=[
                        FormFieldOption(value="private", label="Private"),
                        FormFieldOption(value="medicare", label="Medicare"),
                    ]
                ),
            ]
        )

        # Create automation
        automation = AutomationConfig(
            type="local_ai",
            ai_model="llama3",
            ai_prompt_template="Verify patient info: {data}"
        )

        # Create stages
        stages = [
            Stage(
                id="intake",
                name="Patient Intake",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.QUEUE,
                form=form,
                next_stages=[
                    ConditionalRoute(next_stage_id="verify", conditions=None)
                ]
            ),
            Stage(
                id="verify",
                name="AI Verification",
                stage_type=StageType.AI,
                assignment_type=AssignmentType.AUTOMATION,
                automation=automation,
                auto_advance=True,
                next_stages=[
                    ConditionalRoute(
                        next_stage_id="nurse-review",
                        conditions=[
                            RoutingCondition(
                                field="ai_confidence",
                                operator=ConditionOperator.GREATER_THAN,
                                value=0.9
                            )
                        ]
                    ),
                    ConditionalRoute(next_stage_id="manual-review", conditions=None)
                ]
            ),
            Stage(
                id="nurse-review",
                name="Nurse Review",
                stage_type=StageType.APPROVAL,
                assignment_type=AssignmentType.ROLE,
                role_name="nurse",
                sla_minutes=60
            ),
            Stage(
                id="manual-review",
                name="Manual Review",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.ROLE,
                role_name="supervisor"
            )
        ]

        # Create triggers
        triggers = [
            WorkflowTrigger(trigger_type=WorkflowTriggerType.MANUAL),
            WorkflowTrigger(
                trigger_type=WorkflowTriggerType.FORM_SUBMISSION,
                form_id=form.id
            )
        ]

        # Create workflow
        workflow = Workflow(
            name="Healthcare Patient Intake",
            description="Process new patient intake forms",
            icon="🏥",
            category="Healthcare",
            stages=stages,
            triggers=triggers,
            created_by="admin",
            owner_team_id="healthcare-team",
            visibility="team",
            tags=["healthcare", "patient", "intake"]
        )

        # Verify structure
        assert len(workflow.stages) == 4
        assert len(workflow.triggers) == 2
        assert workflow.stages[0].form is not None
        assert workflow.stages[1].automation is not None
        assert len(workflow.stages[0].next_stages) == 1
        assert len(workflow.stages[1].next_stages) == 2

        # Test serialization
        data = workflow.model_dump(mode='json')
        json_str = json.dumps(data)
        assert "Healthcare Patient Intake" in json_str
        assert "nurse" in json_str

    def test_work_item_lifecycle(self):
        """Test work item through lifecycle"""
        # Create work item
        item = WorkItem(
            workflow_id="wf-1",
            workflow_name="Test Workflow",
            current_stage_id="stage-1",
            current_stage_name="Intake",
            status=WorkItemStatus.PENDING,
            created_by="creator",
            data={"patient_name": "John Doe"}
        )

        # Simulate claim
        item.status = WorkItemStatus.CLAIMED
        item.assigned_to = "worker-1"
        item.claimed_at = datetime.now(UTC)

        # Simulate work start
        item.status = WorkItemStatus.IN_PROGRESS

        # Simulate stage transition
        transition = StageTransition(
            from_stage_id="stage-1",
            to_stage_id="stage-2",
            transitioned_by="worker-1",
            duration_seconds=1800
        )
        item.history.append(transition)
        item.current_stage_id = "stage-2"
        item.current_stage_name = "Review"

        # Simulate completion
        item.status = WorkItemStatus.COMPLETED
        item.completed_at = datetime.now(UTC)
        final_transition = StageTransition(
            from_stage_id="stage-2",
            to_stage_id=None,
            transitioned_by="worker-1",
            notes="Approved"
        )
        item.history.append(final_transition)

        # Verify
        assert item.status == WorkItemStatus.COMPLETED
        assert item.completed_at is not None
        assert len(item.history) == 2
        assert item.history[-1].to_stage_id is None  # Terminal
