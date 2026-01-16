"""Backward Compatibility Shim - use api.workflows.enums instead."""

from api.workflows.enums import (
    WorkflowTriggerType,
    StageType,
    WorkItemStatus,
    WorkItemPriority,
    AssignmentType,
    ConditionOperator,
    FieldType,
    WorkflowType,
    NotificationEvent,
    get_all_workflow_statuses,
    get_active_statuses,
    get_terminal_statuses,
    is_human_stage,
    is_ai_stage,
)

__all__ = [
    "WorkflowTriggerType",
    "StageType",
    "WorkItemStatus",
    "WorkItemPriority",
    "AssignmentType",
    "ConditionOperator",
    "FieldType",
    "WorkflowType",
    "NotificationEvent",
    "get_all_workflow_statuses",
    "get_active_statuses",
    "get_terminal_statuses",
    "is_human_stage",
    "is_ai_stage",
]
