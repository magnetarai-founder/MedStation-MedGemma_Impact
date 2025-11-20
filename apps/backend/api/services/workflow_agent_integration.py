"""
Workflow Agent Integration Service (Phase B)

Provides Agent Assist functionality for workflow stages.
When a WorkItem enters an AGENT_ASSIST stage, this service:
- Builds context using agent orchestration
- Generates plan recommendations
- Stores suggestions in WorkItem data (non-destructive, advisory only)
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from api.workflow_models import WorkItem, Stage
    from api.workflow_storage import WorkflowStorage
    from api.agent.orchestration.models import ContextRequest, ContextResponse
    from api.agent.orchestration import context_bundle as context_mod
    from api.agent.orchestration import planning as planning_mod
    from api.config_paths import get_config_paths
except ImportError:
    from workflow_models import WorkItem, Stage
    from workflow_storage import WorkflowStorage
    from agent.orchestration.models import ContextRequest, ContextResponse
    from agent.orchestration import context_bundle as context_mod
    from agent.orchestration import planning as planning_mod
    from config_paths import get_config_paths

logger = logging.getLogger(__name__)


def run_agent_assist_for_stage(
    storage: WorkflowStorage,
    work_item: WorkItem,
    stage: Stage,
    user_id: str,
) -> None:
    """
    Run Agent Assist for a given work item & stage.

    Behavior (Phase B - Advisory Only):
    - Build context for the agent using repo_root from work item data or config paths
    - Call agent context logic to gather file tree, recent diffs, etc.
    - Call agent planning logic to generate plan and recommendations
    - Store results under work_item.data["agent_recommendation"]
    - Persist work item via storage
    - Does NOT auto-apply any patches or changes

    Args:
        storage: WorkflowStorage instance for persisting work item
        work_item: WorkItem entering the Agent Assist stage
        stage: Stage configuration with agent_prompt and other settings
        user_id: User ID for audit/permissions

    Side Effects:
        - Updates work_item.data["agent_recommendation"] with plan summary, steps, risks
        - Saves work_item to storage
        - Logs errors to work_item.data["agent_recommendation_error"] if agent fails
    """
    try:
        # Determine repo_root from work item data or fallback to config
        paths = get_config_paths()
        repo_root = work_item.data.get("repo_root")
        if not repo_root:
            # Fallback to a sensible default
            repo_root = str(paths.repo_root) if hasattr(paths, 'repo_root') else str(Path.cwd())

        logger.info(
            f"Agent Assist starting for work item {work_item.id} in stage {stage.name}",
            extra={"work_item_id": work_item.id, "stage_name": stage.name, "repo_root": repo_root}
        )

        # Build context request for agent
        ctx_req = ContextRequest(
            session_id=None,
            cwd=None,
            repo_root=repo_root,
            open_files=[],
        )

        # Fake current_user dict for context (only user_id is needed)
        current_user: Dict[str, Any] = {"user_id": user_id}

        # Build context bundle using agent context logic
        ctx_response: ContextResponse = context_mod.build_context_bundle(
            body=ctx_req,
            current_user=current_user,
            paths=paths,
        )

        # Build prompt for planning
        prompt = stage.agent_prompt
        if not prompt:
            # Fallback prompt if stage doesn't specify one
            prompt = f"Assist with stage '{stage.name}' for workflow '{work_item.workflow_name}'"

        # Add target path hint if specified
        if stage.agent_target_path:
            prompt = f"{prompt}\n\nFocus on: {stage.agent_target_path}"

        # Generate plan using agent planning logic
        plan_response = planning_mod.generate_plan_logic(
            input_text=prompt,
            context_bundle=ctx_response.model_dump() if ctx_response else None,
        )

        # For Phase B: do NOT auto-apply patches. Just store recommendation metadata.
        work_item.data.setdefault("agent_recommendation", {})
        work_item.data["agent_recommendation"].update(
            {
                "plan_summary": " ".join(
                    step.description for step in plan_response.steps
                )[:2000],  # Truncate to 2000 chars for storage
                "engine_used": "planner",  # Phase B uses planner engine
                "model_used": plan_response.model_used,
                "steps": [
                    {
                        "description": step.description,
                        "risk_level": step.risk_level,
                        "estimated_files": step.estimated_files,
                    }
                    for step in plan_response.steps
                ],
                "risks": plan_response.risks,
                "requires_confirmation": plan_response.requires_confirmation,
                "estimated_time_min": plan_response.estimated_time_min,
            }
        )

        # Clear any previous errors
        if "agent_recommendation_error" in work_item.data:
            del work_item.data["agent_recommendation_error"]

        # Persist work item
        storage.save_work_item(work_item, user_id=user_id)

        logger.info(
            f"Agent Assist completed for work item {work_item.id} in stage {stage.name}",
            extra={
                "work_item_id": work_item.id,
                "stage_name": stage.name,
                "steps_count": len(plan_response.steps),
                "model_used": plan_response.model_used,
            }
        )

    except Exception as e:
        logger.error(
            f"Agent Assist failed for work item {work_item.id}: {e}",
            exc_info=True,
            extra={"work_item_id": work_item.id, "stage_name": stage.name}
        )
        # Record error in WorkItem data but do not raise (graceful degradation)
        work_item.data.setdefault("agent_recommendation_error", str(e))
        # Clear partial recommendations if error occurred
        if "agent_recommendation" in work_item.data:
            del work_item.data["agent_recommendation"]
        storage.save_work_item(work_item, user_id=user_id)
