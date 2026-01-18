"""
Agent Orchestration - Plan Generation

Plan generation for code tasks using EnhancedPlanner:
- Generate execution plans
- Map plan dataclass to response format
- Risk assessment
- Time estimation

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
from typing import Optional, Dict, Any

from ..planner_enhanced import EnhancedPlanner
from .models import PlanStep, PlanResponse

logger = logging.getLogger(__name__)


def generate_plan_logic(
    input_text: str,
    context_bundle: Optional[Dict[str, Any]] = None
) -> PlanResponse:
    """
    Generate execution plan for a code task.

    Uses EnhancedPlanner to generate a plan dataclass, then maps to PlanResponse.

    Args:
        input_text: User requirement/task description
        context_bundle: Optional context from /agent/context endpoint

    Returns:
        PlanResponse with steps, risks, confirmation requirement, time estimate

    Raises:
        Exception if planning fails
    """
    try:
        # Use enhanced planner
        planner = EnhancedPlanner()

        # Extract files from context_bundle
        files = []
        if context_bundle:
            # Primary source: file_tree_slice from ContextResponse
            if "file_tree_slice" in context_bundle:
                files.extend(context_bundle["file_tree_slice"])

            # Secondary source: extract changed files from recent_diffs
            if "recent_diffs" in context_bundle:
                for diff in context_bundle["recent_diffs"]:
                    # diff_stat contains "file | +N -M" lines
                    diff_stat = diff.get("diff_stat", "")
                    for line in diff_stat.split("\n"):
                        line = line.strip()
                        if "|" in line:
                            # Extract filename before the pipe
                            filename = line.split("|")[0].strip()
                            if filename and filename not in files:
                                files.append(filename)

        # Generate plan (EnhancedPlanner.plan returns a Plan dataclass)
        plan_result = planner.plan(
            description=input_text,
            files=files
        )

        # Map Plan dataclass to our response format
        steps = []
        for step in plan_result.steps:
            steps.append(PlanStep(
                description=step.description,
                risk_level=step.risk,
                estimated_files=step.files
            ))

        risks = plan_result.risks
        requires_confirmation = plan_result.requires_approval

        return PlanResponse(
            steps=steps,
            risks=risks,
            requires_confirmation=requires_confirmation,
            estimated_time_min=plan_result.estimated_time_min,
            model_used=plan_result.model_used
        )

    except Exception as e:
        # Log full error and re-raise
        logger.error(f"Planning failed: {e}", exc_info=True)
        raise Exception("Failed to generate plan. Please try again.") from e
