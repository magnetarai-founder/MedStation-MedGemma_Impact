"""
LLM Package

Language model utilities for MedStation:
- Ollama configuration and tuning for Apple Silicon
- Token counting with tiktoken
- Template orchestration for multi-step workflows
"""

from api.llm.ollama import (
    OllamaConfig,
    OllamaConfigManager,
    get_ollama_config,
)

from api.llm.tokens import (
    TokenCounter,
    get_token_counter,
    DEFAULT_ENCODING,
)

# Template orchestrator has external dependencies (templates, bigquery_engine)
# Use lazy import to avoid failures when dependencies missing
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
    # Ollama
    "OllamaConfig",
    "OllamaConfigManager",
    "get_ollama_config",
    # Tokens
    "TokenCounter",
    "get_token_counter",
    "DEFAULT_ENCODING",
    # Template Orchestrator (optional)
    "WorkflowStep",
    "TemplateWorkflow",
    "TemplateOrchestrator",
    "validate_sql_condition",
]
