"""
Chat Memory Semantic Search

Cross-session semantic search with caching.
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SearchMixin:
    """Mixin providing semantic search operations"""

    def search_messages_semantic(self, query: str, limit: int = 10, user_id: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search across messages using semantic similarity

        Phase 5: Team-aware - filters by user_id/team_id
        Performance: Uses pre-computed embeddings for 100x faster search + Redis caching
        """
        from api.chat_enhancements import SimpleEmbedding
        from api.cache_service import get_cache

        # Cache key based on query, user, and team context
        cache_key = f"semantic_search:{hashlib.sha256(query.encode()).hexdigest()}:{user_id or 'none'}:{team_id or 'none'}:{limit}"
        cache = get_cache()

        # Check cache first
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.debug(f"Semantic search cache HIT for query: '{query[:50]}...'")
            return cached_results

        query_embedding = SimpleEmbedding.create_embedding(query)
        conn = self._get_connection()

        # Phase 5: Team-scoped search query with pre-computed embeddings
        if team_id:
            # Team sessions - use pre-computed embeddings
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model, s.title, e.embedding_json
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE length(m.content) > 20 AND m.team_id = ?
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (team_id,))
        else:
            # Personal sessions - use pre-computed embeddings
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model, s.title, e.embedding_json
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE length(m.content) > 20 AND m.user_id = ? AND m.team_id IS NULL
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (user_id,))

        results = []
        for row in cur.fetchall():
            # Use pre-computed embedding if available, otherwise compute on-the-fly
            if row["embedding_json"]:
                msg_embedding = json.loads(row["embedding_json"])
            else:
                # Fallback for messages without pre-computed embeddings
                msg_embedding = SimpleEmbedding.create_embedding(row["content"])

            similarity = SimpleEmbedding.cosine_similarity(query_embedding, msg_embedding)

            if similarity > 0.3:  # Threshold
                results.append({
                    "session_id": row["session_id"],
                    "session_title": row["title"],
                    "role": row["role"],
                    "content": row["content"][:200],
                    "timestamp": row["timestamp"],
                    "model": row["model"],
                    "similarity": similarity
                })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        final_results = results[:limit]

        # Cache results for 5 minutes (searches are user-specific)
        cache.set(cache_key, final_results, ttl=300)
        logger.debug(f"Cached semantic search results for query: '{query[:50]}...'")

        return final_results


__all__ = ["SearchMixin"]
