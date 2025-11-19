"""
Code modification templates (CODE_MODIFICATION category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all CODE_MODIFICATION templates."""
    return [
        NLPTemplate(
            id="CM_001",
            name="Refactor Code",
            category=IntentCategory.CODE_MODIFICATION,
            patterns=[
                r"refactor\s+(?:the\s+)?(.+)",
                r"(clean up|cleanup|improve)\s+(?:the\s+)?(?:code\s+)?(?:in\s+)?(.+)",
                r"make\s+(.+)\s+(?:more\s+)?(?:clean|readable|efficient)"
            ],
            keywords=["refactor", "clean", "improve", "optimize"],
            entities=["target_code", "improvement_type"],
            response_template="Refactoring {target_code}",
            tool_suggestions=["aider", "ollama:qwen2.5-coder"],
            examples=[
                "refactor the authentication module",
                "clean up code in main.py",
                "improve the database queries"
            ]
        ),

        NLPTemplate(
            id="CM_002",
            name="Add Feature",
            category=IntentCategory.CODE_MODIFICATION,
            patterns=[
                r"add\s+(?:a\s+)?(?:feature\s+)?(?:to\s+|for\s+)?(.+)",
                r"implement\s+(.+)\s+feature",
                r"(?:can you\s+)?add\s+(.+)\s+(?:functionality|capability)"
            ],
            keywords=["add", "feature", "implement", "functionality"],
            entities=["feature_name", "target_location", "requirements"],
            response_template="Adding {feature_name} feature",
            tool_suggestions=["aider", "workflow:feature_add"],
            examples=[
                "add dark mode to the app",
                "implement search feature",
                "add export functionality to reports"
            ]
        ),

        NLPTemplate(
            id="CM_003",
            name="Update Dependencies",
            category=IntentCategory.CODE_MODIFICATION,
            patterns=[
                r"update\s+(?:the\s+)?(?:dependencies|packages|libs|libraries)",
                r"upgrade\s+(.+)\s+(?:package|dependency|library)",
                r"(?:npm|pip|cargo)\s+update"
            ],
            keywords=["update", "upgrade", "dependencies", "packages"],
            entities=["package_manager", "packages"],
            response_template="Updating dependencies",
            tool_suggestions=["bash", "npm", "pip"],
            examples=[
                "update all dependencies",
                "upgrade React to latest version",
                "npm update packages"
            ]
        ),
    ]
