"""
Workflow Agent Integration Service (Phase B)

Provides Agent Assist functionality for workflow stages.
When a WorkItem enters an AGENT_ASSIST stage, this service:
- Builds context using agent orchestration
- Generates plan recommendations
- Stores suggestions in WorkItem data (non-destructive, advisory only)
"""

import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

from api.workflow_models import WorkItem, Stage, StageType
from api.workflow_storage import WorkflowStorage
from api.agent.orchestration.models import ContextRequest, ContextResponse
from api.agent.orchestration import context_bundle as context_mod
from api.agent.orchestration import planning as planning_mod
from api.config_paths import get_config_paths

# Optional audit/metrics - graceful degradation if unavailable
try:
    from api.audit_logger import AuditAction, audit_log_sync
    from api.metrics import get_metrics
except ImportError:
    AuditAction = None
    audit_log_sync = lambda *args, **kwargs: None
    get_metrics = lambda: None

logger = logging.getLogger(__name__)
metrics = get_metrics() if get_metrics() else None


def _get_default_agent_prompt_for_stage(stage: Stage, work_item: WorkItem) -> str:
    """
    Get default agent prompt based on stage type (AGENT-PHASE-1).

    If stage.agent_prompt is explicitly set, returns it unchanged.
    Otherwise, provides opinionated defaults for specialized stage types:
    - CODE_REVIEW: Focus on code quality, security, maintainability
    - TEST_ENRICHMENT: Focus on test coverage and edge cases
    - DOC_UPDATE: Focus on documentation and release notes

    Args:
        stage: Stage configuration
        work_item: WorkItem context

    Returns:
        Agent prompt string to use for planning
    """
    # If stage has explicit prompt, use it
    if stage.agent_prompt and stage.agent_prompt.strip():
        return stage.agent_prompt

    # Choose default based on stage_type
    stage_type = stage.stage_type

    if stage_type == StageType.CODE_REVIEW:
        return (
            "You are a senior code reviewer. Review the following changes for "
            "correctness, readability, maintainability, and security risks. "
            "Summarize key issues and provide actionable recommendations. "
            "Focus on: potential bugs, code smell, security vulnerabilities, "
            "performance concerns, and adherence to best practices."
        )

    elif stage_type == StageType.TEST_ENRICHMENT:
        return (
            "You are a test engineer. Based on the code changes and description, "
            "propose comprehensive test cases that validate the behavior and guard "
            "against regressions. Include: unit tests for core logic, integration "
            "tests for component interactions, edge cases, error scenarios, and "
            "boundary conditions. Suggest both positive and negative test cases."
        )

    elif stage_type == StageType.DOC_UPDATE:
        return (
            "You are a technical writer. Review the code changes and update or "
            "propose documentation to reflect these changes. Focus on: API "
            "documentation, user-facing release notes, architectural decisions, "
            "migration guides (if breaking changes), and examples. Ensure clarity, "
            "correctness, and appropriate detail for the target audience."
        )

    else:
        # Fallback for AGENT_ASSIST or other types
        return f"Assist with stage '{stage.name}' for workflow '{work_item.workflow_name}'"


