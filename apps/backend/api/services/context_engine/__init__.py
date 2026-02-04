"""
Context Engine for MagnetarCode

Provides intelligent context retrieval using:
- Vector embeddings (semantic search)
- Full-text search (keyword matching)
- Hybrid ranking (best of both)

This is the core differentiator that makes MagnetarCode smarter than Claude Code.
"""

from typing import Optional

from .engine import ContextEngine
from .indexer import FullTextIndexer, VectorIndexer
from .retriever import ContextRetriever
from .sources import TerminalSource, WorkspaceSource

# Global instance
_context_engine: ContextEngine | None = None


def get_context_engine() -> ContextEngine:
    """Get or create global context engine instance"""
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine()
    return _context_engine


__all__ = [
    "ContextEngine",
    "ContextRetriever",
    "FullTextIndexer",
    "TerminalSource",
    "VectorIndexer",
    "WorkspaceSource",
    "get_context_engine",
]
