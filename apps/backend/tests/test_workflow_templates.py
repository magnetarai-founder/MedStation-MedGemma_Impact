"""
Tests for Phase D: Workflow Templates
Tests template creation, listing, retrieval, and instantiation
"""

import pytest
import tempfile
from pathlib import Path

from api.workflow_models import (
    Workflow,
    Stage,
    WorkflowTrigger,
    WorkflowTriggerType,
    StageType,
    AssignmentType,
    WorkflowType,
)
from api.workflow_storage import WorkflowStorage


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
def template_workflow(storage, test_user_id):
    """Create a template workflow"""
    workflow = Workflow(
        name="Code Review Template",
        description="Template for code review workflows",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        is_template=True,  # Mark as template
        stages=[
            Stage(
                id="stage1",
                name="Initial Review",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.ROLE,
                role_name="reviewer",
            ),
            Stage(
                id="stage2",
                name="Approval",
                stage_type=StageType.APPROVAL,
                assignment_type=AssignmentType.ROLE,
                role_name="approver",
            ),
        ],
        triggers=[
            WorkflowTrigger(
                trigger_type=WorkflowTriggerType.MANUAL,
                enabled=True,
            )
        ],
        created_by=test_user_id,
        tags=["review", "template"],
    )
    storage.save_workflow(workflow, user_id=test_user_id)
    return workflow


@pytest.fixture
def regular_workflow(storage, test_user_id):
    """Create a regular (non-template) workflow"""
    workflow = Workflow(
        name="Regular Workflow",
        description="Not a template",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        is_template=False,  # Not a template
        stages=[
            Stage(
                id="stage1",
                name="Work Stage",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.QUEUE,
            )
        ],
        triggers=[],
        created_by=test_user_id,
    )
    storage.save_workflow(workflow, user_id=test_user_id)
    return workflow


