"""
Workflow Automation Execution Module

Handles execution of automation stages in workflows:
- n8n workflow triggers
- Local AI processing
- Custom script execution

Extracted from workflow_orchestrator.py during P2 decomposition.
"""

import logging
from datetime import datetime, UTC
from typing import Any, Optional

logger = logging.getLogger(__name__)


def execute_automation_stage(
    work_item: Any,
    stage: Any,
    user_id: str,
    storage: Optional[Any] = None
) -> None:
    """
    Execute automation stage (n8n, local AI, or custom)

    Args:
        work_item: Work item being processed
        stage: Stage with automation config
        user_id: User ID for context
        storage: Optional storage layer for persisting changes
    """
    automation = stage.automation
    if not automation:
        logger.warning(f"No automation config for stage {stage.name}")
        return

    automation_type = automation.type

    if automation_type == "n8n":
        trigger_n8n_automation(work_item, stage, user_id)
    elif automation_type == "local_ai":
        run_local_ai_automation(work_item, stage, user_id)
    elif automation_type == "custom":
        run_custom_automation(work_item, stage, user_id)
    else:
        logger.warning(f"Unknown automation type: {automation_type}")


def trigger_n8n_automation(
    work_item: Any,
    stage: Any,
    user_id: str
) -> None:
    """
    Trigger n8n workflow execution

    Args:
        work_item: Work item being processed
        stage: Stage with n8n config
        user_id: User ID for context
    """
    import asyncio

    try:
        from api.n8n_integration import get_n8n_service
    except ImportError:
        from n8n_integration import get_n8n_service

    service = get_n8n_service()
    if not service or not service.config.enabled:
        logger.warning("n8n integration not configured or disabled")
        work_item.data['automation_error'] = "n8n not configured"
        return

    automation = stage.automation

    # Prepare work item dict for n8n
    work_item_dict = {
        'id': work_item.id,
        'workflow_id': work_item.workflow_id,
        'data': work_item.data,
        'priority': work_item.priority.value,
        'created_at': work_item.created_at.isoformat() if work_item.created_at else None
    }

    # Build stage dict
    stage_dict = {
        'id': stage.id,
        'name': stage.name,
        'automation': {
            'n8n_workflow_id': automation.n8n_workflow_id,
            'webhook_url': automation.n8n_webhook_url
        }
    }

    async def execute():
        try:
            result = await service.execute_automation_stage(work_item_dict, stage_dict)
            logger.info(f"✅ n8n automation triggered for work item {work_item.id}")

            # Store execution reference
            work_item.data['n8n_execution'] = {
                'triggered_at': datetime.now(UTC).isoformat(),
                'status': 'pending'
            }

        except Exception as e:
            logger.error(f"❌ n8n automation failed for work item {work_item.id}: {e}")
            work_item.data['automation_error'] = str(e)

    # Run async in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(execute())
        else:
            loop.run_until_complete(execute())
    except RuntimeError:
        # No event loop, create one
        asyncio.run(execute())


def run_local_ai_automation(
    work_item: Any,
    stage: Any,
    user_id: str
) -> None:
    """
    Run local AI processing for automation stage

    Args:
        work_item: Work item being processed
        stage: Stage with AI config
        user_id: User ID for context
    """
    automation = stage.automation
    if not automation:
        return

    model = automation.ai_model or "llama3"
    prompt_template = automation.ai_prompt_template

    if not prompt_template:
        logger.warning(f"No AI prompt template for stage {stage.name}")
        return

    # Format prompt with work item data
    try:
        prompt = prompt_template.format(**work_item.data)
    except KeyError as e:
        logger.warning(f"Missing data key for AI prompt: {e}")
        prompt = prompt_template

    # Store that AI processing was triggered
    work_item.data['ai_automation'] = {
        'model': model,
        'status': 'pending',
        'triggered_at': datetime.now(UTC).isoformat()
    }

    logger.info(f"🧠 Local AI automation queued: {model}")
    # Actual AI processing would be handled by a background worker


def run_custom_automation(
    work_item: Any,
    stage: Any,
    user_id: str
) -> None:
    """
    Run custom script automation

    Args:
        work_item: Work item being processed
        stage: Stage with custom script config
        user_id: User ID for context
    """
    automation = stage.automation
    if not automation or not automation.custom_script_path:
        logger.warning(f"No custom script path for stage {stage.name}")
        return

    # Store that custom automation was triggered
    work_item.data['custom_automation'] = {
        'script': automation.custom_script_path,
        'status': 'pending',
        'triggered_at': datetime.now(UTC).isoformat()
    }

    logger.info(f"📜 Custom automation queued: {automation.custom_script_path}")
    # Actual script execution would be handled by a background worker


__all__ = [
    "execute_automation_stage",
    "trigger_n8n_automation",
    "run_local_ai_automation",
    "run_custom_automation",
]
