"""
Workflow Orchestrator Utilities - Helper functions

Provides pure functions for:
- Priority scoring for work item sorting
- Stage lookup in workflows
- Assignment type handling

Extracted from workflow_orchestrator.py during P2 decomposition.
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Optional

# Import workflow types
from api.workflow_models import (
    Workflow,
    Stage,
    WorkItem,
    WorkItemStatus,
    WorkItemPriority,
    AssignmentType,
)

logger = logging.getLogger(__name__)


# ===== Priority Scoring =====

# Priority to numeric score mapping (higher = more urgent)
PRIORITY_SCORES = {
    WorkItemPriority.LOW: 1,
    WorkItemPriority.NORMAL: 2,
    WorkItemPriority.HIGH: 3,
    WorkItemPriority.URGENT: 4,
}


def priority_score(priority: WorkItemPriority) -> int:
    """
    Convert priority enum to numeric score for sorting.

    Higher scores = higher priority (more urgent).

    Args:
        priority: WorkItemPriority enum value

    Returns:
        Integer score (1-4), defaults to 2 for unknown values
    """
    return PRIORITY_SCORES.get(priority, 2)


# ===== Stage Lookup =====

def find_stage(workflow: Workflow, stage_id: str) -> Optional[Stage]:
    """
    Find a stage by ID within a workflow.

    Args:
        workflow: Workflow containing stages
        stage_id: Stage ID to find

    Returns:
        Stage if found, None otherwise
    """
    for stage in workflow.stages:
        if stage.id == stage_id:
            return stage
    return None


def find_first_stage(workflow: Workflow) -> Optional[Stage]:
    """
    Find the first stage in a workflow (lowest order).

    Args:
        workflow: Workflow containing stages

    Returns:
        First stage if workflow has stages, None otherwise
    """
    if not workflow.stages:
        return None
    return min(workflow.stages, key=lambda s: s.order)


# ===== Assignment Handling =====

def apply_auto_assignment(work_item: WorkItem, stage: Stage) -> bool:
    """
    Apply automatic assignment based on stage configuration.

    Modifies work_item in place if assignment is needed.

    Args:
        work_item: Work item to potentially assign
        stage: Stage with assignment configuration

    Returns:
        True if assignment was made, False otherwise
    """
    if stage.assignment_type == AssignmentType.SPECIFIC_USER:
        if stage.assigned_user_id:
            work_item.assigned_to = stage.assigned_user_id
            work_item.status = WorkItemStatus.CLAIMED
            work_item.claimed_at = datetime.now(UTC)
            logger.info(f"👤 Auto-assigned to user: {stage.assigned_user_id}")
            return True

    elif stage.assignment_type == AssignmentType.AUTOMATION:
        work_item.assigned_to = "system"
        work_item.status = WorkItemStatus.IN_PROGRESS
        logger.info("🤖 Auto-assigned to automation")
        return True

    return False


__all__ = [
    # Priority
    "PRIORITY_SCORES",
    "priority_score",
    # Stage lookup
    "find_stage",
    "find_first_stage",
    # Assignment
    "apply_auto_assignment",
]
