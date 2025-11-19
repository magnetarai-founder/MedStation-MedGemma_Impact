"""
Documentation templates (DOCUMENTATION category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all DOCUMENTATION templates."""
    return [
        NLPTemplate(
            id="DC_001",
            name="Write Documentation",
            category=IntentCategory.DOCUMENTATION,
            patterns=[
                r"(?:write|create|add)\s+(?:documentation|docs)\s+(?:for\s+)?(.+)",
                r"document\s+(?:the\s+)?(.+)",
                r"add\s+(?:code\s+)?comments\s+(?:to\s+)?(.+)"
            ],
            keywords=["documentation", "document", "docs", "comments"],
            entities=["doc_target", "doc_type", "detail_level"],
            response_template="Writing documentation for {doc_target}",
            tool_suggestions=["aider", "markdown", "workflow:doc_gen"],
            examples=[
                "write documentation for the API",
                "document the User class",
                "add comments to main.py"
            ]
        ),

        NLPTemplate(
            id="DC_002",
            name="Generate README",
            category=IntentCategory.DOCUMENTATION,
            patterns=[
                r"(?:create|write|generate)\s+(?:a\s+)?readme",
                r"(?:update|improve)\s+(?:the\s+)?readme",
                r"add\s+(.+)\s+to\s+(?:the\s+)?readme"
            ],
            keywords=["readme", "create", "generate"],
            entities=["readme_sections", "project_info"],
            response_template="Generating README",
            tool_suggestions=["workflow:readme_gen", "markdown"],
            examples=[
                "create a README file",
                "update the README with installation steps",
                "add usage examples to README"
            ]
        ),

        NLPTemplate(
            id="DC_003",
            name="API Documentation",
            category=IntentCategory.DOCUMENTATION,
            patterns=[
                r"(?:document|write docs for)\s+(?:the\s+)?api",
                r"(?:create|generate)\s+api\s+(?:docs|documentation)"
            ],
            keywords=["api", "documentation", "swagger", "openapi"],
            entities=["api_endpoints", "format"],
            response_template="Generating API documentation",
            tool_suggestions=["swagger", "openapi", "workflow:doc_gen"],
            examples=["document the API", "create API docs", "generate swagger documentation"]
        ),

        NLPTemplate(
            id="DC_004",
            name="Code Comments",
            category=IntentCategory.DOCUMENTATION,
            patterns=[
                r"(?:add|write)\s+comments\s+(?:to|in)\s+(.+)",
                r"comment\s+(?:the\s+)?(?:code\s+)?(?:in\s+)?(.+)"
            ],
            keywords=["comment", "comments", "annotate"],
            entities=["file_path", "comment_style"],
            response_template="Adding comments to {file_path}",
            tool_suggestions=["aider", "editor"],
            examples=["add comments to main.py", "comment the code", "write comments in functions"]
        ),
    ]
