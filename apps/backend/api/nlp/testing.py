"""
Testing templates (TESTING category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all TESTING templates."""
    return [
        NLPTemplate(
            id="CG_004",
            name="Generate Test",
            category=IntentCategory.TESTING,
            patterns=[
                r"(write|create|add|generate)\s+(?:a\s+)?test(?:s)?\s+(?:for\s+)?(.+)",
                r"test\s+(?:for\s+|that\s+)?(.+)",
                r"(?:unit\s+)?test\s+(.+)"
            ],
            keywords=["test", "testing", "unit", "coverage"],
            entities=["test_target", "test_type", "assertions"],
            response_template="Generating tests for {test_target}",
            tool_suggestions=["aider", "pytest", "workflow:test_gen"],
            examples=[
                "write tests for the auth module",
                "create unit tests for user class",
                "add test coverage for API endpoints"
            ]
        ),
    ]
