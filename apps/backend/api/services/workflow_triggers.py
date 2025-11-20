"""
Workflow Trigger Service (Phase D)
Handles event-based workflow triggering
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from ..workflow_models import (
        WorkflowTriggerType,
        WorkItem,
        WorkItemStatus,
        WorkItemPriority,
    )
    from ..workflow_storage import WorkflowStorage
except ImportError:
    from workflow_models import (
        WorkflowTriggerType,
        WorkItem,
        WorkItemStatus,
        WorkItemPriority,
    )
    from workflow_storage import WorkflowStorage

logger = logging.getLogger(__name__)


def handle_agent_event(
    event: Dict[str, Any],
    storage: WorkflowStorage,
    user_id: str,
    team_id: Optional[str] = None,
) -> List[str]:
    """
    Handle agent events and create WorkItems for matching workflows.

    Phase D: Agent → Workflow integration.
    Called after agent operations (apply, plan complete, etc.) to trigger workflows.

    Args:
        event: Agent event dictionary with:
            - type: str (e.g. "agent.apply.success", "agent.plan.complete")
            - user_id: str
            - repo_root: str
            - files: List[str] (optional)
            - patch_id: str (optional)
            - summary: str (optional)
            - session_id: str (optional)
        storage: WorkflowStorage instance
        user_id: User ID for isolation
        team_id: Optional team ID for team workflows

    Returns:
        List of created WorkItem IDs

    Example event:
        {
            "type": "agent.apply.success",
            "user_id": "user_123",
            "repo_root": "/path/to/repo",
            "files": ["src/main.py", "tests/test_main.py"],
            "patch_id": "patch_abc123",
            "summary": "Implemented new feature X",
            "session_id": "session_def456"
        }
    """
    if not event or "type" not in event:
        logger.warning("⚠ handle_agent_event called with invalid event (no type)")
        return []

    event_type = event["type"]
    logger.info(f"🔔 Processing agent event: {event_type}")

    try:
        # Find all workflows with ON_AGENT_EVENT triggers matching this event type
        all_workflows = storage.list_workflows(
            user_id=user_id,
            enabled_only=True,
            team_id=team_id,
        )

        matching_workflows = []
        for workflow in all_workflows:
            for trigger in workflow.triggers:
                if (
                    trigger.trigger_type == WorkflowTriggerType.ON_AGENT_EVENT
                    and trigger.enabled
                    and trigger.agent_event_type == event_type
                ):
                    matching_workflows.append(workflow)
                    break  # Only match once per workflow

        if not matching_workflows:
            logger.debug(f"No workflows match event type: {event_type}")
            return []

        logger.info(f"📋 Found {len(matching_workflows)} workflow(s) matching event: {event_type}")

        # Create WorkItems for each matching workflow
        created_work_item_ids = []
        for workflow in matching_workflows:
            # Skip if workflow is a template
            if workflow.is_template:
                logger.debug(f"Skipping template workflow: {workflow.name}")
                continue

            # Get the initial stage
            if not workflow.stages:
                logger.warning(f"Workflow {workflow.name} has no stages, skipping")
                continue

            initial_stage = workflow.stages[0]

            # Create WorkItem
            work_item = WorkItem(
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                current_stage_id=initial_stage.id,
                current_stage_name=initial_stage.name,
                status=WorkItemStatus.PENDING,
                priority=WorkItemPriority.NORMAL,
                data={
                    "agent_event": event,  # Store the full event
                    "triggered_by": "agent_event",
                    "event_type": event_type,
                },
                created_by=user_id,
            )

            # Save to storage
            storage.save_work_item(work_item, user_id)
            created_work_item_ids.append(work_item.id)

            logger.info(
                f"✅ Created WorkItem {work_item.id} in workflow '{workflow.name}' "
                f"(stage: {initial_stage.name}) from event: {event_type}"
            )

        return created_work_item_ids

    except Exception as e:
        # Graceful degradation - log error but don't crash caller
        logger.error(f"❌ Error handling agent event {event_type}: {e}", exc_info=True)
        return []


def handle_file_event(
    event: Dict[str, Any],
    storage: WorkflowStorage,
    user_id: str,
    team_id: Optional[str] = None,
) -> List[str]:
    """
    Handle file pattern events and create WorkItems for matching workflows.

    Phase D: File trigger support (skeleton for future implementation).

    Args:
        event: File event dictionary with:
            - type: str ("file.created", "file.modified", etc.)
            - file_path: str
            - repo_root: str
            - operation: str ("create", "modify", "delete")
        storage: WorkflowStorage instance
        user_id: User ID for isolation
        team_id: Optional team ID for team workflows

    Returns:
        List of created WorkItem IDs

    Note: This is a skeleton implementation. Full file watching/pattern matching
    would require integration with a file system watcher service.
    """
    if not event or "type" not in event:
        logger.warning("⚠ handle_file_event called with invalid event (no type)")
        return []

    event_type = event["type"]
    file_path = event.get("file_path", "")
    logger.info(f"🔔 Processing file event: {event_type} for {file_path}")

    try:
        # Find all workflows with ON_FILE_PATTERN triggers
        all_workflows = storage.list_workflows(
            user_id=user_id,
            enabled_only=True,
            team_id=team_id,
        )

        matching_workflows = []
        for workflow in all_workflows:
            for trigger in workflow.triggers:
                if (
                    trigger.trigger_type == WorkflowTriggerType.ON_FILE_PATTERN
                    and trigger.enabled
                    and trigger.file_pattern
                ):
                    # Simple pattern matching (could be enhanced with glob/regex)
                    if trigger.file_pattern in file_path:
                        matching_workflows.append(workflow)
                        break

        if not matching_workflows:
            logger.debug(f"No workflows match file pattern for: {file_path}")
            return []

        logger.info(f"📋 Found {len(matching_workflows)} workflow(s) matching file: {file_path}")

        # Create WorkItems for each matching workflow
        created_work_item_ids = []
        for workflow in matching_workflows:
            if workflow.is_template:
                continue

            if not workflow.stages:
                continue

            initial_stage = workflow.stages[0]

            work_item = WorkItem(
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                current_stage_id=initial_stage.id,
                current_stage_name=initial_stage.name,
                status=WorkItemStatus.PENDING,
                priority=WorkItemPriority.NORMAL,
                data={
                    "file_event": event,
                    "triggered_by": "file_pattern",
                    "file_path": file_path,
                },
                created_by=user_id,
            )

            storage.save_work_item(work_item, user_id)
            created_work_item_ids.append(work_item.id)

            logger.info(
                f"✅ Created WorkItem {work_item.id} in workflow '{workflow.name}' "
                f"from file event: {file_path}"
            )

        return created_work_item_ids

    except Exception as e:
        logger.error(f"❌ Error handling file event: {e}", exc_info=True)
        return []
