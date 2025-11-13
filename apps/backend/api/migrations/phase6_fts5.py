"""
Sprint 6 Theme B: Full-Text Search Migration

Creates FTS5 virtual table for fast session message search.
"""

import sqlite3
from pathlib import Path

def migrate(db_path: str = "data/elohimos.db"):
    """Create FTS5 virtual table for message search"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create FTS5 virtual table for messages
        # FTS5 provides fast full-text search with ranking and snippets
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                session_id UNINDEXED,
                ts UNINDEXED,
                user_id UNINDEXED,
                role UNINDEXED,
                tokenize = 'porter unicode61'
            )
        """)

        print("✅ FTS5 virtual table created successfully")
        print("   Note: Initial indexing will be done by search_indexer service")

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"❌ FTS5 migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Auto-run if executed directly
    migrate()
