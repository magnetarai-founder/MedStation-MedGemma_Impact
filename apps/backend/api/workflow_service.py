"""
Workflow Service Layer - Compatibility Facade

This file has been refactored into the api/workflows/ module.
It now serves as a backward-compatible facade for imports.

For new code, import directly from the workflows module:
    from api.workflows import router
    from api.workflows import storage, orchestrator
    from api.workflows.dependencies import get_user_team_id
"""

# Re-export everything from the new modular structure
from api.workflows import (
    router,
    storage,
    orchestrator,
    analytics,
    workflow_sync,
    setup_p2p_sync,
    get_user_team_id,
)

# Re-export models for backward compatibility
from api.workflows.dependencies import (
    Workflow,
    WorkItem,
    Stage,
    WorkItemStatus,
    WorkItemPriority,
    StageType,
    AssignmentType,
    WorkflowTriggerType,
    WorkflowType,
    CreateWorkItemRequest,
    ClaimWorkItemRequest,
    CompleteStageRequest,
    CreateWorkflowRequest,
    StageTransition,
)

__all__ = [
    "router",
    "storage",
    "orchestrator",
    "analytics",
    "workflow_sync",
    "setup_p2p_sync",
    "get_user_team_id",
    # Models
    "Workflow",
    "WorkItem",
    "Stage",
    "WorkItemStatus",
    "WorkItemPriority",
    "StageType",
    "AssignmentType",
    "WorkflowTriggerType",
    "WorkflowType",
    "CreateWorkItemRequest",
    "ClaimWorkItemRequest",
    "CompleteStageRequest",
    "CreateWorkflowRequest",
    "StageTransition",
]
