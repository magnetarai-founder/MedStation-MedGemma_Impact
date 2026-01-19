"""
Workflow Storage Converters

Row-to-model conversion helpers for workflow storage.
"""

import json
import sqlite3
from datetime import datetime

from api.workflow_models import (
    Workflow,
    WorkItem,
    Stage,
    WorkflowTrigger,
    StageTransition,
    WorkItemAttachment,
    WorkItemStatus,
    WorkItemPriority,
    WorkflowType,
)


def row_to_workflow(row: sqlite3.Row) -> Workflow:
    """Convert database row to Workflow object."""
    stages_data = json.loads(row['stages'])
    triggers_data = json.loads(row['triggers'])

    # Handle workflow_type with backward compatibility
    try:
        workflow_type_value = row['workflow_type']
    except (KeyError, IndexError):
        workflow_type_value = 'team'  # Default for backward compatibility

    workflow_type = (
        WorkflowType.LOCAL_AUTOMATION
        if workflow_type_value == 'local'
        else WorkflowType.TEAM_WORKFLOW
    )

    # Handle is_template with backward compatibility
    try:
        is_template_value = bool(row['is_template'])
    except (KeyError, IndexError):
        is_template_value = False

    # T3-1: Handle owner_team_id and visibility with backward compatibility
    try:
        owner_team_id_value = row['owner_team_id']
    except (KeyError, IndexError):
        owner_team_id_value = None

    try:
        visibility_value = row['visibility'] or 'personal'
    except (KeyError, IndexError):
        visibility_value = 'personal'

    return Workflow(
        id=row['id'],
        name=row['name'],
        description=row['description'],
        icon=row['icon'],
        category=row['category'],
        workflow_type=workflow_type,
        stages=[Stage(**s) for s in stages_data],
        triggers=[WorkflowTrigger(**t) for t in triggers_data],
        enabled=bool(row['enabled']),
        allow_manual_creation=bool(row['allow_manual_creation']),
        require_approval_to_start=bool(row['require_approval_to_start']),
        is_template=is_template_value,
        created_by=row['created_by'],
        owner_team_id=owner_team_id_value,
        visibility=visibility_value,
        created_at=datetime.fromisoformat(row['created_at']),
        updated_at=datetime.fromisoformat(row['updated_at']),
        version=row['version'],
        tags=json.loads(row['tags']) if row['tags'] else [],
    )


def row_to_work_item(row: sqlite3.Row) -> WorkItem:
    """Convert database row to WorkItem object."""
    return WorkItem(
        id=row['id'],
        workflow_id=row['workflow_id'],
        workflow_name=row['workflow_name'],
        current_stage_id=row['current_stage_id'],
        current_stage_name=row['current_stage_name'],
        status=WorkItemStatus(row['status']),
        priority=WorkItemPriority(row['priority']),
        assigned_to=row['assigned_to'],
        claimed_at=datetime.fromisoformat(row['claimed_at']) if row['claimed_at'] else None,
        data=json.loads(row['data']),
        created_by=row['created_by'],
        created_at=datetime.fromisoformat(row['created_at']),
        updated_at=datetime.fromisoformat(row['updated_at']),
        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
        sla_due_at=datetime.fromisoformat(row['sla_due_at']) if row['sla_due_at'] else None,
        is_overdue=bool(row['is_overdue']),
        tags=json.loads(row['tags']) if row['tags'] else [],
        reference_number=row['reference_number'],
        history=[],  # Loaded separately
        attachments=[],  # Loaded separately
    )


def row_to_transition(row: sqlite3.Row) -> StageTransition:
    """Convert database row to StageTransition object."""
    return StageTransition(
        from_stage_id=row['from_stage_id'],
        to_stage_id=row['to_stage_id'],
        transitioned_at=datetime.fromisoformat(row['transitioned_at']),
        transitioned_by=row['transitioned_by'],
        notes=row['notes'],
        duration_seconds=row['duration_seconds'],
    )


def row_to_attachment(row: sqlite3.Row) -> WorkItemAttachment:
    """Convert database row to WorkItemAttachment object."""
    return WorkItemAttachment(
        id=row['id'],
        filename=row['filename'],
        file_path=row['file_path'],
        file_size=row['file_size'],
        mime_type=row['mime_type'],
        uploaded_by=row['uploaded_by'],
        uploaded_at=datetime.fromisoformat(row['uploaded_at']),
    )
