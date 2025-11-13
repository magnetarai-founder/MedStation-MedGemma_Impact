"""
Sprint 6 Theme C - Model Performance KPIs Migration

Adds columns to analytics_daily for model performance metrics:
- response_time_avg: Average response latency in milliseconds
- response_time_p95: 95th percentile response latency
- satisfaction_score: Average feedback score (-1 to +1)
- message_count: Total messages for the model
"""

import sqlite3

def migrate():
    """Run the migration"""
    conn = sqlite3.connect("data/elohimos.db")
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
    migrate()
