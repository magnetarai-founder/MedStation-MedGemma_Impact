"""
Sprint 6 Theme C - Model Performance KPIs Migration

Adds columns to analytics_daily for model performance metrics:
- response_time_avg: Average response latency in milliseconds
- response_time_p95: 95th percentile response latency
- satisfaction_score: Average feedback score (-1 to +1)
- message_count: Total messages for the model
"""

import sqlite3

def check_migration_applied(db_path: str) -> bool:
    """Return True if KPI columns exist on analytics_daily"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info('analytics_daily')")
        cols = {row[1] for row in cur.fetchall()}
        return 'response_time_avg' in cols and 'response_time_p95' in cols and 'satisfaction_score' in cols and 'message_count' in cols
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass

def migrate(db_path: str):
    """Run the migration"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add new columns for model KPIs
        print("Adding model KPI columns to analytics_daily...")

        cursor.execute("""
            ALTER TABLE analytics_daily
            ADD COLUMN response_time_avg INTEGER DEFAULT NULL
        """)

        cursor.execute("""
            ALTER TABLE analytics_daily
            ADD COLUMN response_time_p95 INTEGER DEFAULT NULL
        """)

        cursor.execute("""
            ALTER TABLE analytics_daily
            ADD COLUMN satisfaction_score REAL DEFAULT NULL
        """)

        cursor.execute("""
            ALTER TABLE analytics_daily
            ADD COLUMN message_count INTEGER DEFAULT 0
        """)

        conn.commit()
        print("✅ Model KPI columns added successfully")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Columns already exist, skipping...")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    # No default path; run via startup migrations
    pass
