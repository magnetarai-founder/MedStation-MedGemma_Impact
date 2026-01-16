"""
Compatibility Shim for Template Orchestrator

The implementation now lives in the `api.llm` package:
- api.llm.orchestrator: TemplateOrchestrator class

This shim maintains backward compatibility.

Note: Requires 'templates' and 'bigquery_engine' modules.
"""

try:
    from api.llm.orchestrator import (
        WorkflowStep,
        TemplateWorkflow,
        TemplateOrchestrator,
        validate_sql_condition,
    )
except ImportError:
    WorkflowStep = None
    TemplateWorkflow = None
    TemplateOrchestrator = None
    validate_sql_condition = None

__all__ = [
    "WorkflowStep",
    "TemplateWorkflow",
    "TemplateOrchestrator",
    "validate_sql_condition",
]
