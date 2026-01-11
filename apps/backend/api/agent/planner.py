"""
Base planner implementation for agent system

Module structure (P2 decomposition):
- planner_types.py: Step, Plan dataclasses
- planner.py: Planner class (this file)
"""

import logging
from typing import List, Optional

# Import from extracted module (P2 decomposition)
from api.agent.planner_types import Step, Plan

logger = logging.getLogger(__name__)


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
