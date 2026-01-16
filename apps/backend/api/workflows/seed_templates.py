"""
Workflow Template Seeding (AGENT-PHASE-2)

Idempotently seeds high-quality global workflow templates that showcase
the new opinionated stage types (CODE_REVIEW, TEST_ENRICHMENT, DOC_UPDATE).
"""

import logging
from typing import Optional
from datetime import datetime, UTC
import uuid

try:
    from api.workflows.models import (
        Workflow,
        Stage,
        WorkflowTrigger,
        StageType,
        AssignmentType,
        WorkflowType,
        WorkflowTriggerType,
    )
    from api.workflow_storage import WorkflowStorage
except ImportError:
    from api.workflows.models import (
        Workflow,
        Stage,
        WorkflowTrigger,
        StageType,
        AssignmentType,
        WorkflowType,
        WorkflowTriggerType,
    )
    from workflow_storage import WorkflowStorage

logger = logging.getLogger(__name__)

# System user ID for global templates
SYSTEM_USER_ID = "system"


def _template_exists(storage: WorkflowStorage, template_key: str) -> bool:
    """
    Check if a template with the given key already exists.

    We check by querying all global templates and looking for one with
    matching system_template_key in the workflow name or a data field.

    Args:
        storage: WorkflowStorage instance
        template_key: Unique template identifier (e.g., "code_review_standard")

    Returns:
        True if template exists, False otherwise
    """
    try:
        # Query all workflows visible to system user (includes global templates)
        workflows = storage.list_workflows(
            user_id=SYSTEM_USER_ID,
            enabled_only=False,
            team_id=None
        )

        # Check if any workflow has this template key in its name or matches by name pattern
        for workflow in workflows:
            if workflow.is_template and workflow.visibility == "global":
                # Check by name matching (our template keys map to names)
                if template_key in [
                    "code_review_standard",
                    "bug_fix_test",
                    "release_notes_docs"
                ]:
                    name_map = {
                        "code_review_standard": "Standard Code Review",
                        "bug_fix_test": "Bug Fix + Test",
                        "release_notes_docs": "Release Notes & Docs"
                    }
                    if workflow.name == name_map[template_key]:
                        return True

        return False
    except Exception as e:
        logger.warning(f"Error checking template existence for {template_key}: {e}")
        return False


def _create_code_review_template() -> Workflow:
    """
    Create "Standard Code Review" template.

    Flow:
    1. Intake (HUMAN) - Capture PR/diff context
    2. Agent Code Review (CODE_REVIEW) - AI code quality analysis
    3. Human Review (HUMAN) - Final decision and comments
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    stages = [
        Stage(
            id=str(uuid.uuid4()),
            name="Intake",
            description="Capture PR/diff context and owner information",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=0,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Agent Code Review",
            description="AI analyzes code for quality, security, and maintainability",
            stage_type=StageType.CODE_REVIEW,
            assignment_type=AssignmentType.AUTOMATION,
            agent_prompt=None,  # Uses default CODE_REVIEW prompt
            agent_auto_apply=False,  # Advisory only
            order=1,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Human Review",
            description="Final review and approval by human reviewer",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=2,
            next_stages=[],
        ),
    ]

    triggers = [
        WorkflowTrigger(
            id=str(uuid.uuid4()),
            trigger_type=WorkflowTriggerType.MANUAL,
            enabled=True,
        )
    ]

    return Workflow(
        id=workflow_id,
        name="Standard Code Review",
        description="Agent-assisted code review for pull requests and changes. Flow: Intake → Agent Code Review → Human Review",
        icon="🔍",
        category="Development",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=stages,
        triggers=triggers,
        enabled=True,
        allow_manual_creation=True,
        require_approval_to_start=False,
        is_template=True,
        created_by=SYSTEM_USER_ID,
        created_at=now,
        updated_at=now,
        version=1,
        tags=["code-review", "ai-assisted", "quality"],
        visibility="global",
        owner_team_id=None,
    )


def _create_bug_fix_test_template() -> Workflow:
    """
    Create "Bug Fix + Test" template.

    Flow:
    1. Bug Intake (HUMAN) - Describe bug, link logs/examples
    2. Agent Diagnosis (AGENT_ASSIST) - AI diagnosis and investigation
    3. Agent Test Suggestions (TEST_ENRICHMENT) - AI test generation
    4. Implement Fix (HUMAN) - Human implements fix and runs tests
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    stages = [
        Stage(
            id=str(uuid.uuid4()),
            name="Bug Intake",
            description="Document bug details, logs, and reproduction steps",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=0,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Agent Diagnosis",
            description="AI analyzes bug and suggests root cause",
            stage_type=StageType.AGENT_ASSIST,
            assignment_type=AssignmentType.AUTOMATION,
            agent_prompt="You are a debugging expert. Analyze the bug report, logs, and code to identify the root cause and suggest fixes. Focus on: error patterns, stack traces, recent changes, and potential side effects.",
            agent_auto_apply=False,
            order=1,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Agent Test Suggestions",
            description="AI suggests tests to reproduce bug and prevent regressions",
            stage_type=StageType.TEST_ENRICHMENT,
            assignment_type=AssignmentType.AUTOMATION,
            agent_prompt=None,  # Uses default TEST_ENRICHMENT prompt
            agent_auto_apply=False,
            order=2,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Implement Fix",
            description="Developer implements fix and runs tests",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=3,
            next_stages=[],
        ),
    ]

    triggers = [
        WorkflowTrigger(
            id=str(uuid.uuid4()),
            trigger_type=WorkflowTriggerType.MANUAL,
            enabled=True,
        )
    ]

    return Workflow(
        id=workflow_id,
        name="Bug Fix + Test",
        description="Agent-assisted bug triage with test suggestions. Flow: Bug Intake → Agent Diagnosis → Agent Test Suggestions → Implement Fix",
        icon="🐛",
        category="Development",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=stages,
        triggers=triggers,
        enabled=True,
        allow_manual_creation=True,
        require_approval_to_start=False,
        is_template=True,
        created_by=SYSTEM_USER_ID,
        created_at=now,
        updated_at=now,
        version=1,
        tags=["bug-fix", "testing", "ai-assisted"],
        visibility="global",
        owner_team_id=None,
    )


