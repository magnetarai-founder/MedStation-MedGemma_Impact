"""
Knowledge Store

Persistent storage for extracted knowledge.
Uses SQLite with FTS for fast retrieval.
"""

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .extractor import (
    CodePattern,
    ExtractionResult,
    PatternType,
    ProblemSolution,
    Topic,
    TopicCategory,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEntry:
    """A stored knowledge entry."""

    id: str
    entry_type: str  # "topic", "pattern", "solution"
    user_id: str
    workspace_root: str | None
    data: dict[str, Any]
    created_at: str
    updated_at: str
    access_count: int = 0
    usefulness_score: float = 0.0


@dataclass
class KnowledgeQuery:
    """Query parameters for knowledge retrieval."""

    query: str = ""
    entry_type: str | None = None  # Filter by type
    user_id: str | None = None
    workspace_root: str | None = None
    limit: int = 20
    min_score: float = 0.0
    include_related: bool = True


class KnowledgeStore:
    """
    Persistent knowledge storage.

    Features:
    - Full-text search for fast retrieval
    - Workspace-scoped and global knowledge
    - Access tracking for relevance ranking
    - Usefulness scoring from feedback
    """

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()

        with self._write_lock:
            conn.executescript("""
                -- Main knowledge entries table
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    workspace_root TEXT,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    usefulness_score REAL DEFAULT 0.0
                );

                -- Index for common queries
                CREATE INDEX IF NOT EXISTS idx_knowledge_user
                    ON knowledge_entries(user_id);
                CREATE INDEX IF NOT EXISTS idx_knowledge_type
                    ON knowledge_entries(entry_type);
                CREATE INDEX IF NOT EXISTS idx_knowledge_workspace
                    ON knowledge_entries(workspace_root);
                CREATE INDEX IF NOT EXISTS idx_knowledge_score
                    ON knowledge_entries(usefulness_score DESC);

                -- Full-text search table
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    id,
                    entry_type,
                    content,
                    content=knowledge_entries,
                    content_rowid=rowid
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_entries BEGIN
                    INSERT INTO knowledge_fts(id, entry_type, content)
                    VALUES (new.id, new.entry_type, new.data_json);
                END;

                CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_entries BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, id, entry_type, content)
                    VALUES ('delete', old.id, old.entry_type, old.data_json);
                END;

                CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_entries BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, id, entry_type, content)
                    VALUES ('delete', old.id, old.entry_type, old.data_json);
                    INSERT INTO knowledge_fts(id, entry_type, content)
                    VALUES (new.id, new.entry_type, new.data_json);
                END;

                -- Related knowledge (for suggestions)
                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    UNIQUE(source_id, target_id, relation_type)
                );

                CREATE INDEX IF NOT EXISTS idx_relations_source
                    ON knowledge_relations(source_id);
            """)
            conn.commit()

    def store_extraction(
        self,
        result: ExtractionResult,
        user_id: str,
        workspace_root: str | None = None,
    ) -> list[str]:
        """
        Store extracted knowledge.

        Args:
            result: Extraction result to store
            user_id: User ID
            workspace_root: Optional workspace scope

        Returns:
            List of stored entry IDs
        """
        stored_ids = []
        now = datetime.utcnow().isoformat()

        conn = self._get_conn()

        with self._write_lock:
            # Store topics
            for topic in result.topics:
                entry_id = f"topic_{topic.name.lower().replace(' ', '_')}_{user_id[:8]}"

                # Upsert - update frequency if exists
                conn.execute("""
                    INSERT INTO knowledge_entries
                    (id, entry_type, user_id, workspace_root, data_json, created_at, updated_at)
                    VALUES (?, 'topic', ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        data_json = ?,
                        updated_at = ?,
                        access_count = access_count + 1
                """, (
                    entry_id, user_id, workspace_root,
                    json.dumps(topic.to_dict()), now, now,
                    json.dumps(topic.to_dict()), now,
                ))
                stored_ids.append(entry_id)

            # Store patterns
            for pattern in result.patterns:
                entry_id = f"pattern_{pattern.pattern_id}"

                conn.execute("""
                    INSERT INTO knowledge_entries
                    (id, entry_type, user_id, workspace_root, data_json, created_at, updated_at)
                    VALUES (?, 'pattern', ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        data_json = ?,
                        updated_at = ?,
                        access_count = access_count + 1
                """, (
                    entry_id, user_id, workspace_root,
                    json.dumps(pattern.to_dict()), now, now,
                    json.dumps(pattern.to_dict()), now,
                ))
                stored_ids.append(entry_id)

            # Store solutions
            for solution in result.solutions:
                entry_id = f"solution_{solution.pair_id}"

                conn.execute("""
                    INSERT INTO knowledge_entries
                    (id, entry_type, user_id, workspace_root, data_json, created_at, updated_at)
                    VALUES (?, 'solution', ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        updated_at = ?,
                        access_count = access_count + 1
                """, (
                    entry_id, user_id, workspace_root,
                    json.dumps(solution.to_dict()), now, now,
                    now,
                ))
                stored_ids.append(entry_id)

            conn.commit()

        logger.info(f"Stored {len(stored_ids)} knowledge entries for user {user_id}")
        return stored_ids

    def search(self, query: KnowledgeQuery) -> list[KnowledgeEntry]:
        """
        Search knowledge base.

        Args:
            query: Search query parameters

        Returns:
            List of matching knowledge entries
        """
        conn = self._get_conn()
        entries = []

        # Build query
        if query.query:
            # Full-text search
            sql = """
                SELECT e.*
                FROM knowledge_entries e
                JOIN knowledge_fts f ON e.id = f.id
                WHERE knowledge_fts MATCH ?
            """
            params = [query.query]
        else:
            sql = "SELECT * FROM knowledge_entries WHERE 1=1"
            params = []

        # Add filters
        if query.entry_type:
            sql += " AND entry_type = ?"
            params.append(query.entry_type)

        if query.user_id:
            sql += " AND user_id = ?"
            params.append(query.user_id)

        if query.workspace_root:
            sql += " AND (workspace_root = ? OR workspace_root IS NULL)"
            params.append(query.workspace_root)

        if query.min_score > 0:
            sql += " AND usefulness_score >= ?"
            params.append(query.min_score)

        # Order by relevance and usefulness
        sql += " ORDER BY usefulness_score DESC, access_count DESC"
        sql += f" LIMIT {query.limit}"

        cursor = conn.execute(sql, params)

        for row in cursor:
            entries.append(KnowledgeEntry(
                id=row["id"],
                entry_type=row["entry_type"],
                user_id=row["user_id"],
                workspace_root=row["workspace_root"],
                data=json.loads(row["data_json"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                access_count=row["access_count"],
                usefulness_score=row["usefulness_score"],
            ))

        # Track access
        if entries:
            entry_ids = [e.id for e in entries]
            self._increment_access(entry_ids)

        return entries

    def get_topics(
        self,
        user_id: str,
        workspace_root: str | None = None,
        limit: int = 20,
    ) -> list[Topic]:
        """Get topics for a user/workspace."""
        query = KnowledgeQuery(
            entry_type="topic",
            user_id=user_id,
            workspace_root=workspace_root,
            limit=limit,
        )

        entries = self.search(query)

        return [
            Topic(
                name=e.data.get("name", ""),
                category=TopicCategory(e.data.get("category", "general")),
                confidence=e.data.get("confidence", 0.5),
                keywords=e.data.get("keywords", []),
                frequency=e.data.get("frequency", 1),
                last_seen=e.data.get("last_seen", ""),
            )
            for e in entries
        ]

    def get_patterns(
        self,
        user_id: str,
        workspace_root: str | None = None,
        pattern_type: PatternType | None = None,
        limit: int = 20,
    ) -> list[CodePattern]:
        """Get code patterns for a user/workspace."""
        query = KnowledgeQuery(
            entry_type="pattern",
            user_id=user_id,
            workspace_root=workspace_root,
            limit=limit,
        )

        entries = self.search(query)

        patterns = []
        for e in entries:
            pt = PatternType(e.data.get("pattern_type", "other"))
            if pattern_type and pt != pattern_type:
                continue

            patterns.append(CodePattern(
                name=e.data.get("name", ""),
                pattern_type=pt,
                description=e.data.get("description", ""),
                example_code=e.data.get("example_code", ""),
                language=e.data.get("language", ""),
                files_seen_in=e.data.get("files_seen_in", []),
                frequency=e.data.get("frequency", 1),
            ))

        return patterns

    def get_solutions(
        self,
        user_id: str,
        workspace_root: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[ProblemSolution]:
        """Get problem-solution pairs."""
        query = KnowledgeQuery(
            entry_type="solution",
            user_id=user_id,
            workspace_root=workspace_root,
            limit=limit * 2 if tags else limit,  # Fetch more for filtering
        )

        entries = self.search(query)

        solutions = []
        for e in entries:
            entry_tags = e.data.get("tags", [])

            # Filter by tags if specified
            if tags and not any(t in entry_tags for t in tags):
                continue

            solutions.append(ProblemSolution(
                problem=e.data.get("problem", ""),
                solution=e.data.get("solution", ""),
                context=e.data.get("context", ""),
                files_involved=e.data.get("files_involved", []),
                tags=entry_tags,
                effectiveness_score=e.data.get("effectiveness_score", 0.0),
                created_at=e.data.get("created_at", ""),
            ))

            if len(solutions) >= limit:
                break

        return solutions

    def find_similar_solutions(
        self,
        problem: str,
        user_id: str,
        limit: int = 5,
    ) -> list[ProblemSolution]:
        """
        Find solutions similar to a given problem.

        Uses FTS to find relevant past solutions.
        """
        query = KnowledgeQuery(
            query=problem,
            entry_type="solution",
            user_id=user_id,
            limit=limit,
        )

        entries = self.search(query)

        return [
            ProblemSolution(
                problem=e.data.get("problem", ""),
                solution=e.data.get("solution", ""),
                context=e.data.get("context", ""),
                tags=e.data.get("tags", []),
                effectiveness_score=e.data.get("effectiveness_score", 0.0),
            )
            for e in entries
        ]

    def update_usefulness(
        self,
        entry_id: str,
        helpful: bool,
    ) -> None:
        """
        Update usefulness score based on feedback.

        Args:
            entry_id: Entry ID
            helpful: Whether the knowledge was helpful
        """
        conn = self._get_conn()

        # Adjust score
        delta = 0.1 if helpful else -0.05

        with self._write_lock:
            conn.execute("""
                UPDATE knowledge_entries
                SET usefulness_score = MAX(0, MIN(1, usefulness_score + ?))
                WHERE id = ?
            """, (delta, entry_id))
            conn.commit()

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
    ) -> None:
        """Add a relation between knowledge entries."""
        conn = self._get_conn()

        with self._write_lock:
            conn.execute("""
                INSERT INTO knowledge_relations
                (source_id, target_id, relation_type, strength)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation_type)
                DO UPDATE SET strength = strength + ?
            """, (source_id, target_id, relation_type, strength, strength * 0.1))
            conn.commit()

    def get_related(
        self,
        entry_id: str,
        relation_type: str | None = None,
        limit: int = 10,
    ) -> list[KnowledgeEntry]:
        """Get related knowledge entries."""
        conn = self._get_conn()

        sql = """
            SELECT e.*
            FROM knowledge_entries e
            JOIN knowledge_relations r ON e.id = r.target_id
            WHERE r.source_id = ?
        """
        params = [entry_id]

        if relation_type:
            sql += " AND r.relation_type = ?"
            params.append(relation_type)

        sql += " ORDER BY r.strength DESC LIMIT ?"
        params.append(limit)

        entries = []
        for row in conn.execute(sql, params):
            entries.append(KnowledgeEntry(
                id=row["id"],
                entry_type=row["entry_type"],
                user_id=row["user_id"],
                workspace_root=row["workspace_root"],
                data=json.loads(row["data_json"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                access_count=row["access_count"],
                usefulness_score=row["usefulness_score"],
            ))

        return entries

    def _increment_access(self, entry_ids: list[str]) -> None:
        """Increment access count for entries."""
        conn = self._get_conn()

        with self._write_lock:
            placeholders = ",".join("?" * len(entry_ids))
            conn.execute(f"""
                UPDATE knowledge_entries
                SET access_count = access_count + 1
                WHERE id IN ({placeholders})
            """, entry_ids)
            conn.commit()

    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get knowledge store statistics."""
        conn = self._get_conn()

        stats = {}

        # Total entries
        if user_id:
            row = conn.execute(
                "SELECT COUNT(*) as total FROM knowledge_entries WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as total FROM knowledge_entries"
            ).fetchone()

        stats["total_entries"] = row["total"]

        # By type
        sql = "SELECT entry_type, COUNT(*) as count FROM knowledge_entries"
        if user_id:
            sql += " WHERE user_id = ?"
            cursor = conn.execute(sql + " GROUP BY entry_type", (user_id,))
        else:
            cursor = conn.execute(sql + " GROUP BY entry_type")

        stats["by_type"] = {row["entry_type"]: row["count"] for row in cursor}

        # Top accessed
        row = conn.execute("""
            SELECT id, access_count
            FROM knowledge_entries
            ORDER BY access_count DESC
            LIMIT 1
        """).fetchone()

        if row:
            stats["most_accessed"] = {"id": row["id"], "count": row["access_count"]}

        return stats


# Global instance
_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    """Get or create global knowledge store."""
    global _store

    if _store is None:
        data_dir = Path.home() / ".magnetarcode/data"
        db_path = data_dir / "knowledge.db"
        _store = KnowledgeStore(db_path)

    return _store
