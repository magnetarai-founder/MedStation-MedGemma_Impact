"""
Chat Memory Module

Extracted and adapted from Jarvis Agent's ConversationMemory and JarvisBigQueryMemory.

Provides:
1. Conversation summaries with rolling window
2. SQLite storage with WAL mode for concurrency
3. Model/engine tracking across switches
4. Semantic context preservation

This module has been refactored from chat_memory.py (993 lines) into:
- models.py: ConversationEvent dataclass
- schema.py: Database schema and migrations
- base.py: Connection management base class
- sessions.py: Session CRUD operations
- messages.py: Message operations
- summaries.py: Rolling conversation summaries
- documents.py: Document chunking and RAG
- search.py: Semantic search with caching
- analytics.py: Usage analytics
- memory.py: Main NeutronChatMemory class
"""

from .models import ConversationEvent
from .memory import NeutronChatMemory, get_memory

# Export MEMORY_DIR
from api.config_paths import get_memory_dir

MEMORY_DIR = get_memory_dir()

__all__ = [
    "ConversationEvent",
    "NeutronChatMemory",
    "get_memory",
    "MEMORY_DIR",
]
