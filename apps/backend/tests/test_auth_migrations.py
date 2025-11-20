"""
Tests for auth migration system (AUTH-P1)

Validates that:
1. Auth migrations run successfully on a fresh database
2. Auth schema tables are created correctly
3. Migration tracking works properly
4. Migrations are idempotent (can run multiple times safely)
"""

import sqlite3
import tempfile
import pytest
from pathlib import Path


def test_auth_migrations_fresh_db():
    """
    Test auth migrations on a fresh database

    Creates a temporary empty database and runs auth migrations.
    Verifies that all expected tables are created.
    """
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    try:
        # Connect to fresh database
        conn = sqlite3.connect(str(tmp_db_path))
        cursor = conn.cursor()

        # Verify database is empty (no tables)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_before = cursor.fetchall()
        assert len(tables_before) == 0, "Database should be empty initially"

        # Run auth migrations
        from api.migrations.auth import run_auth_migrations
        run_auth_migrations(conn)

        # Verify migrations table exists and contains auth migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'")
        assert cursor.fetchone() is not None, "migrations table should exist"

        cursor.execute("SELECT migration_name FROM migrations WHERE migration_name LIKE 'auth_%'")
        auth_migrations = cursor.fetchall()
        assert len(auth_migrations) >= 1, "At least one auth migration should be recorded"
        assert any('auth_0001_initial' in m[0] for m in auth_migrations), "auth_0001_initial should be recorded"

        # Verify all expected auth tables exist
        expected_tables = [
            "users",
            "sessions",
            "user_profiles",
            "permissions",
            "permission_profiles",
            "profile_permissions",
            "permission_sets",
            "permission_set_permissions",
            "user_permission_profiles",
            "user_permission_sets",
            "user_permissions_cache",
        ]

        for table in expected_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            result = cursor.fetchone()
            assert result is not None, f"Table '{table}' should exist after auth migrations"

        # Verify users table has correct columns
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in cursor.fetchall()}  # row[1] is column name
        expected_user_columns = {
            "user_id", "username", "password_hash", "device_id",
            "created_at", "last_login", "is_active", "role", "job_role"
        }
        assert expected_user_columns.issubset(user_columns), \
            f"users table should have all expected columns. Missing: {expected_user_columns - user_columns}"

        # Verify sessions table has correct columns
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = {row[1] for row in cursor.fetchall()}
        expected_session_columns = {
            "session_id", "user_id", "token_hash", "refresh_token_hash",
            "created_at", "expires_at", "refresh_expires_at",
            "device_fingerprint", "last_activity"
        }
        assert expected_session_columns.issubset(session_columns), \
            f"sessions table should have all expected columns. Missing: {expected_session_columns - session_columns}"

        conn.close()

    finally:
        # Cleanup
        tmp_db_path.unlink(missing_ok=True)


def test_auth_migrations_idempotent():
    """
    Test that auth migrations are idempotent

    Runs auth migrations twice on the same database.
    Second run should not fail and should not create duplicate records.
    """
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    try:
        conn = sqlite3.connect(str(tmp_db_path))

        # Run auth migrations first time
        from api.migrations.auth import run_auth_migrations
        run_auth_migrations(conn)

        # Count migrations after first run
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM migrations WHERE migration_name LIKE 'auth_%'")
        count_after_first = cursor.fetchone()[0]

        # Run auth migrations second time (should be idempotent)
        run_auth_migrations(conn)

        # Count migrations after second run
        cursor.execute("SELECT COUNT(*) FROM migrations WHERE migration_name LIKE 'auth_%'")
        count_after_second = cursor.fetchone()[0]

        # Should have same number of migrations (no duplicates)
        assert count_after_first == count_after_second, \
            "Running migrations twice should not create duplicate migration records"

        # Verify no errors occurred and tables still exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None, "users table should still exist after second migration run"

        conn.close()

    finally:
        # Cleanup
        tmp_db_path.unlink(missing_ok=True)


def test_auth_migrations_with_existing_tables():
    """
    Test auth migrations when some tables already exist

    This simulates the scenario where an existing ElohimOS instance
    upgrades to the new migration system. Tables created by auth_middleware
    should not conflict with migrations.
    """
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    try:
        conn = sqlite3.connect(str(tmp_db_path))
        cursor = conn.cursor()

        # Manually create users table (simulating existing deployment)
        cursor.execute("""
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                role TEXT DEFAULT 'member'
            )
        """)
        conn.commit()

        # Insert a test user
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_user_1", "testuser", "hash123", "device1", "2025-01-01T00:00:00", "member"))
        conn.commit()

        # Run auth migrations (should not fail even though users table exists)
        from api.migrations.auth import run_auth_migrations
        run_auth_migrations(conn)

        # Verify user data is preserved
        cursor.execute("SELECT user_id, username FROM users WHERE user_id = ?", ("test_user_1",))
        user = cursor.fetchone()
        assert user is not None, "Existing user should be preserved"
        assert user[1] == "testuser", "User data should be intact"

        # Verify other tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permissions'")
        assert cursor.fetchone() is not None, "permissions table should be created by migrations"

        conn.close()

    finally:
        # Cleanup
        tmp_db_path.unlink(missing_ok=True)
