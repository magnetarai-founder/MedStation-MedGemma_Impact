"""
Planner Types - Dataclasses for execution planning

Extracted from planner.py during P2 decomposition.
Contains:
- Step (single step in plan)
- Plan (execution plan)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Step:
    """Single step in execution plan"""
    description: str
    risk: str = "low"  # low, medium, high
    files: int = 0
    tool: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """Execution plan for a task"""
    steps: List["Step"]
    risks: List[str] = field(default_factory=list)
    requires_approval: bool = False
    estimated_time_min: int = 0
    model_used: str = "qwen2.5-coder:32b"
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Step",
    "Plan",
]