def run_agent_assist_for_stage(
    storage: WorkflowStorage,
    work_item: WorkItem,
    stage: Stage,
    user_id: str,
) -> None:
    """
    Run Agent Assist for a given work item & stage.

    Behavior (Phase B - Advisory Only, Phase E - Optional Auto-Apply):
    - Build context for the agent using repo_root from work item data or config paths
    - Call agent context logic to gather file tree, recent diffs, etc.
    - Call agent planning logic to generate plan and recommendations
    - Store results under work_item.data["agent_recommendation"]
    - Persist work item via storage
    - Phase E: If stage.agent_auto_apply=True, applies patches automatically (requires code.edit permission)

    Args:
        storage: WorkflowStorage instance for persisting work item
        work_item: WorkItem entering the Agent Assist stage
        stage: Stage configuration with agent_prompt, agent_auto_apply, and other settings
        user_id: User ID for audit/permissions

    Side Effects:
        - Updates work_item.data["agent_recommendation"] with plan summary, steps, risks
        - Phase E: If auto-apply enabled, updates work_item.data["agent_auto_apply_result"]
        - Saves work_item to storage
        - Logs errors to work_item.data["agent_recommendation_error"] if agent fails
    """
    start_time = time.perf_counter()

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

        # Audit log start
        if AuditAction:
            audit_log_sync(
                user_id=user_id,
                action=AuditAction.WORKFLOW_AGENT_ASSIST_STARTED,
                resource="workflow_work_item",
                resource_id=work_item.id,
                details={
                    "workflow_id": work_item.workflow_id,
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "agent_auto_apply": stage.agent_auto_apply
                }
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

        # Build prompt for planning (AGENT-PHASE-1: Use opinionated defaults)
        prompt = _get_default_agent_prompt_for_stage(stage, work_item)

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

        # Phase E: Auto-apply if stage.agent_auto_apply is True
        if stage.agent_auto_apply:
            logger.info(
                f"🤖 Phase E: Auto-apply enabled for stage {stage.name}, applying agent patches",
                extra={"work_item_id": work_item.id, "stage_name": stage.name}
            )

            try:
                # Import apply logic
                from api.agent.orchestration.apply import apply_plan_logic
                from api.agent.orchestration.models import ApplyRequest

                # Build apply request from plan
                apply_req = ApplyRequest(
                    input=prompt,
                    repo_root=repo_root,
                    files=[],  # Let agent determine files
                    session_id=None,  # No session for workflow-triggered applies
                    model=stage.agent_model_hint,  # Use stage hint if specified
                    dry_run=False,  # Real apply
                )

                # Apply the plan (this may raise exceptions)
                current_user = {"user_id": user_id}
                patches, patch_id, engine_used = apply_plan_logic(apply_req, current_user)

                # Record auto-apply result
                work_item.data.setdefault("agent_auto_apply_result", {})
                work_item.data["agent_auto_apply_result"].update({
                    "success": True,
                    "patch_id": patch_id,
                    "files_changed": [p.path for p in patches],
                    "engine_used": engine_used,
                    "summary": f"Auto-applied {len(patches)} patch(es)",
                })

                logger.info(
                    f"✅ Auto-apply succeeded for work item {work_item.id}: patch_id={patch_id}",
                    extra={
                        "work_item_id": work_item.id,
                        "patch_id": patch_id,
                        "files_changed": len(patches),
                    }
                )

            except Exception as auto_apply_error:
                # Log error but don't fail the entire Agent Assist operation
                logger.warning(
                    f"⚠ Auto-apply failed for work item {work_item.id}: {auto_apply_error}",
                    exc_info=True,
                    extra={"work_item_id": work_item.id}
                )
                work_item.data.setdefault("agent_auto_apply_result", {})
                work_item.data["agent_auto_apply_result"].update({
                    "success": False,
                    "error": str(auto_apply_error),
                })

                # Metrics for auto-apply failure
                if metrics:
                    metrics.record("workflow.agent_auto_apply.failures", 0, error=True)

        # Persist work item (with auto-apply results if applicable)
        storage.save_work_item(work_item, user_id=user_id)

        # Audit log completion
        if AuditAction:
            audit_log_sync(
                user_id=user_id,
                action=AuditAction.WORKFLOW_AGENT_ASSIST_COMPLETED,
                resource="workflow_work_item",
                resource_id=work_item.id,
                details={
                    "workflow_id": work_item.workflow_id,
                    "stage_id": stage.id,
                    "engine_used": work_item.data.get("agent_recommendation", {}).get("engine_used"),
                    "model_used": work_item.data.get("agent_recommendation", {}).get("model_used"),
                    "steps_count": len(work_item.data.get("agent_recommendation", {}).get("steps", [])),
                    "risks_count": len(work_item.data.get("agent_recommendation", {}).get("risks", []))
                }
            )

        # Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        if metrics:
            metrics.record("workflow.agent_assist.runs", duration_ms, error=False)
            if stage.agent_auto_apply:
                metrics.record("workflow.agent_auto_apply.attempts", 0, error=False)

        logger.info(
            f"Agent Assist completed for work item {work_item.id} in stage {stage.name}",
            extra={
                "work_item_id": work_item.id,
                "stage_name": stage.name,
                "steps_count": len(plan_response.steps),
                "model_used": plan_response.model_used,
                "auto_apply": stage.agent_auto_apply,
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

        # Audit log error
        if AuditAction:
            audit_log_sync(
                user_id=user_id,
                action=AuditAction.WORKFLOW_AGENT_ASSIST_ERROR,
                resource="workflow_work_item",
                resource_id=work_item.id,
                details={
                    "workflow_id": work_item.workflow_id,
                    "stage_id": stage.id,
                    "error_type": type(e).__name__,
                    "message": str(e)[:200]
                }
            )

        # Metrics
        if metrics:
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics.record("workflow.agent_assist.runs", duration_ms, error=True)
            metrics.record("workflow.agent_assist.failures", 0, error=True)
