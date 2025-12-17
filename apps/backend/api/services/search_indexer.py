"""
Search Indexer Service - Sprint 6 Theme B

Manages FTS5 index for session message search.
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "data/elohimos.db"

class SearchIndexer:
    """Service for indexing messages into FTS5 for search"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_message_to_index(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: str,
        user_id: str
    ):
        """
        Add a message to the FTS5 index

        Args:
            session_id: Chat session ID
            role: Message role (user/assistant/system)
            content: Message content
            timestamp: ISO timestamp
            user_id: User who owns the session
        """
        # Skip empty messages
        if not content or not content.strip():
            return

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO messages_fts (content, session_id, ts, user_id, role)
                VALUES (?, ?, ?, ?, ?)
            """, (content, session_id, timestamp, user_id, role))

            conn.commit()
            logger.debug(f"Indexed message for session {session_id}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to index message: {e}")
            # Don't raise - indexing failure shouldn't break chat
        finally:
            conn.close()

    def backfill_from_chat_memory(self, limit: Optional[int] = None):
        """
        Backfill FTS index from existing chat_memory messages

        Args:
            limit: Optional limit on number of messages to index (for testing)
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Clear existing FTS entries (for clean backfill)
            cursor.execute("DELETE FROM messages_fts")

            # Get all messages from chat_memory
            # Note: chat_memory stores messages as JSON in the 'messages' column
            # We need to parse each session's messages array
            if limit:
                cursor.execute("""
                    SELECT session_id, messages, user_id
                    FROM chat_memory
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT session_id, messages, user_id
                    FROM chat_memory
                """)

            sessions = cursor.fetchall()
            total_messages = 0

            import json
            for session in sessions:
                session_id = session['session_id']
                user_id = session['user_id']

                try:
                    messages = json.loads(session['messages'])

                    for msg in messages:
                        if isinstance(msg, dict) and 'content' in msg:
                            content = msg.get('content', '')
                            role = msg.get('role', 'user')
                            timestamp = msg.get('timestamp', datetime.now(UTC).isoformat())

                            if content and content.strip():
                                cursor.execute("""
                                    INSERT INTO messages_fts (content, session_id, ts, user_id, role)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (content, session_id, timestamp, user_id, role))
                                total_messages += 1

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse messages for session {session_id}: {e}")
                    continue

            conn.commit()
            logger.info(f"✅ Backfilled {total_messages} messages from {len(sessions)} sessions into FTS index")
            return total_messages

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to backfill FTS index: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def rebuild_index(self):
        """
        Rebuild the entire FTS index (maintenance operation)

        This is useful if the index gets corrupted or out of sync
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Use FTS5's rebuild command
            cursor.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
            conn.commit()
            logger.info("✅ FTS index rebuilt successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rebuild FTS index: {e}")
            raise
        finally:
            conn.close()

    def optimize_index(self):
        """
        Optimize the FTS index (improves search performance)

        Should be run periodically (e.g., daily via background job)
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO messages_fts(messages_fts) VALUES('optimize')")
            conn.commit()
            logger.info("✅ FTS index optimized successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to optimize FTS index: {e}")
            raise
        finally:
            conn.close()

    def get_index_stats(self):
        """Get statistics about the FTS index"""
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Count total indexed messages
            cursor.execute("SELECT COUNT(*) as count FROM messages_fts")
            row = cursor.fetchone()
            total_messages = row['count'] if row else 0

            # Count unique sessions
            cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM messages_fts")
            row = cursor.fetchone()
            total_sessions = row['count'] if row else 0

            return {
                "total_messages": total_messages,
                "total_sessions": total_sessions
            }

        finally:
            conn.close()


# Singleton instance
_search_indexer = None

def get_search_indexer() -> SearchIndexer:
    """Get singleton search indexer instance"""
    global _search_indexer
    if _search_indexer is None:
        _search_indexer = SearchIndexer()
    return _search_indexer
