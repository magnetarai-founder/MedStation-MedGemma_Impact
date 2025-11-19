"""
Research templates (RESEARCH category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all RESEARCH templates."""
    return [
        NLPTemplate(
            id="RS_001",
            name="Search Codebase",
            category=IntentCategory.RESEARCH,
            patterns=[
                r"(?:search|find|look)\s+(?:for\s+)?(.+?)(?:\s+in\s+)?(?:the\s+)?(?:code|codebase|project)?",
                r"where\s+(?:is|are)\s+(.+)\s+(?:defined|implemented|used)",
                r"(?:show me|find)\s+(?:all\s+)?(?:uses|usages|references)\s+(?:of\s+)?(.+)",
                r"search\s+for\s+all\s+(.+)"
            ],
            keywords=["search", "find", "where", "locate", "references", "all"],
            entities=["search_term", "search_scope", "file_pattern"],
            response_template="Searching for {search_term}",
            tool_suggestions=["grep", "ripgrep", "workflow:research"],
            examples=[
                "search for database connections in the code",
                "search for all database connections",
                "where is the User class defined",
                "find all uses of the authenticate function"
            ]
        ),

        NLPTemplate(
            id="RS_002",
            name="Explain Code",
            category=IntentCategory.RESEARCH,
            patterns=[
                r"explain\s+(?:this\s+)?(?:code|function|class|method):?\s*(.+)?",
                r"what\s+does\s+(?:this\s+)?(.+)\s+do",
                r"how\s+does\s+(.+)\s+work"
            ],
            keywords=["explain", "what", "how", "understand"],
            entities=["code_target", "context"],
            response_template="Explaining {code_target}",
            tool_suggestions=["ollama", "code_analysis"],
            examples=[
                "explain this function",
                "what does the auth middleware do",
                "how does the caching system work"
            ]
        ),

        NLPTemplate(
            id="RS_003",
            name="Analyze Architecture",
            category=IntentCategory.RESEARCH,
            patterns=[
                r"(?:analyze|show|explain)\s+(?:the\s+)?(?:architecture|structure)\s+(?:of\s+)?(.+)?",
                r"how\s+is\s+(?:the\s+)?(.+)\s+(?:structured|organized|architected)",
                r"(?:what\'s|what is)\s+the\s+(?:project\s+)?structure"
            ],
            keywords=["architecture", "structure", "organization", "design"],
            entities=["target_scope", "detail_level"],
            response_template="Analyzing architecture",
            tool_suggestions=["tree", "workflow:architecture_analysis"],
            examples=[
                "analyze the project architecture",
                "how is the backend structured",
                "show me the folder structure"
            ]
        ),
    ]
