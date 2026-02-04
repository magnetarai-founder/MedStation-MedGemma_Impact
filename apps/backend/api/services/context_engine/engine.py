"""
Context Engine

Main orchestrator for intelligent context retrieval.
Coordinates indexing and retrieval across all sources.
"""

from pathlib import Path
from typing import Any

from api.utils.structured_logging import get_logger

from .indexer import FullTextIndexer, VectorIndexer
from .retriever import ContextRetriever
from .sources import TerminalSource, WorkspaceSource

logger = get_logger(__name__)


class ContextEngine:
    """
    Main context engine for MagnetarCode.

    Provides intelligent context retrieval using:
    - Vector embeddings for semantic search
    - Full-text search for keyword matching
    - Hybrid ranking for best results
    """

    def __init__(self, db_path: str = "context.db"):
        """
        Initialize context engine.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.vector_indexer = VectorIndexer(db_path=db_path)
        self.fts_indexer = FullTextIndexer(db_path=db_path)
        self.retriever = ContextRetriever(db_path=db_path)

        self.workspace_source = None
        self.terminal_source = TerminalSource()

    async def index_workspace(
        self, workspace_path: str, show_progress: bool = False
    ) -> dict[str, Any]:
        """
        Index all files in a workspace.

        Args:
            workspace_path: Path to workspace root
            show_progress: Show indexing progress

        Returns:
            Indexing statistics
        """
        workspace_path = Path(workspace_path).resolve()

        if not workspace_path.exists() or not workspace_path.is_dir():
            raise ValueError(f"Invalid workspace path: {workspace_path}")

        # Create workspace source
        source = WorkspaceSource(str(workspace_path))

        # Collect files to index
        items_vector = []
        items_fts = []

        for source_id, content, metadata in source.iter_files():
            items_vector.append((source_id, content, metadata))
            items_fts.append((source_id, content, metadata))

        if show_progress:
            logger.info(f"Indexing {len(items_vector)} files from {workspace_path}")

        # Index in batches (vector indexing is slow)
        batch_size = 32

        vector_ids = []
        for i in range(0, len(items_vector), batch_size):
            batch = items_vector[i : i + batch_size]
            ids = self.vector_indexer.index_batch(batch)
            vector_ids.extend(ids)

            if show_progress:
                logger.info(f"  Vector indexed: {len(vector_ids)}/{len(items_vector)}")

        # Index FTS (fast, no batching needed)
        fts_ids = []
        for source_id, content, metadata in items_fts:
            doc_id = self.fts_indexer.index(source_id, content, metadata)
            fts_ids.append(doc_id)

        if show_progress:
            logger.info(f"  FTS indexed: {len(fts_ids)} files")

        return {
            "workspace_path": str(workspace_path),
            "files_indexed": len(vector_ids),
            "vector_ids": len(vector_ids),
            "fts_ids": len(fts_ids),
        }

    async def index_terminal(self, session_id: str = "main", lines: int = 100) -> str | None:
        """
        Index terminal output.

        Args:
            session_id: Terminal session ID
            lines: Number of lines to index

        Returns:
            Document ID or None
        """
        result = self.terminal_source.get_context(session_id, lines)

        if not result:
            return None

        source_id, content, metadata = result

        # Index in both
        self.vector_indexer.index(source_id, content, metadata)
        self.fts_indexer.index(source_id, content, metadata)

        return source_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        use_hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant context.

        Args:
            query: Search query
            top_k: Number of results
            source_filter: Optional source filter (e.g., "file:", "terminal:")
            use_hybrid: Use both semantic and keyword search

        Returns:
            List of relevant context items
        """
        return self.retriever.search(
            query=query, top_k=top_k, source_filter=source_filter, use_hybrid=use_hybrid
        )

    def get_context_for_query(
        self,
        query: str,
        max_results: int = 5,
        max_tokens: int = 4000,
        include_files: bool = True,
        include_terminal: bool = True,
    ) -> str:
        """
        Get formatted context for a query.

        Args:
            query: User query
            max_results: Maximum search results
            max_tokens: Token limit for context
            include_files: Include file context
            include_terminal: Include terminal context

        Returns:
            Formatted context string ready for LLM
        """
        # Build source filter
        source_filters = []
        if include_files:
            source_filters.append("file:")
        if include_terminal:
            source_filters.append("terminal:")

        # Search for each source type separately
        all_results = []

        for source_filter in source_filters:
            results = self.search(
                query=query, top_k=max_results, source_filter=source_filter, use_hybrid=True
            )
            all_results.extend(results)

        # Re-sort combined results by score
        all_results.sort(key=lambda x: x["score"], reverse=True)

        # Format context
        context = self.retriever.format_context(
            all_results[:max_results], max_tokens=max_tokens, include_metadata=True
        )

        return context

    def clear_workspace(self, workspace_path: str | None = None):
        """
        Clear workspace index.

        Args:
            workspace_path: Optional path to clear (all if None)
        """
        source_filter = f"file:{workspace_path}" if workspace_path else "file:"
        self.vector_indexer.clear(source_filter)
        self.fts_indexer.clear(source_filter)

    def clear_terminal(self, session_id: str | None = None):
        """
        Clear terminal index.

        Args:
            session_id: Optional session ID (all if None)
        """
        source_filter = f"terminal:{session_id}" if session_id else "terminal:"
        self.vector_indexer.clear(source_filter)
        self.fts_indexer.clear(source_filter)

    def get_stats(self) -> dict[str, Any]:
        """Get indexing statistics"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count embeddings
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        vector_count = cursor.fetchone()[0]

        # Count by source type
        cursor.execute(
            """
            SELECT
                CASE
                    WHEN source LIKE 'file:%' THEN 'file'
                    WHEN source LIKE 'terminal:%' THEN 'terminal'
                    ELSE 'other'
                END as source_type,
                COUNT(*) as count
            FROM embeddings
            GROUP BY source_type
        """
        )
        by_source = dict(cursor.fetchall())

        conn.close()

        return {"total_documents": vector_count, "by_source": by_source, "db_path": self.db_path}


# Global context engine instance
_context_engine: ContextEngine | None = None


def get_context_engine(db_path: str = "context.db") -> ContextEngine:
    """Get or create global context engine instance"""
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine(db_path=db_path)
    return _context_engine
