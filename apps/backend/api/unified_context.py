#!/usr/bin/env python3
"""
Unified Context Manager for ElohimOS
Shares context across Chat, Terminal, and Code tabs with 200k+ rolling window
"""

import logging
import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

try:
    from .config_paths import PATHS
except ImportError:
    from config_paths import PATHS

logger = logging.getLogger(__name__)

# PATHS imported from config_paths module


@dataclass
class ContextEntry:
    """Single context entry"""
    entry_id: str
    user_id: str
    session_id: str
    source: str  # 'chat', 'terminal', 'code', 'agent'
    entry_type: str  # 'message', 'command', 'file_edit', 'patch', 'plan'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens_estimate: int = 0


class UnifiedContextManager:
    """
    Manages shared context across all ElohimOS components

    - Chat messages persist and are visible to terminal/code
    - Terminal commands/output persist and are visible to chat/code
    - Code edits persist and are visible to chat/terminal
    - Agent plans persist across all contexts
    - Rolling 200k token window (configurable)
    """

    def __init__(self, db_path: Optional[Path] = None):
        # Use PATHS.data_dir for consistent location
        if db_path is None:
            db_path = PATHS.data_dir / "unified_context.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Token limits
        self.max_tokens_per_session = 200_000
        self.max_tokens_global = 1_000_000  # Across all sessions

    def _init_db(self) -> None:
        """Initialize unified context database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_entries (
                entry_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                tokens_estimate INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_session
            ON context_entries(session_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_user
            ON context_entries(user_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_source
            ON context_entries(source, timestamp DESC)
        """)

        # Session metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_root TEXT,
                active_files TEXT,
                total_tokens INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_activity TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_entry(
        self,
        user_id: str,
        session_id: str,
        source: str,
        entry_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a context entry

        Args:
            user_id: User ID
            session_id: Session ID (shared across chat/terminal/code)
            source: 'chat', 'terminal', 'code', 'agent'
            entry_type: 'message', 'command', 'file_edit', 'patch', 'plan'
            content: The actual content
            metadata: Additional structured data

        Returns:
            entry_id
        """
        import hashlib
        import time

        # Generate entry ID
        entry_id = f"{source}_{int(time.time())}_{hashlib.sha256(content.encode()).hexdigest()[:8]}"

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        tokens_estimate = len(content) // 4

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Insert entry
        cursor.execute("""
            INSERT INTO context_entries
            (entry_id, user_id, session_id, source, entry_type, content, metadata, timestamp, tokens_estimate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            user_id,
            session_id,
            source,
            entry_type,
            content,
            json.dumps(metadata or {}),
            datetime.now(UTC).isoformat(),
            tokens_estimate
        ))

        # Update session metadata
        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, total_tokens, last_activity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                total_tokens = total_tokens + ?,
                last_activity = ?
        """, (
            session_id,
            user_id,
            tokens_estimate,
            datetime.now(UTC).isoformat(),
            tokens_estimate,
            datetime.now(UTC).isoformat()
        ))

        conn.commit()
        conn.close()

        # Cleanup old entries if over limit
        self._cleanup_session(session_id)
        self._cleanup_global_tokens(user_id)

        logger.debug(f"Added context entry {entry_id} ({tokens_estimate} tokens)")
        return entry_id

    def get_session_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
        sources: Optional[List[str]] = None,
        since: Optional[datetime] = None
    ) -> List[ContextEntry]:
        """
        Get all context for a session

        Args:
            session_id: Session ID
            max_tokens: Maximum tokens to return (default: self.max_tokens_per_session)
            sources: Filter by source(s) ['chat', 'terminal', 'code', 'agent']
            since: Only entries after this timestamp

        Returns:
            List of ContextEntry objects in chronological order
        """
        max_tokens = max_tokens or self.max_tokens_per_session

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT entry_id, user_id, session_id, source, entry_type, content, metadata, timestamp, tokens_estimate
            FROM context_entries
            WHERE session_id = ?
        """
        params = [session_id]

        if sources:
            placeholders = ','.join('?' * len(sources))
            query += f" AND source IN ({placeholders})"
            params.extend(sources)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Convert to ContextEntry objects and enforce token limit
        entries = []
        total_tokens = 0

        for row in rows:
            entry = ContextEntry(
                entry_id=row[0],
                user_id=row[1],
                session_id=row[2],
                source=row[3],
                entry_type=row[4],
                content=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
                timestamp=datetime.fromisoformat(row[7]),
                tokens_estimate=row[8]
            )

            # Check token limit
            if total_tokens + entry.tokens_estimate > max_tokens:
                break

            entries.append(entry)
            total_tokens += entry.tokens_estimate

        # Return in chronological order
        entries.reverse()

        logger.debug(f"Retrieved {len(entries)} entries ({total_tokens} tokens) for session {session_id}")
        return entries

    def get_recent_context(
        self,
        user_id: str,
        max_entries: int = 50,
        sources: Optional[List[str]] = None
    ) -> List[ContextEntry]:
        """Get recent context across all sessions for a user"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = """
            SELECT entry_id, user_id, session_id, source, entry_type, content, metadata, timestamp, tokens_estimate
            FROM context_entries
            WHERE user_id = ?
        """
        params = [user_id]

        if sources:
            placeholders = ','.join('?' * len(sources))
            query += f" AND source IN ({placeholders})"
            params.extend(sources)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(max_entries)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        entries = []
        for row in rows:
            entries.append(ContextEntry(
                entry_id=row[0],
                user_id=row[1],
                session_id=row[2],
                source=row[3],
                entry_type=row[4],
                content=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
                timestamp=datetime.fromisoformat(row[7]),
                tokens_estimate=row[8]
            ))

        # Return in chronological order
        entries.reverse()
        return entries

    def build_prompt_context(
        self,
        session_id: str,
        max_tokens: int = 150_000,
        include_sources: Optional[List[str]] = None
    ) -> str:
        """
        Build formatted context for LLM prompt

        Args:
            session_id: Session ID
            max_tokens: Max tokens to include
            include_sources: Sources to include (default: all)

        Returns:
            Formatted context string ready for prompt injection
        """
        entries = self.get_session_context(
            session_id=session_id,
            max_tokens=max_tokens,
            sources=include_sources
        )

        if not entries:
            return ""

        # Build formatted context
        sections = {
            'chat': [],
            'terminal': [],
            'code': [],
            'agent': []
        }

        for entry in entries:
            source = entry.source
            if source in sections:
                if entry.entry_type == 'message':
                    role = entry.metadata.get('role', 'user')
                    sections[source].append(f"{role}: {entry.content}")
                elif entry.entry_type == 'command':
                    sections[source].append(f"$ {entry.content}")
                    if 'output' in entry.metadata:
                        sections[source].append(entry.metadata['output'][:500])  # Truncate output
                elif entry.entry_type == 'file_edit':
                    file_path = entry.metadata.get('file_path', 'unknown')
                    sections[source].append(f"Edited {file_path}")
                elif entry.entry_type == 'patch':
                    files = entry.metadata.get('files', [])
                    sections[source].append(f"Applied patch to {len(files)} file(s)")
                elif entry.entry_type == 'plan':
                    sections[source].append(f"Plan: {entry.content[:200]}...")

        # Format output
        context_parts = []

        if sections['chat']:
            context_parts.append("# Recent Chat History\n" + "\n".join(sections['chat']))

        if sections['terminal']:
            context_parts.append("# Terminal Activity\n" + "\n".join(sections['terminal']))

        if sections['code']:
            context_parts.append("# Code Changes\n" + "\n".join(sections['code']))

        if sections['agent']:
            context_parts.append("# Agent Plans\n" + "\n".join(sections['agent']))

        return "\n\n".join(context_parts)

    def _cleanup_session(self, session_id: str) -> None:
        """Remove old entries if session exceeds token limit"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get current total
        cursor.execute("""
            SELECT SUM(tokens_estimate) FROM context_entries WHERE session_id = ?
        """, (session_id,))
        total = cursor.fetchone()[0] or 0

        if total > self.max_tokens_per_session:
            # Delete oldest entries until under limit
            cursor.execute("""
                DELETE FROM context_entries
                WHERE entry_id IN (
                    SELECT entry_id FROM context_entries
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT (
                        SELECT COUNT(*) FROM context_entries
                        WHERE session_id = ?
                    ) / 4
                )
            """, (session_id, session_id))

            logger.info(f"Cleaned up old entries for session {session_id}")

        conn.commit()
        conn.close()

    def _cleanup_global_tokens(self, user_id: str) -> None:
        """Remove old entries across all sessions if user exceeds global token limit"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get current total across all user's sessions
        cursor.execute("""
            SELECT SUM(tokens_estimate) FROM context_entries WHERE user_id = ?
        """, (user_id,))
        total = cursor.fetchone()[0] or 0

        if total > self.max_tokens_global:
            # Delete oldest entries across all sessions until under global limit
            # Delete 25% of oldest entries
            cursor.execute("""
                DELETE FROM context_entries
                WHERE entry_id IN (
                    SELECT entry_id FROM context_entries
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                    LIMIT (
                        SELECT COUNT(*) FROM context_entries
                        WHERE user_id = ?
                    ) / 4
                )
            """, (user_id, user_id))

            deleted = cursor.rowcount
            logger.info(f"Global cleanup: removed {deleted} old entries for user {user_id}")

        conn.commit()
        conn.close()

    def update_session_workspace(self, session_id: str, workspace_root: str, active_files: List[str]) -> None:
        """Update session workspace metadata"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE sessions
            SET workspace_root = ?, active_files = ?, last_activity = ?
            WHERE session_id = ?
        """, (
            workspace_root,
            json.dumps(active_files),
            datetime.now(UTC).isoformat(),
            session_id
        ))

        conn.commit()
        conn.close()

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, workspace_root, active_files, total_tokens, created_at, last_activity
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'session_id': row[0],
            'user_id': row[1],
            'workspace_root': row[2],
            'active_files': json.loads(row[3]) if row[3] else [],
            'total_tokens': row[4],
            'created_at': row[5],
            'last_activity': row[6]
        }


# Global instance
_unified_context = None

def get_unified_context() -> UnifiedContextManager:
    """Get global unified context manager instance"""
    global _unified_context
    if _unified_context is None:
        _unified_context = UnifiedContextManager()
    return _unified_context
