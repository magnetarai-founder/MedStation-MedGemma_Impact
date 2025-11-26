#!/usr/bin/env python3
"""
ElohimOS Memory System
Copyright (c) 2025 MagnetarAI, LLC
Adapter for Jarvis BigQuery Memory to handle SQL/JSON query history
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import time
import hashlib

from jarvis_bigquery_memory import JarvisBigQueryMemory


class ElohimOSMemory:
    """
    ElohimOS-specific memory layer built on Jarvis BigQuery Memory
    Handles SQL and JSON query history with semantic search and patterns
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".elohimos" / "query_history.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = JarvisBigQueryMemory(db_path)
        self._setup_elohimos_tables()

        # In-memory cache for history queries
        self._history_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes TTL
        self._cache_timestamps: Dict[str, float] = {}

    def _setup_elohimos_tables(self):
        """Create ElohimOS-specific tables"""

        # Query history table (replaces localStorage)
        self.memory.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                query_type TEXT NOT NULL CHECK(query_type IN ('sql', 'json')),
                query_hash TEXT,
                execution_time REAL,
                row_count INTEGER,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                file_context TEXT,
                embedding_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for fast lookups
        self.memory.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_type
            ON query_history(query_type)
        """)
        self.memory.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_timestamp
            ON query_history(timestamp DESC)
        """)
        self.memory.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_hash
            ON query_history(query_hash)
        """)

        # Saved queries table (replaces saved queries store)
        self.memory.conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                query_type TEXT NOT NULL,
                folder TEXT,
                description TEXT,
                tags TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # App settings table (persistent settings storage)
        self.memory.conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.memory.conn.commit()

    def add_query_history(
        self,
        query: str,
        query_type: str,
        execution_time: Optional[float] = None,
        row_count: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        file_context: Optional[str] = None
    ) -> int:
        """Add a query to history with embedding for semantic search"""

        query_hash = hashlib.md5(query.encode()).hexdigest()

        # Generate embedding for semantic search
        embedding = self.memory._generate_embedding(query)

        with self.memory._write_lock:
            cursor = self.memory.conn.execute("""
                INSERT INTO query_history
                (query, query_type, query_hash, execution_time, row_count,
                 success, error_message, file_context, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query,
                query_type,
                query_hash,
                execution_time,
                row_count,
                success,
                error_message,
                file_context,
                json.dumps(embedding)
            ))

            self.memory.conn.commit()

            # Invalidate cache when new data is added
            self._invalidate_history_cache()

            return cursor.lastrowid

    def _invalidate_history_cache(self):
        """Clear the in-memory cache to force fresh data on next request"""
        self._history_cache.clear()
        self._cache_timestamps.clear()

    def get_history(
        self,
        query_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        date_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get query history with pagination and filters (with in-memory cache)"""

        # Generate cache key
        cache_key = f"{query_type}_{limit}_{offset}_{date_filter}"

        # Check if cache is valid
        current_time = time.time()
        if cache_key in self._history_cache:
            cache_age = current_time - self._cache_timestamps.get(cache_key, 0)
            if cache_age < self._cache_ttl:
                # Cache hit! Return from RAM
                return self._history_cache[cache_key]

        # Cache miss - query SQLite
        where_clauses = []
        params = []

        if query_type:
            where_clauses.append("query_type = ?")
            params.append(query_type)

        if date_filter == 'today':
            where_clauses.append("timestamp >= date('now')")
        elif date_filter == 'week':
            where_clauses.append("timestamp >= date('now', '-7 days')")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT
                id,
                query,
                query_type,
                execution_time,
                row_count,
                success,
                error_message,
                timestamp
            FROM query_history
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        cursor = self.memory.conn.execute(query, params)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]

        # Store in cache
        self._history_cache[cache_key] = result
        self._cache_timestamps[cache_key] = current_time

        return result

    def search_similar_queries(
        self,
        query_text: str,
        query_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar queries using semantic search with cosine similarity"""

        # Generate embedding for search query
        search_embedding = self.memory._generate_embedding(query_text)

        if not search_embedding:
            logger.warning("Failed to generate embedding for similarity search, falling back to text search")
            # Fallback to simple text search
            where_clause = "query_type = ?" if query_type else "1=1"
            params = [query_type] if query_type else []
            params.append(f"%{query_text}%")
            params.append(limit)

            cursor = self.memory.conn.execute(f"""
                SELECT
                    id,
                    query,
                    query_type,
                    execution_time,
                    row_count,
                    timestamp
                FROM query_history
                WHERE {where_clause}
                  AND query LIKE ?
                  AND success = 1
                ORDER BY timestamp DESC
                LIMIT ?
            """, params)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        # Fetch candidate queries with embeddings
        where_clause = "query_type = ? AND embedding IS NOT NULL" if query_type else "embedding IS NOT NULL"
        params = [query_type] if query_type else []

        try:
            cursor = self.memory.conn.execute(f"""
                SELECT
                    id,
                    query,
                    query_type,
                    embedding,
                    execution_time,
                    row_count,
                    timestamp
                FROM query_history
                WHERE {where_clause}
                  AND success = 1
                ORDER BY timestamp DESC
                LIMIT 100
            """, params)

            candidates = cursor.fetchall()

            if not candidates:
                return []

            # Compute cosine similarity for each candidate
            import numpy as np
            import json

            search_vec = np.array(search_embedding)
            search_norm = np.linalg.norm(search_vec)

            if search_norm == 0:
                logger.warning("Search embedding has zero norm")
                return []

            similarities = []
            for row in candidates:
                try:
                    # Deserialize embedding (stored as JSON string)
                    candidate_embedding = json.loads(row['embedding']) if isinstance(row['embedding'], str) else row['embedding']
                    candidate_vec = np.array(candidate_embedding)
                    candidate_norm = np.linalg.norm(candidate_vec)

                    if candidate_norm == 0:
                        continue

                    # Cosine similarity: dot(A, B) / (||A|| * ||B||)
                    similarity = np.dot(search_vec, candidate_vec) / (search_norm * candidate_norm)

                    similarities.append({
                        "id": row['id'],
                        "query": row['query'],
                        "query_type": row['query_type'],
                        "execution_time": row['execution_time'],
                        "row_count": row['row_count'],
                        "timestamp": row['timestamp'],
                        "similarity_score": float(similarity)
                    })
                except Exception as e:
                    logger.error(f"Failed to compute similarity for candidate {row.get('id')}: {e}")
                    continue

            # Sort by similarity score (highest first) and return top matches
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

            return similarities[:limit]

        except Exception as e:
            logger.error(f"Error in cosine similarity search: {e}")
            # Fallback to simple text search
            return []

    def get_history_count(
        self,
        query_type: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> int:
        """Get total count of history items"""

        where_clauses = []
        params = []

        if query_type:
            where_clauses.append("query_type = ?")
            params.append(query_type)

        if date_filter == 'today':
            where_clauses.append("timestamp >= date('now')")
        elif date_filter == 'week':
            where_clauses.append("timestamp >= date('now', '-7 days')")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        cursor = self.memory.conn.execute(f"""
            SELECT COUNT(*) as count
            FROM query_history
            WHERE {where_sql}
        """, params)

        return cursor.fetchone()['count']

    def delete_history_item(self, history_id: int) -> bool:
        """Delete a specific history item"""

        with self.memory._write_lock:
            self.memory.conn.execute("""
                DELETE FROM query_history WHERE id = ?
            """, (history_id,))
            self.memory.conn.commit()

            # Invalidate cache
            self._invalidate_history_cache()

            return True

    def clear_history(
        self,
        query_type: Optional[str] = None,
        before_date: Optional[str] = None
    ) -> int:
        """Clear history with optional filters"""

        where_clauses = []
        params = []

        if query_type:
            where_clauses.append("query_type = ?")
            params.append(query_type)

        if before_date:
            where_clauses.append("timestamp < ?")
            params.append(before_date)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        with self.memory._write_lock:
            cursor = self.memory.conn.execute(f"""
                DELETE FROM query_history WHERE {where_sql}
            """, params)
            self.memory.conn.commit()

            # Invalidate cache
            self._invalidate_history_cache()

            return cursor.rowcount

    def save_query(
        self,
        name: str,
        query: str,
        query_type: str,
        folder: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Save a query for later use"""

        with self.memory._write_lock:
            cursor = self.memory.conn.execute("""
                INSERT INTO saved_queries
                (name, query, query_type, folder, description, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                query,
                query_type,
                folder,
                description,
                json.dumps(tags or [])
            ))
            self.memory.conn.commit()
            return cursor.lastrowid

    def get_saved_queries(
        self,
        folder: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all saved queries"""

        where_clauses = []
        params = []

        if folder:
            where_clauses.append("folder = ?")
            params.append(folder)

        if query_type:
            where_clauses.append("query_type = ?")
            params.append(query_type)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        cursor = self.memory.conn.execute(f"""
            SELECT *
            FROM saved_queries
            WHERE {where_sql}
            ORDER BY folder, name
        """, params)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def update_saved_query(
        self,
        query_id: int,
        name: str,
        query: str,
        query_type: str,
        folder: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing saved query"""

        with self.memory._write_lock:
            self.memory.conn.execute("""
                UPDATE saved_queries
                SET name = ?,
                    query = ?,
                    query_type = ?,
                    folder = ?,
                    description = ?,
                    tags = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                name,
                query,
                query_type,
                folder,
                description,
                json.dumps(tags or []),
                query_id
            ))
            self.memory.conn.commit()
            return True

    def delete_saved_query(self, query_id: int) -> bool:
        """Delete a saved query"""

        with self.memory._write_lock:
            self.memory.conn.execute("""
                DELETE FROM saved_queries WHERE id = ?
            """, (query_id,))
            self.memory.conn.commit()
            return True

    # ============================================================================
    # Settings Management
    # ============================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        cursor = self.memory.conn.execute("""
            SELECT value FROM app_settings WHERE key = ?
        """, (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row['value'])
        return default

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value"""
        with self.memory._write_lock:
            self.memory.conn.execute("""
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json.dumps(value)))
            self.memory.conn.commit()

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        cursor = self.memory.conn.execute("""
            SELECT key, value FROM app_settings
        """)
        return {row['key']: json.loads(row['value']) for row in cursor.fetchall()}

    def set_all_settings(self, settings: Dict[str, Any]) -> None:
        """Bulk update settings"""
        with self.memory._write_lock:
            for key, value in settings.items():
                self.memory.conn.execute("""
                    INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value)))
            self.memory.conn.commit()

    def close(self):
        """Close the database connection"""
        self.memory.conn.close()
