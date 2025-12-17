"""
Auth Update Safety Tests (AUTH-P6)

Tests that verify auth data survives updates and device identity is stable.

These tests simulate the "update" flow by:
1. Creating auth data with old schema
2. Running new migrations
3. Verifying data survives and device identity is stable

Key scenarios tested:
- Existing users survive migration to device_identity schema
- Device identity is stable across restarts
- Migrations are idempotent (can run multiple times)
- Device identity persists even if all users are deleted

These tests ensure that updates never break auth data.
"""

import sqlite3
import tempfile
import pytest
import time
from pathlib import Path
from datetime import datetime, UTC

from api.migrations.auth import run_auth_migrations
from api.device_identity import ensure_device_identity, get_device_identity


# ==================== User Survival Tests ====================

def test_existing_user_survives_migration():
    """
    Test that existing users survive migration to device_identity schema.

    Simulates an "update" by:
    1. Creating user with old schema (migrations 0001 + 0002)
    2. Running new migration 0003 (device_identity)
    3. Verifying user data is unchanged

    This proves updates preserve existing auth data.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db_path))

        # Step 1: Run migrations 0001 and 0002 (old schema)
        from api.migrations.auth import runner
        runner._ensure_migration_table(conn)

        # Import and run migrations 0001 and 0002 only
        import importlib
        migration_0001 = importlib.import_module(".0001_initial", package="api.migrations.auth")
        migration_0002 = importlib.import_module(".0002_founder_role", package="api.migrations.auth")

        migration_0001.apply_migration(conn)
        runner._record_migration(conn, "auth_0001_initial", "Initial schema")
        migration_0002.apply_migration(conn)
        runner._record_migration(conn, "auth_0002_founder_role", "Founder role")

        # Step 2: Create a test user
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                user_id, username, password_hash, device_id,
                created_at, role, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_user_123",
            "testuser",
            "hash_placeholder",
            "device_abc",
            datetime.now(UTC).isoformat(),
            "member",
            1
        ))
        conn.commit()

        # Verify user exists before migration
        cursor.execute("SELECT user_id, username, role FROM users WHERE user_id = ?", ("test_user_123",))
        user_before = cursor.fetchone()
        assert user_before is not None
        assert user_before[0] == "test_user_123"
        assert user_before[1] == "testuser"
        assert user_before[2] == "member"

        # Step 3: Run migration 0003 (device_identity)
        import importlib
        migration_0003 = importlib.import_module(".0003_device_identity", package="api.migrations.auth")
        migration_0003.apply_migration(conn)
        runner._record_migration(conn, "auth_0003_device_identity", "Device identity")

        # Step 4: Verify user still exists with same data
        cursor.execute("SELECT user_id, username, role FROM users WHERE user_id = ?", ("test_user_123",))
        user_after = cursor.fetchone()

        assert user_after is not None, "User should still exist after migration"
        assert user_after[0] == "test_user_123", "User ID should be unchanged"
        assert user_after[1] == "testuser", "Username should be unchanged"
        assert user_after[2] == "member", "Role should be unchanged"

        conn.close()


def test_all_auth_migrations_preserve_users():
    """
    Test that running ALL auth migrations preserves existing users.

    This is the most realistic "update" simulation:
    1. Create user with minimal schema
    2. Run all migrations via run_auth_migrations()
    3. Verify user data is unchanged

    This proves the full migration path is safe.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db_path))

        # Create migrations table manually
        from api.migrations.auth import runner
        runner._ensure_migration_table(conn)

        # Create users table manually (minimal schema)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1
            )
        """)

        # Insert test user
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "user_abc",
            "alice",
            "hash123",
            "device_xyz",
            datetime.now(UTC).isoformat(),
            "admin"
        ))
        conn.commit()

        # Run ALL auth migrations
        run_auth_migrations(conn)

        # Verify user still exists
        cursor.execute("SELECT user_id, username, role FROM users WHERE user_id = ?", ("user_abc",))
        user = cursor.fetchone()

        assert user is not None, "User should survive all migrations"
        assert user[0] == "user_abc"
        assert user[1] == "alice"
        assert user[2] == "admin"

        conn.close()


# ==================== Device Identity Stability Tests ====================

def test_device_identity_is_stable():
    """
    Test that device identity is stable across multiple calls.

    Verifies:
    - First call creates device_identity row
    - Second call returns same device_id
    - last_boot_at is updated on second call
    - machine_id remains the same

    This proves device identity survives restarts.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db_path))

        # Run migrations to create device_identity table
        run_auth_migrations(conn)

        # First call: Create device identity
        device_id_1 = ensure_device_identity(conn)
        assert device_id_1 is not None
        assert len(device_id_1) == 36  # UUID format

        # Get details after first call
        cursor = conn.cursor()
        cursor.execute("""
            SELECT device_id, machine_id, created_at, last_boot_at
            FROM device_identity
        """)
        row_1 = cursor.fetchone()
        assert row_1 is not None

        device_id_before = row_1[0]
        machine_id_before = row_1[1]
        created_at_before = row_1[2]
        last_boot_before = row_1[3]

        # Wait a moment to ensure timestamp changes
        time.sleep(0.1)

        # Second call: Should return same device_id
        device_id_2 = ensure_device_identity(conn)

        # Get details after second call
        cursor.execute("""
            SELECT device_id, machine_id, created_at, last_boot_at
            FROM device_identity
        """)
        row_2 = cursor.fetchone()
        assert row_2 is not None

        device_id_after = row_2[0]
        machine_id_after = row_2[1]
        created_at_after = row_2[2]
        last_boot_after = row_2[3]

        # Verify stability
        assert device_id_1 == device_id_2, "Device ID should be stable across calls"
        assert device_id_before == device_id_after, "Device ID should not change"
        assert machine_id_before == machine_id_after, "Machine ID should not change"
        assert created_at_before == created_at_after, "Creation timestamp should not change"
        assert last_boot_after > last_boot_before, "last_boot_at should be updated"

        conn.close()


