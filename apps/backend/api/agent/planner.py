"""
Base planner implementation for agent system
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


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
    steps: List[Step]
    risks: List[str] = field(default_factory=list)
    requires_approval: bool = False
    estimated_time_min: int = 0
    model_used: str = "qwen2.5-coder:32b"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """Base planner for generating execution plans"""

    def __init__(self):
        self.risk_keywords = {
            'high': ['delete', 'remove', 'drop', 'truncate', 'rm -rf', 'format', 'wipe'],
            'medium': ['modify', 'update', 'change', 'alter', 'migrate', 'refactor'],
            'low': ['add', 'create', 'read', 'list', 'show', 'display']
        }

    def plan(self, description: str, files: Optional[List[str]] = None) -> Plan:
        """
        Generate execution plan from task description

        Args:
            description: Task description
            files: Optional list of files to operate on

        Returns:
            Plan object with steps and risk assessment
        """
        # Basic planning logic
        steps = self._parse_steps(description, files or [])
        risks = self._assess_risks(description, steps)
        requires_approval = any(s.risk == 'high' for s in steps) or len(steps) > 5

        return Plan(
            steps=steps,
            risks=risks,
            requires_approval=requires_approval,
            estimated_time_min=len(steps) * 2,  # Rough estimate: 2 min per step
            model_used="qwen2.5-coder:32b"
        )

    def _parse_steps(self, description: str, files: List[str]) -> List[Step]:
        """Parse description into steps"""
        # Simple heuristic parsing
        desc_lower = description.lower()

        steps = []

        # Check for common task patterns
        if 'create' in desc_lower or 'add' in desc_lower or 'implement' in desc_lower:
            steps.append(Step(
                description=f"Create/implement: {description[:50]}...",
                risk="low",
                files=len(files)
            ))

        if 'modify' in desc_lower or 'update' in desc_lower or 'change' in desc_lower:
            steps.append(Step(
                description=f"Modify: {description[:50]}...",
                risk="medium",
                files=len(files)
            ))

        if 'delete' in desc_lower or 'remove' in desc_lower:
            steps.append(Step(
                description=f"Delete/remove: {description[:50]}...",
                risk="high",
                files=len(files)
            ))

        if 'test' in desc_lower:
            steps.append(Step(
                description="Run tests",
                risk="low",
                files=0
            ))

        # Default: single step if no patterns matched
        if not steps:
            steps.append(Step(
                description=description[:100],
                risk="medium",
                files=len(files)
            ))

        return steps

    def _assess_risks(self, description: str, steps: List[Step]) -> List[str]:
        """Assess risks in the plan"""
        risks = []
        desc_lower = description.lower()

        # Check for high-risk keywords
        for keyword in self.risk_keywords['high']:
            if keyword in desc_lower:
                risks.append(f"Destructive operation detected: {keyword}")

        # Check for file count risk
        total_files = sum(s.files for s in steps)
        if total_files > 10:
            risks.append(f"Large file count: {total_files} files affected")

        # Check for high-risk steps
        high_risk_steps = [s for s in steps if s.risk == 'high']
        if high_risk_steps:
            risks.append(f"{len(high_risk_steps)} high-risk step(s) require careful review")

        return risks
