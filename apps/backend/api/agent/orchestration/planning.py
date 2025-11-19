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

try:
    from ..planner_enhanced import EnhancedPlanner
except ImportError:
    from planner_enhanced import EnhancedPlanner

try:
    from .models import PlanStep, PlanResponse
except ImportError:
    from models import PlanStep, PlanResponse

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

        # Generate plan (EnhancedPlanner.plan returns a Plan dataclass)
        plan_result = planner.plan(
            description=input_text,
            files=[]  # TODO: extract files from context_bundle
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