def test_device_identity_persists_after_user_deletion():
    """
    Test that device identity persists even if all users are deleted.

    This is critical for update safety:
    - Device identity is independent of user accounts
    - Used by future update server to identify this machine
    - Must survive even complete user data reset

    Verifies:
    1. Create device identity
    2. Create user
    3. Delete user
    4. Device identity still exists and is unchanged
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db_path))

        # Run migrations
        run_auth_migrations(conn)

        # Create device identity
        device_id = ensure_device_identity(conn)
        assert device_id is not None

        # Create test user
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "user_to_delete",
            "temp_user",
            "hash",
            "device_123",
            datetime.now(UTC).isoformat()
        ))
        conn.commit()

        # Verify user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", ("user_to_delete",))
        user_count_before = cursor.fetchone()[0]
        assert user_count_before == 1

        # Delete the user
        cursor.execute("DELETE FROM users WHERE user_id = ?", ("user_to_delete",))
        conn.commit()

        # Verify user is gone
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", ("user_to_delete",))
        user_count_after = cursor.fetchone()[0]
        assert user_count_after == 0

        # Verify device identity still exists
        device_id_after = get_device_identity(conn)
        assert device_id_after is not None, "Device identity should survive user deletion"
        assert device_id_after == device_id, "Device identity should be unchanged"

        conn.close()


# ==================== Migration Idempotency Tests ====================

def test_migrations_are_idempotent():
    """
    Test that migrations can be run multiple times safely.

    This is critical for update safety:
    - Updates may fail and need to retry
    - Running migrations twice should not cause errors
    - No duplicate entries or corrupted data

    Verifies:
    1. Run all auth migrations
    2. Run them again
    3. No errors occur
    4. Data is unchanged
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"

        # First run: Run all migrations
        conn = sqlite3.connect(str(db_path))
        run_auth_migrations(conn)

        # Create device identity
        device_id_1 = ensure_device_identity(conn)
        assert device_id_1 is not None

        # Close and reopen connection to simulate restart
        conn.close()

        # Second run: Run migrations again
        conn = sqlite3.connect(str(db_path))
        run_auth_migrations(conn)  # Should not raise

        # Ensure device identity again
        device_id_2 = ensure_device_identity(conn)
        assert device_id_2 is not None

        # Verify device ID is the same
        assert device_id_1 == device_id_2, "Device ID should be stable across migration reruns"

        # Verify only one device_identity row exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM device_identity")
        device_count = cursor.fetchone()[0]
        assert device_count == 1, "Should have exactly one device identity row"

        conn.close()


