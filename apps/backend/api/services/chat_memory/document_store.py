"""
Document Store for Chat Memory

Handles RAG document operations:
- Store document chunks with embeddings
- Check for document existence
- Search document chunks semantically
"""
import json
import logging
from datetime import datetime
from typing import Any

from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DocumentStore:
    """
    Manages document chunks for RAG (Retrieval Augmented Generation).

    Documents are chunked and stored with embeddings for
    semantic search during conversations.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize document store.

        Args:
            db_manager: Shared database manager instance
        """
        self._db = db_manager

    def store_chunks(self, session_id: str, chunks: list[dict[str, Any]]):
        """
        Store document chunks for RAG.

        Args:
            session_id: Session to associate chunks with
            chunks: List of chunk dicts with keys:
                - file_id: Unique file identifier
                - filename: Original filename
                - chunk_index: Index of this chunk
                - total_chunks: Total chunks for this file
                - content: Chunk text content
                - embedding: Optional embedding vector
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            for chunk in chunks:
                embedding_json = json.dumps(chunk.get("embedding", []))

                conn.execute(
                    """
                    INSERT INTO document_chunks
                    (session_id, file_id, filename, chunk_index, total_chunks,
                     content, embedding_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        chunk.get("file_id"),
                        chunk.get("filename"),
                        chunk.get("chunk_index"),
                        chunk.get("total_chunks"),
                        chunk.get("content"),
                        embedding_json,
                        now,
                    ),
                )

            conn.commit()

    def has_documents(self, session_id: str) -> bool:
        """
        Check if a session has any uploaded documents.

        Args:
            session_id: Session to check

        Returns:
            True if session has documents
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT COUNT(*) as count
            FROM document_chunks
            WHERE session_id = ?
            LIMIT 1
        """,
            (session_id,),
        )

        row = cur.fetchone()
        return row["count"] > 0 if row else False

    def search_chunks(
        self,
        session_id: str,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant document chunks using semantic similarity.

        Args:
            session_id: Session to search within
            query_embedding: Query embedding vector
            top_k: Number of top results to return

        Returns:
            List of matching chunks with similarity scores
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT id, file_id, filename, chunk_index, content, embedding_json
            FROM document_chunks
            WHERE session_id = ?
        """,
            (session_id,),
        )

        chunks = []
        for row in cur.fetchall():
            chunk_embedding = json.loads(row["embedding_json"])

            # Calculate similarity
            from api.chat_enhancements import SimpleEmbedding

            similarity = SimpleEmbedding.cosine_similarity(query_embedding, chunk_embedding)

            chunks.append(
                {
                    "id": row["id"],
                    "file_id": row["file_id"],
                    "filename": row["filename"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "similarity": similarity,
                }
            )

        # Sort by similarity and return top_k
        chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return chunks[:top_k]
