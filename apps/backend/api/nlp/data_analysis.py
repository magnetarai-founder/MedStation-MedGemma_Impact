"""
Data analysis templates (DATA_ANALYSIS category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all DATA_ANALYSIS templates."""
    return [
        NLPTemplate(
            id="DA_001",
            name="Analyze Data",
            category=IntentCategory.DATA_ANALYSIS,
            patterns=[
                r"analyze\s+(?:the\s+)?(?:data\s+)?(?:in\s+)?(.+)",
                r"(?:show|get)\s+(?:me\s+)?statistics\s+(?:for|on|about)\s+(.+)",
                r"(?:what are|what\'s)\s+the\s+(?:metrics|stats|statistics)\s+(?:for\s+)?(.+)"
            ],
            keywords=["analyze", "data", "statistics", "metrics"],
            entities=["data_source", "metrics_requested"],
            response_template="Analyzing data from {data_source}",
            tool_suggestions=["pandas", "workflow:data_analysis"],
            examples=[
                "analyze the user data",
                "show me statistics for the last month",
                "what are the performance metrics"
            ]
        ),

        NLPTemplate(
            id="DA_002",
            name="Generate Report",
            category=IntentCategory.DATA_ANALYSIS,
            patterns=[
                r"(?:generate|create|make)\s+(?:a\s+)?report\s+(?:for|on|about)\s+(.+)",
                r"(?:summarize|summary)\s+(?:the\s+)?(.+)",
                r"(?:create|make)\s+(?:a\s+)?summary\s+of\s+(.+)"
            ],
            keywords=["report", "summary", "summarize", "generate"],
            entities=["report_subject", "format", "time_range"],
            response_template="Generating report on {report_subject}",
            tool_suggestions=["workflow:report_gen", "markdown"],
            examples=[
                "generate a report on user activity",
                "summarize the test results",
                "create a performance report"
            ]
        ),

        NLPTemplate(
            id="DA_003",
            name="Visualize Data",
            category=IntentCategory.DATA_ANALYSIS,
            patterns=[
                r"(?:visualize|plot|graph)\s+(?:the\s+)?(.+)",
                r"(?:create|make|generate)\s+(?:a\s+)?(?:chart|graph|plot)\s+(?:of|for)\s+(.+)"
            ],
            keywords=["visualize", "plot", "graph", "chart"],
            entities=["data_source", "chart_type"],
            response_template="Visualizing {data_source}",
            tool_suggestions=["matplotlib", "plotly", "seaborn"],
            examples=["visualize the sales data", "create a chart of user growth", "plot the results"]
        ),

        NLPTemplate(
            id="DA_004",
            name="Data Transformation",
            category=IntentCategory.DATA_ANALYSIS,
            patterns=[
                r"(?:transform|convert|process)\s+(?:the\s+)?data\s+(?:from\s+)?(.+)",
                r"(?:clean|normalize|aggregate)\s+(?:the\s+)?(.+)\s+data"
            ],
            keywords=["transform", "convert", "clean", "normalize", "aggregate"],
            entities=["data_source", "transformation_type"],
            response_template="Transforming {data_source} data",
            tool_suggestions=["pandas", "workflow:data_pipeline"],
            examples=["transform the CSV data", "clean the dataset", "normalize user data"]
        ),

        NLPTemplate(
            id="DA_005",
            name="Query Database",
            category=IntentCategory.DATA_ANALYSIS,
            patterns=[
                r"(?:query|select|get)\s+(?:from\s+)?(?:the\s+)?database\s+(.+)",
                r"(?:sql|database)\s+(?:query\s+)?(?:for\s+)?(.+)"
            ],
            keywords=["query", "database", "sql", "select"],
            entities=["query_target", "table", "conditions"],
            response_template="Querying database for {query_target}",
            tool_suggestions=["sql", "sqlalchemy", "database"],
            examples=["query database for users", "select from orders table", "get all products"]
        ),
    ]