def test_device_identity_migration_is_idempotent():
    """
    Test that device_identity migration can run multiple times.

    Specifically tests migration 0003:
    - CREATE TABLE IF NOT EXISTS ensures no errors on re-run
    - No duplicate rows created
    - Indexes don't cause conflicts

    This is the most direct test of migration safety.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db_path))

        # Setup migration tracking
        from api.migrations.auth import runner
        runner._ensure_migration_table(conn)

        # Import migration
        import importlib
        migration_0003 = importlib.import_module(".0003_device_identity", package="api.migrations.auth")

        # Run migration first time
        migration_0003.apply_migration(conn)

        # Verify table exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='device_identity'
        """)
        assert cursor.fetchone() is not None

        # Run migration second time (should not error)
        migration_0003.apply_migration(conn)

        # Verify still only one table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='device_identity'
        """)
        result = cursor.fetchone()
        assert result is not None

        conn.close()


# ==================== Update Simulation Tests ====================

def test_complete_update_flow():
    """
    Test complete update flow from old to new schema.

    This is the most comprehensive test:
    1. Start with old schema (before AUTH-P6)
    2. Create users and data
    3. Simulate update (run new migrations)
    4. Verify all data survives
    5. Verify new features work (device identity)

    This simulates a real-world update scenario.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"

        # === OLD SCHEMA (before AUTH-P6) ===
        conn = sqlite3.connect(str(db_path))
        from api.migrations.auth import runner
        runner._ensure_migration_table(conn)

        # Run migrations 0001 and 0002 only (old schema)
        import importlib
        migration_0001 = importlib.import_module(".0001_initial", package="api.migrations.auth")
        migration_0002 = importlib.import_module(".0002_founder_role", package="api.migrations.auth")

        migration_0001.apply_migration(conn)
        runner._record_migration(conn, "auth_0001_initial", "Initial schema")
        migration_0002.apply_migration(conn)
        runner._record_migration(conn, "auth_0002_founder_role", "Founder role")

        # Create test users
        cursor = conn.cursor()
        users = [
            ("user_1", "alice", "admin"),
            ("user_2", "bob", "member"),
            ("user_3", "charlie", "guest"),
        ]

        for user_id, username, role in users:
            cursor.execute("""
                INSERT INTO users (user_id, username, password_hash, device_id, created_at, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, f"hash_{username}", f"device_{user_id}", datetime.now(UTC).isoformat(), role))

        conn.commit()

        # Verify users exist before update
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count_before = cursor.fetchone()[0]
        assert user_count_before == 3

        conn.close()

        # === SIMULATE UPDATE ===
        conn = sqlite3.connect(str(db_path))

        # Run NEW migrations (includes 0003_device_identity)
        run_auth_migrations(conn)

        # Ensure device identity (new feature)
        device_id = ensure_device_identity(conn)
        assert device_id is not None

        # === VERIFY DATA SURVIVED ===
        cursor = conn.cursor()

        # All users should still exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count_after = cursor.fetchone()[0]
        assert user_count_after == 3, "All users should survive update"

        # Verify each user
        for user_id, username, role in users:
            cursor.execute("""
                SELECT username, role FROM users WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            assert row is not None, f"User {user_id} should exist after update"
            assert row[0] == username, f"Username for {user_id} should be unchanged"
            assert row[1] == role, f"Role for {user_id} should be unchanged"

        # Verify new feature works (device identity)
        cursor.execute("SELECT COUNT(*) FROM device_identity")
        device_count = cursor.fetchone()[0]
        assert device_count == 1, "Device identity should be created during update"

        conn.close()
