#!/usr/bin/env python3
"""
OmniStudio Memory System
Adapter for Jarvis BigQuery Memory to handle SQL/JSON query history
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from jarvis_bigquery_memory import JarvisBigQueryMemory


class OmniStudioMemory:
    """
    OmniStudio-specific memory layer built on Jarvis BigQuery Memory
    Handles SQL and JSON query history with semantic search and patterns
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".omnistudio" / "query_history.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = JarvisBigQueryMemory(db_path)
        self._setup_omnistudio_tables()

    def _setup_omnistudio_tables(self):
        """Create OmniStudio-specific tables"""

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

        import hashlib
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
            return cursor.lastrowid

    def get_history(
        self,
        query_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        date_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get query history with pagination and filters"""

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

        return [dict(row) for row in rows]

    def search_similar_queries(
        self,
        query_text: str,
        query_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar queries using semantic search"""

        # Generate embedding for search query
        search_embedding = self.memory._generate_embedding(query_text)

        # For now, use simple text similarity
        # TODO: Implement proper cosine similarity with embeddings
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

    def close(self):
        """Close the database connection"""
        self.memory.conn.close()
