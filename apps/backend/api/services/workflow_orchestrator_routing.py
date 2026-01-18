"""
Workflow Orchestrator Routing - Conditional routing logic

Provides pure functions for:
- Condition evaluation (AND logic)
- Operator comparisons (EQUALS, NOT_EQUALS, GREATER_THAN, etc.)

Extracted from workflow_orchestrator.py during P2 decomposition.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any

# Import condition types
from api.workflow_models import (
    ConditionOperator,
    RoutingCondition,
)

logger = logging.getLogger(__name__)


def evaluate_conditions(
    conditions: List[RoutingCondition],
    data: Dict[str, Any]
) -> bool:
    """
    Evaluate all conditions using AND logic.

    Each condition checks a field in the data against a target value
    using the specified operator.

    Args:
        conditions: List of RoutingCondition to evaluate
        data: Work item data dictionary

    Returns:
        True if ALL conditions match, False otherwise

    Supported operators:
        - EQUALS: field_value == target_value
        - NOT_EQUALS: field_value != target_value
        - GREATER_THAN: field_value > target_value
        - LESS_THAN: field_value < target_value
        - CONTAINS: target_value in str(field_value)
        - NOT_CONTAINS: target_value not in str(field_value)
        - IS_TRUE: bool(field_value) is True
        - IS_FALSE: bool(field_value) is False
    """
    for condition in conditions:
        if not evaluate_single_condition(condition, data):
            return False
    return True


def evaluate_single_condition(
    condition: RoutingCondition,
    data: Dict[str, Any]
) -> bool:
    """
    Evaluate a single routing condition against data.

    Args:
        condition: RoutingCondition with field, operator, and value
        data: Work item data dictionary

    Returns:
        True if condition matches, False otherwise
    """
    field_value = data.get(condition.field)
    target_value = condition.value

    # Evaluate based on operator
    if condition.operator == ConditionOperator.EQUALS:
        return field_value == target_value

    elif condition.operator == ConditionOperator.NOT_EQUALS:
        return field_value != target_value

    elif condition.operator == ConditionOperator.GREATER_THAN:
        if field_value is None:
            return False
        return field_value > target_value

    elif condition.operator == ConditionOperator.LESS_THAN:
        if field_value is None:
            return False
        return field_value < target_value

    elif condition.operator == ConditionOperator.CONTAINS:
        if field_value is None:
            return False
        return target_value in str(field_value)

    elif condition.operator == ConditionOperator.NOT_CONTAINS:
        if field_value is None:
            return True  # None doesn't contain anything
        return target_value not in str(field_value)

    elif condition.operator == ConditionOperator.IS_TRUE:
        return bool(field_value)

    elif condition.operator == ConditionOperator.IS_FALSE:
        return not bool(field_value)

    # Unknown operator - fail safe
    logger.warning(f"Unknown condition operator: {condition.operator}")
    return False


__all__ = [
    "evaluate_conditions",
    "evaluate_single_condition",
]
