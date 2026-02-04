"""
Embedding generation and storage for semantic search
"""
import asyncio
import hashlib
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import numpy as np

from api.config.constants import CACHE_TTL_LONG
from api.services.cache_service import get_cache
from api.utils.structured_logging import get_logger

logger = get_logger(__name__)
cache = get_cache()


class EmbeddingManager:
    """Manages embedding model loading, generation, and storage"""

    def __init__(self, db_path: Path, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding manager

        Args:
            db_path: Path to chat memory database
            model_name: Sentence transformer model name
        """
        self.db_path = db_path
        self.model_name = model_name
        self._model = None
        self._local = threading.local()

    def _get_model(self):
        """Get or load sentence transformer model (lazy loading)"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading sentence-transformers model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info(
                    f"Model loaded successfully, embedding dimension: {self._model.get_sentence_embedding_dimension()}"
                )
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. Install with: pip install sentence-transformers"
                )
        return self._model

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=True, timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            logger.debug(f"Created new DB connection for thread {threading.current_thread().name}")
        return self._local.conn

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text (cached)

        Args:
            text: Input text to embed

        Returns:
            List of floats (embedding vector)
        """
        # Create cache key from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"embedding:{self.model_name}:{text_hash}"

        # Try cache first
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for embedding: {text_hash[:8]}...")
            return cached

        # Generate embedding
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self._generate_embedding_sync, text)
        embedding_list = embedding.tolist()

        # Cache for 24 hours (embeddings don't change)
        await cache.set(cache_key, embedding_list, ttl=CACHE_TTL_LONG)

        return embedding_list

    def _generate_embedding_sync(self, text: str) -> np.ndarray:
        """Synchronous embedding generation"""
        model = self._get_model()
        return model.encode(text, convert_to_numpy=True)

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts (more efficient)

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._generate_embeddings_batch_sync, texts)
        return embeddings.tolist()

    def _generate_embeddings_batch_sync(self, texts: list[str]) -> np.ndarray:
        """Synchronous batch embedding generation"""
        model = self._get_model()
        return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

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
        # Skip if content too short
        if len(content.strip()) < 10:
            logger.debug(f"Skipping embedding for short message {message_id}")
            return

        # Generate embedding
        embedding = await self.generate_embedding(content)
        embedding_json = json.dumps(embedding)

        # Store in database
        conn = self._get_connection()
        now = datetime.utcnow().isoformat()

        conn.execute(
            """
            INSERT INTO message_embeddings (message_id, session_id, embedding_json, created_at, team_id)
            VALUES (?, ?, ?, ?, ?)
        """,
            (message_id, session_id, embedding_json, now, team_id),
        )
        conn.commit()

        logger.debug(f"Stored embedding for message {message_id}")

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
        conn = self._get_connection()

        # Find messages without embeddings
        if team_id:
            query = """
                SELECT m.id, m.session_id, m.content, m.team_id
                FROM chat_messages m
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE e.id IS NULL AND m.team_id = ? AND length(m.content) >= 10
                ORDER BY m.timestamp DESC
            """
            params = (team_id,)
        elif user_id:
            query = """
                SELECT m.id, m.session_id, m.content, m.team_id
                FROM chat_messages m
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE e.id IS NULL AND m.user_id = ? AND m.team_id IS NULL AND length(m.content) >= 10
                ORDER BY m.timestamp DESC
            """
            params = (user_id,)
        else:
            query = """
                SELECT m.id, m.session_id, m.content, m.team_id
                FROM chat_messages m
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE e.id IS NULL AND length(m.content) >= 10
                ORDER BY m.timestamp DESC
            """
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        cur = conn.execute(query, params)
        messages = cur.fetchall()

        total_messages = len(messages)
        if total_messages == 0:
            logger.info("No messages need embedding backfill")
            return {"total": 0, "processed": 0, "skipped": 0}

        logger.info(f"Backfilling embeddings for {total_messages} messages")

        processed = 0
        skipped = 0

        # Process in batches for efficiency
        for i in range(0, total_messages, batch_size):
            batch = messages[i : i + batch_size]

            # Extract texts and metadata
            texts = [msg["content"] for msg in batch]
            message_ids = [msg["id"] for msg in batch]
            session_ids = [msg["session_id"] for msg in batch]
            # sqlite3.Row doesn't have .get(), use conditional with 'in' check
            team_ids = [msg["team_id"] if "team_id" in msg else None for msg in batch]

            try:
                # Generate embeddings in batch
                embeddings = await self.generate_embeddings_batch(texts)

                # Store embeddings
                now = datetime.utcnow().isoformat()

                for msg_id, sess_id, embedding, t_id in zip(
                    message_ids, session_ids, embeddings, team_ids, strict=False
                ):
                    embedding_json = json.dumps(embedding)
                    conn.execute(
                        """
                        INSERT INTO message_embeddings (message_id, session_id, embedding_json, created_at, team_id)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (msg_id, sess_id, embedding_json, now, t_id),
                    )

                # Don't commit inside the loop - batch all inserts
                processed += len(batch)

                logger.info(f"Backfill progress: {processed}/{total_messages}")

            except Exception as e:
                logger.error(f"Error backfilling batch: {e}")
                skipped += len(batch)

        # Single commit after all batches (80-90% faster!)
        conn.commit()
        logger.info(f"Backfill complete: {processed} processed, {skipped} skipped")
        return {"total": total_messages, "processed": processed, "skipped": skipped}
