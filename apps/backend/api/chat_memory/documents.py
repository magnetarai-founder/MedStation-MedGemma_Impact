"""
Chat Memory Document Operations

Document chunking and RAG storage.
"""

import json
import logging
from datetime import datetime, UTC
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DocumentMixin:
    """Mixin providing document/RAG operations"""

    def store_document_chunks(self, session_id: str, chunks: List[Dict[str, Any]]) -> None:
        """Store document chunks for RAG"""
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()

        with self._write_lock:
            for chunk in chunks:
                embedding_json = json.dumps(chunk.get("embedding", []))

                conn.execute("""
                    INSERT INTO document_chunks
                    (session_id, file_id, filename, chunk_index, total_chunks, content, embedding_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    chunk.get("file_id"),
                    chunk.get("filename"),
                    chunk.get("chunk_index"),
                    chunk.get("total_chunks"),
                    chunk.get("content"),
                    embedding_json,
                    now
                ))

            conn.commit()

    def has_documents(self, session_id: str) -> bool:
        """Check if a session has any uploaded documents"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT COUNT(*) as count
            FROM document_chunks
            WHERE session_id = ?
            LIMIT 1
        """, (session_id,))

        row = cur.fetchone()
        return row["count"] > 0 if row else False

    def search_document_chunks(self, session_id: str, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant document chunks using semantic similarity"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT id, file_id, filename, chunk_index, content, embedding_json
            FROM document_chunks
            WHERE session_id = ?
        """, (session_id,))

        chunks = []
        for row in cur.fetchall():
            chunk_embedding = json.loads(row["embedding_json"])

            # Calculate similarity
            try:
                from api.chat_enhancements import SimpleEmbedding
            except ImportError:
                from chat_enhancements import SimpleEmbedding
            similarity = SimpleEmbedding.cosine_similarity(query_embedding, chunk_embedding)

            chunks.append({
                "id": row["id"],
                "file_id": row["file_id"],
                "filename": row["filename"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "similarity": similarity
            })

        # Sort by similarity and return top_k
        chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return chunks[:top_k]


__all__ = ["DocumentMixin"]
