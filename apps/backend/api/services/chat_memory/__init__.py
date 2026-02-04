"""
MagnetarCode Chat Memory System

This module provides a modular, single-responsibility architecture:
- MagnetarChatMemory: Facade class (backward compatible API)
- DatabaseManager: Connection and schema management
- SessionStore: Session CRUD operations
- MessageStore: Message storage and retrieval
- SummaryManager: Conversation summaries
- PreferenceStore: Model preferences
- DocumentStore: RAG document operations
- AnalyticsEngine: Analytics queries

ALL imports remain backward compatible.
"""

# Re-export all public APIs for backward compatibility
from .analytics_engine import AnalyticsEngine

# New component exports (for advanced usage)
from .db_manager import DatabaseManager
from .decorators import log_query_performance
from .document_store import DocumentStore
from .memory import MagnetarChatMemory
from .message_store import MessageStore
from .models import ConversationEvent
from .preference_store import PreferenceStore
from .session_store import SessionStore
from .summary_manager import SummaryManager

# Singleton getter (backward compatibility)
_memory_instance = None


def get_memory():
    """Get singleton memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MagnetarChatMemory()
    return _memory_instance


# Explicit exports for type checkers
__all__ = [
    # Primary API (backward compatible)
    "ConversationEvent",
    "MagnetarChatMemory",
    "log_query_performance",
    "get_memory",
    # Component classes (for advanced usage)
    "DatabaseManager",
    "SessionStore",
    "MessageStore",
    "SummaryManager",
    "PreferenceStore",
    "DocumentStore",
    "AnalyticsEngine",
]
