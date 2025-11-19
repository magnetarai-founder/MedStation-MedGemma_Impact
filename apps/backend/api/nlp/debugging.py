"""
Debugging templates (DEBUGGING category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all DEBUGGING templates."""
    return [
        NLPTemplate(
            id="DB_001",
            name="Fix Bug",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"fix\s+(?:the\s+)?(?:bug|issue|problem|error)(?:\s+in\s+|with\s+)?(.+)?",
                r"(?:there\'s\s+)?(?:a\s+)?bug(?:\s+in\s+)?(.+)?",
                r"(.+)\s+(?:is\s+)?(?:not\s+working|broken|failing)",
                r"fix\s+(?:the\s+)?bug"
            ],
            keywords=["fix", "bug", "error", "issue", "broken"],
            entities=["bug_location", "error_message", "symptoms"],
            response_template="Fixing bug",
            tool_suggestions=["aider", "workflow:bug_fix", "debugger"],
            examples=[
                "fix the bug in authentication",
                "fix the bug",
                "there's a bug in the payment module",
                "the login form is not working"
            ]
        ),

        NLPTemplate(
            id="DB_002",
            name="Debug Code",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"debug\s+(?:the\s+)?(.+)",
                r"(?:help me\s+)?(?:find|locate)\s+(?:the\s+)?(?:issue|problem)\s+(?:in\s+)?(.+)",
                r"why\s+(?:is\s+)?(.+)\s+(?:not\s+working|failing)"
            ],
            keywords=["debug", "find", "issue", "why", "failing"],
            entities=["debug_target", "symptoms", "error_output"],
            response_template="Debugging {debug_target}",
            tool_suggestions=["debugger", "print", "logging"],
            examples=[
                "debug the API endpoint",
                "help me find the issue in the loop",
                "why is the function returning null"
            ]
        ),

        NLPTemplate(
            id="DB_003",
            name="Analyze Error",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"(?:analyze|explain)\s+(?:this\s+)?error:?\s*(.+)",
                r"what\s+does\s+(?:this\s+)?error\s+mean:?\s*(.+)",
                r"(?:i\'m getting|got)\s+(?:an?\s+)?error:?\s*(.+)"
            ],
            keywords=["error", "analyze", "explain", "mean"],
            entities=["error_message", "stack_trace", "context"],
            response_template="Analyzing error: {error_message}",
            tool_suggestions=["ollama", "error_lookup", "documentation"],
            examples=[
                "analyze this error: TypeError: cannot read property",
                "what does this error mean: ECONNREFUSED",
                "I'm getting error 404"
            ]
        ),

        NLPTemplate(
            id="DB_004",
            name="Trace Execution",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"trace\s+(?:the\s+)?(?:execution\s+)?(?:of\s+)?(.+)",
                r"(?:show|display)\s+(?:the\s+)?(?:execution\s+)?(?:flow|path)\s+(?:of\s+)?(.+)"
            ],
            keywords=["trace", "execution", "flow", "path"],
            entities=["trace_target"],
            response_template="Tracing execution of {trace_target}",
            tool_suggestions=["debugger", "print", "logging"],
            examples=["trace the execution of main function", "show execution flow"]
        ),

        NLPTemplate(
            id="DB_005",
            name="Memory Leak Detection",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"(?:find|detect|check)\s+(?:for\s+)?memory\s+leak",
                r"memory\s+(?:usage|consumption)\s+(?:issue|problem)"
            ],
            keywords=["memory", "leak", "usage"],
            entities=["memory_target"],
            response_template="Checking for memory leaks",
            tool_suggestions=["profiler", "valgrind", "memory_profiler"],
            examples=["find memory leak", "check memory usage"]
        ),

        NLPTemplate(
            id="DB_006",
            name="Performance Bottleneck",
            category=IntentCategory.DEBUGGING,
            patterns=[
                r"(?:find|identify|locate)\s+(?:performance\s+)?bottleneck",
                r"(?:what\'s|what is)\s+(?:making|causing)\s+(?:it|this)\s+slow"
            ],
            keywords=["bottleneck", "performance", "slow"],
            entities=["performance_target"],
            response_template="Identifying performance bottlenecks",
            tool_suggestions=["profiler", "workflow:optimize"],
            examples=["find performance bottleneck", "what's making it slow"]
        ),
    ]
