"""
Sprint 6 Theme A: Analytics Schema

Creates tables for raw analytics events and daily aggregates.
Enables usage tracking, performance monitoring, and trend analysis.
"""

import sqlite3
from pathlib import Path

def check_migration_applied(db_path: str) -> bool:
    """Return True if analytics tables exist in the DB"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Check existence of analytics_daily (also implies events were created)
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('analytics_events','analytics_daily')
        """)
        names = {row[0] for row in cur.fetchall()}
        return 'analytics_daily' in names and 'analytics_events' in names
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass

def migrate(db_path: str) -> None:
    """Create analytics tables with proper indexes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Raw analytics events (high-volume, append-only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                user_id TEXT NOT NULL,
                team_id TEXT,
                session_id TEXT,
                event_type TEXT NOT NULL,
                model_name TEXT,
                tokens_used INTEGER,
                duration_ms INTEGER,
                error_code TEXT,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            )
        """)

        # Indexes for common query patterns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_ts ON analytics_events(ts)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_user_team ON analytics_events(user_id, team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_model ON analytics_events(model_name)")

        # Daily aggregates (pre-computed for dashboard queries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_daily (
                date TEXT NOT NULL,
                team_id TEXT,
                user_id TEXT,
                model_name TEXT,
                sessions_count INTEGER DEFAULT 0,
                tokens_total INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                PRIMARY KEY (date, team_id, user_id, model_name),
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Index for date-range queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_daily_date ON analytics_daily(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_daily_team ON analytics_daily(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_daily_user ON analytics_daily(user_id)")

        conn.commit()
        print("✅ Analytics tables created successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # No default path; run via startup migrations
    pass
