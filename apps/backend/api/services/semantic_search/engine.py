"""
Semantic Search Service for MagnetarCode

Provides vector-based semantic search across conversation history.

Features:
- Automatic embedding generation for messages
- Efficient vector similarity search
- Hybrid search (semantic + keyword)
- Result re-ranking
- Context-aware retrieval

Uses sentence-transformers for embeddings (already in requirements.txt).
"""
from pathlib import Path

from api.utils.structured_logging import get_logger

from .embeddings import EmbeddingManager
from .models import SearchConfig, SemanticSearchResult
from .search import SearchManager

logger = get_logger(__name__)


class SemanticSearchEngine:
    """
    High-performance semantic search engine using sentence-transformers.

    Performance optimizations:
    - Batch embedding generation
    - Numpy vectorized similarity computation
    - Pre-computed embeddings stored in database
    - Efficient approximate nearest neighbor search for large datasets
    """

    def __init__(self, db_path: Path, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic search engine

        Args:
            db_path: Path to chat memory database
            model_name: Sentence transformer model name
                       Default: all-MiniLM-L6-v2 (fast, 384 dimensions)
                       Alternatives:
                       - all-mpnet-base-v2 (better quality, 768 dimensions)
                       - paraphrase-multilingual-MiniLM-L12-v2 (multilingual)
        """
        self.db_path = db_path
        self.model_name = model_name

        # Initialize managers
        self.embedding_manager = EmbeddingManager(db_path, model_name)
        self.search_manager = SearchManager(db_path)

        logger.info(f"Initialized SemanticSearchEngine with model: {model_name}")

    # Embedding methods
    def _get_model(self):
        """Get or load sentence transformer model (lazy loading)"""
        return self.embedding_manager._get_model()

    def _get_connection(self):
        """Get thread-local database connection"""
        return self.embedding_manager._get_connection()

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text (cached)

        Args:
            text: Input text to embed

        Returns:
            List of floats (embedding vector)
        """
        return await self.embedding_manager.generate_embedding(text)

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts (more efficient)

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        return await self.embedding_manager.generate_embeddings_batch(texts)

    async def store_message_embedding(
        self, message_id: int, session_id: str, content: str, team_id: str | None = None
    ) -> None:
        """
        Generate and store embedding for a message

        Args:
            message_id: Message ID
            session_id: Session ID
            content: Message content
            team_id: Team ID (for team isolation)
        """
        return await self.embedding_manager.store_message_embedding(
            message_id, session_id, content, team_id
        )

    async def backfill_embeddings(
        self,
        user_id: str | None = None,
        team_id: str | None = None,
        batch_size: int = 32,
        limit: int | None = None,
    ) -> dict[str, int]:
        """
        Backfill embeddings for existing messages without embeddings

        Args:
            user_id: Filter by user ID
            team_id: Filter by team ID
            batch_size: Number of messages to process per batch
            limit: Maximum number of messages to process

        Returns:
            Statistics about backfill operation
        """
        return await self.embedding_manager.backfill_embeddings(
            user_id, team_id, batch_size, limit
        )

    # Search methods
    async def search(
        self,
        query: str,
        config: SearchConfig | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Semantic search across conversation history (cached)

        Args:
            query: Search query
            config: Search configuration
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of search results ordered by relevance
        """
        # Generate query embedding
        query_embedding = await self.embedding_manager.generate_embedding(query)

        # Perform search
        return await self.search_manager.search(
            query, query_embedding, config, user_id, team_id
        )

    async def search_similar_messages(
        self,
        session_id: str,
        message_id: int,
        top_k: int = 5,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Find messages similar to a given message

        Args:
            session_id: Session ID
            message_id: Message ID to find similar to
            top_k: Number of similar messages to return
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of similar messages
        """
        return await self.search_manager.search_similar_messages(
            session_id, message_id, top_k, user_id, team_id
        )


# Global instance cache
_semantic_search_instances: dict[str, SemanticSearchEngine] = {}


def get_semantic_search(
    db_path: Path, model_name: str = "all-MiniLM-L6-v2"
) -> SemanticSearchEngine:
    """
    Get or create SemanticSearchEngine instance

    Args:
        db_path: Path to chat memory database
        model_name: Sentence transformer model name

    Returns:
        SemanticSearchEngine instance
    """
    db_key = str(db_path.resolve())

    if db_key not in _semantic_search_instances:
        _semantic_search_instances[db_key] = SemanticSearchEngine(db_path, model_name)

    return _semantic_search_instances[db_key]
