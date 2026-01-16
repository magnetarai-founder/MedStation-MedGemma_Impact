"""
Jarvis AI Memory and RAG Pipeline module.

Provides:
- JarvisMemory: Core memory system for AI context
- JarvisBigQueryMemory: BigQuery-backed memory storage
- AdaptiveRouter: Intelligent query routing (requires enhanced_router)
- RAG Pipeline: Retrieval-augmented generation utilities
- Memory models and templates
"""

from api.jarvis.memory import JarvisMemory
from api.jarvis.bigquery_memory import JarvisBigQueryMemory
from api.jarvis.memory_models import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    get_default_templates,
)
from api.jarvis.memory_db import (
    get_default_db_path,
    create_connection,
    setup_schema,
    generate_embedding,
)

# Optional imports (may require additional dependencies)
try:
    from api.jarvis.adaptive_router import AdaptiveRouter, AdaptiveRouteResult
except ImportError:
    AdaptiveRouter = None
    AdaptiveRouteResult = None

try:
    from api.jarvis.rag_pipeline import (
        retrieve_context_for_command,
        ingest_paths,
    )
except ImportError:
    retrieve_context_for_command = None
    ingest_paths = None

__all__ = [
    # Core classes
    "JarvisMemory",
    "JarvisBigQueryMemory",
    # Models
    "MemoryType",
    "MemoryTemplate",
    "SemanticMemory",
    "get_default_templates",
    # Database utilities
    "get_default_db_path",
    "create_connection",
    "setup_schema",
    "generate_embedding",
]

# Add optional exports if available
if AdaptiveRouter is not None:
    __all__.extend(["AdaptiveRouter", "AdaptiveRouteResult"])
if retrieve_context_for_command is not None:
    __all__.extend(["retrieve_context_for_command", "ingest_paths"])
