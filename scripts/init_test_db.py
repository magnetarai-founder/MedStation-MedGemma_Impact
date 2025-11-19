#!/usr/bin/env python3
"""
Initialize test database for Team service smoke test

Creates the necessary tables matching core.py:_init_database() schema.
"""

import sqlite3
from api.config_paths import get_config_paths

def init_test_db():
    PATHS = get_config_paths()
    APP_DB = PATHS.app_db

    print(f"Initializing database at: {APP_DB}")

    conn = sqlite3.connect(str(APP_DB))
    cursor = conn.cursor()

    # Teams table (from core.py:_init_database line 57-65)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL
        )
    """)

    # Team members table (from core.py:_init_database line 68-80)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            job_role TEXT DEFAULT 'unassigned',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id),
            UNIQUE(team_id, user_id)
        )
    """)

    # Invite codes table (from core.py:_init_database line 83-94)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            code TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            used BOOLEAN DEFAULT FALSE,
            used_by TEXT,
            used_at TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        )
    """)

    # Invite code attempts tracking (from core.py:_init_database line 132-140)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invite_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL
        )
    """)

    # Index for fast lookup of recent attempts (from core.py:_init_database line 143-146)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_invite_attempts_code_ip
        ON invite_attempts(invite_code, ip_address, attempt_timestamp DESC)
    """)

    conn.commit()
    conn.close()

    print("✓ Database initialized successfully")
    print("  - teams table created (with description column)")
    print("  - team_members table created")
    print("  - invite_codes table created")
    print("  - invite_attempts table created")
    print("  - idx_invite_attempts_code_ip index created")

if __name__ == "__main__":
    init_test_db()