class TestTemplateWorkflows:
    """Tests for workflow template functionality"""

    def test_create_template_workflow(self, storage, test_user_id):
        """Test creating a workflow with is_template=True"""
        workflow = Workflow(
            name="New Template",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            is_template=True,
            stages=[
                Stage(
                    id="s1",
                    name="Stage 1",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )

        storage.save_workflow(workflow, user_id=test_user_id)

        # Retrieve and verify
        retrieved = storage.get_workflow(workflow.id, user_id=test_user_id)
        assert retrieved is not None
        assert retrieved.is_template is True
        assert retrieved.name == "New Template"

    def test_list_only_templates(
        self, storage, template_workflow, regular_workflow, test_user_id
    ):
        """Test filtering workflows to get only templates"""
        all_workflows = storage.list_workflows(user_id=test_user_id)
        templates = [w for w in all_workflows if w.is_template]

        # Should have exactly 1 template
        assert len(templates) == 1
        assert templates[0].id == template_workflow.id
        assert templates[0].name == "Code Review Template"

    def test_template_backward_compatibility(self, storage, test_user_id):
        """Test that old workflows without is_template default to False"""
        workflow = Workflow(
            name="Old Workflow",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            # is_template not explicitly set (should default to False)
            stages=[
                Stage(
                    id="s1",
                    name="Stage 1",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )

        storage.save_workflow(workflow, user_id=test_user_id)

        # Retrieve and verify
        retrieved = storage.get_workflow(workflow.id, user_id=test_user_id)
        assert retrieved is not None
        assert retrieved.is_template is False  # Should default to False

    def test_update_workflow_to_template(self, storage, regular_workflow, test_user_id):
        """Test converting a regular workflow into a template"""
        # Mark as template
        regular_workflow.is_template = True
        storage.save_workflow(regular_workflow, user_id=test_user_id)

        # Retrieve and verify
        retrieved = storage.get_workflow(regular_workflow.id, user_id=test_user_id)
        assert retrieved is not None
        assert retrieved.is_template is True

    def test_multiple_templates_per_category(self, storage, test_user_id):
        """Test having multiple templates in same category"""
        template1 = Workflow(
            name="Template 1",
            category="Development",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            is_template=True,
            stages=[
                Stage(
                    id="s1",
                    name="Stage",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )
        template2 = Workflow(
            name="Template 2",
            category="Development",
            workflow_type=WorkflowType.TEAM_WORKFLOW,
            is_template=True,
            stages=[
                Stage(
                    id="s1",
                    name="Stage",
                    stage_type=StageType.HUMAN,
                    assignment_type=AssignmentType.QUEUE,
                )
            ],
            triggers=[],
            created_by=test_user_id,
        )

        storage.save_workflow(template1, user_id=test_user_id)
        storage.save_workflow(template2, user_id=test_user_id)

        # List templates in category
        all_workflows = storage.list_workflows(
            user_id=test_user_id, category="Development"
        )
        templates = [w for w in all_workflows if w.is_template]

        assert len(templates) == 2


class TestTemplateInstantiation:
    """Tests for creating workflow instances from templates"""

    def test_instantiate_template_basic(
        self, storage, template_workflow, test_user_id
    ):
        """Test basic template instantiation"""
        # Create instance from template
        new_workflow = Workflow(
            name=f"{template_workflow.name} (Copy)",
            description=template_workflow.description,
            workflow_type=template_workflow.workflow_type,
            is_template=False,  # Instance is not a template
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
            tags=template_workflow.tags.copy(),
        )

        storage.save_workflow(new_workflow, user_id=test_user_id)

        # Verify instance
        instance = storage.get_workflow(new_workflow.id, user_id=test_user_id)
        assert instance is not None
        assert instance.is_template is False
        assert instance.name == "Code Review Template (Copy)"
        assert len(instance.stages) == 2
        assert len(instance.triggers) == 1

    def test_instantiate_with_custom_name(
        self, storage, template_workflow, test_user_id
    ):
        """Test template instantiation with custom name"""
        new_workflow = Workflow(
            name="My Custom Review Workflow",  # Custom name
            description=template_workflow.description,
            workflow_type=template_workflow.workflow_type,
            is_template=False,
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
        )

        storage.save_workflow(new_workflow, user_id=test_user_id)

        instance = storage.get_workflow(new_workflow.id, user_id=test_user_id)
        assert instance is not None
        assert instance.name == "My Custom Review Workflow"

    def test_instantiate_preserves_stage_count(
        self, storage, template_workflow, test_user_id
    ):
        """Test that stage count is preserved during instantiation"""
        new_workflow = Workflow(
            name="Instance",
            workflow_type=template_workflow.workflow_type,
            is_template=False,
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
        )

        storage.save_workflow(new_workflow, user_id=test_user_id)

        instance = storage.get_workflow(new_workflow.id, user_id=test_user_id)
        assert len(instance.stages) == len(template_workflow.stages)
        # Verify stage names match
        for i, stage in enumerate(instance.stages):
            assert stage.name == template_workflow.stages[i].name

    def test_template_remains_unchanged_after_instantiation(
        self, storage, template_workflow, test_user_id
    ):
        """Test that template is not modified when creating instances"""
        original_name = template_workflow.name
        original_stage_count = len(template_workflow.stages)

        # Create instance
        new_workflow = Workflow(
            name="Instance",
            workflow_type=template_workflow.workflow_type,
            is_template=False,
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
        )
        storage.save_workflow(new_workflow, user_id=test_user_id)

        # Verify template unchanged
        template = storage.get_workflow(template_workflow.id, user_id=test_user_id)
        assert template.name == original_name
        assert template.is_template is True
        assert len(template.stages) == original_stage_count

    def test_multiple_instances_from_same_template(
        self, storage, template_workflow, test_user_id
    ):
        """Test creating multiple workflow instances from same template"""
        instance1 = Workflow(
            name="Instance 1",
            workflow_type=template_workflow.workflow_type,
            is_template=False,
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
        )
        instance2 = Workflow(
            name="Instance 2",
            workflow_type=template_workflow.workflow_type,
            is_template=False,
            stages=template_workflow.stages.copy(),
            triggers=template_workflow.triggers.copy(),
            created_by=test_user_id,
        )

        storage.save_workflow(instance1, user_id=test_user_id)
        storage.save_workflow(instance2, user_id=test_user_id)

        # Verify both instances exist
        retrieved1 = storage.get_workflow(instance1.id, user_id=test_user_id)
        retrieved2 = storage.get_workflow(instance2.id, user_id=test_user_id)

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.id != retrieved2.id
        assert retrieved1.name != retrieved2.name
        assert retrieved1.is_template is False
        assert retrieved2.is_template is False