def _create_release_notes_docs_template() -> Workflow:
    """
    Create "Release Notes & Docs" template.

    Flow:
    1. Release Candidate (HUMAN) - Capture release scope
    2. Agent Docs Draft (DOC_UPDATE) - AI drafts docs/release notes
    3. Docs Review & Publish (HUMAN) - Final review and publish
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    stages = [
        Stage(
            id=str(uuid.uuid4()),
            name="Release Candidate",
            description="Document what's included in this release (commits, tickets, features)",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=0,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Agent Docs Draft",
            description="AI drafts documentation and release notes",
            stage_type=StageType.DOC_UPDATE,
            assignment_type=AssignmentType.AUTOMATION,
            agent_prompt=None,  # Uses default DOC_UPDATE prompt
            agent_auto_apply=False,
            order=1,
            next_stages=[],
        ),
        Stage(
            id=str(uuid.uuid4()),
            name="Docs Review & Publish",
            description="Review AI-generated docs and publish",
            stage_type=StageType.HUMAN,
            assignment_type=AssignmentType.QUEUE,
            order=2,
            next_stages=[],
        ),
    ]

    triggers = [
        WorkflowTrigger(
            id=str(uuid.uuid4()),
            trigger_type=WorkflowTriggerType.MANUAL,
            enabled=True,
        )
    ]

    return Workflow(
        id=workflow_id,
        name="Release Notes & Docs",
        description="Agent-assisted documentation and release notes generation. Flow: Release Candidate → Agent Docs Draft → Docs Review & Publish",
        icon="📝",
        category="Documentation",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=stages,
        triggers=triggers,
        enabled=True,
        allow_manual_creation=True,
        require_approval_to_start=False,
        is_template=True,
        created_by=SYSTEM_USER_ID,
        created_at=now,
        updated_at=now,
        version=1,
        tags=["documentation", "release-notes", "ai-assisted"],
        visibility="global",
        owner_team_id=None,
    )


def seed_global_workflow_templates(storage: WorkflowStorage) -> None:
    """
    Ensure core global workflow templates exist (idempotent).

    Seeds three high-quality templates:
    1. Standard Code Review (CODE_REVIEW stage)
    2. Bug Fix + Test (AGENT_ASSIST + TEST_ENRICHMENT stages)
    3. Release Notes & Docs (DOC_UPDATE stage)

    This function is idempotent - it only creates templates that don't exist.

    Args:
        storage: WorkflowStorage instance
    """
    logger.info("🌱 Seeding global workflow templates...")

    templates = [
        ("code_review_standard", _create_code_review_template),
        ("bug_fix_test", _create_bug_fix_test_template),
        ("release_notes_docs", _create_release_notes_docs_template),
    ]

    seeded_count = 0
    skipped_count = 0

    for template_key, factory_fn in templates:
        try:
            # Check if template already exists
            if _template_exists(storage, template_key):
                logger.info(f"  ✓ Template '{template_key}' already exists, skipping")
                skipped_count += 1
                continue

            # Create and save template
            workflow = factory_fn()
            storage.save_workflow(
                workflow=workflow,
                user_id=SYSTEM_USER_ID,
                team_id=None,  # Global templates have no team
            )

            logger.info(f"  ✨ Created template: {workflow.name} (ID: {workflow.id})")
            seeded_count += 1

        except Exception as e:
            logger.error(f"  ❌ Failed to seed template '{template_key}': {e}", exc_info=True)
            # Continue with other templates (fail-soft)

    logger.info(f"🌱 Template seeding complete: {seeded_count} created, {skipped_count} skipped")
