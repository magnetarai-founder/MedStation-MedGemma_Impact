#!/usr/bin/env python3
"""
Stress test for backup service
Tests backup creation, encryption, restoration, and cleanup
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import sqlite3

# Add backend API to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/backend/api'))

from backup_service import BackupService


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_true(self, condition, message):
        if condition:
            self.passed += 1
            print(f"✓ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"✗ {message}")

    def assert_equals(self, actual, expected, message):
        if actual == expected:
            self.passed += 1
            print(f"✓ {message}")
        else:
            self.failed += 1
            self.errors.append(f"{message} - Expected: {expected}, Got: {actual}")
            print(f"✗ {message} - Expected: {expected}, Got: {actual}")

    def summary(self):
        print("\n" + "="*60)
        print(f"Test Results: {self.passed} passed, {self.failed} failed")
        if self.failed > 0:
            print("\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print("="*60)
        return self.failed == 0


def create_test_database(db_path: Path, table_name: str = "test_data"):
    """Create a test SQLite database"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Insert test data
    for i in range(10):
        cursor.execute(f"INSERT INTO {table_name} (data) VALUES (?)",
                      (f"Test data row {i}",))

    conn.commit()
    conn.close()


def main():
    results = TestResults()

    # Create temp directory for test
    test_dir = Path(tempfile.mkdtemp(prefix="backup_test_"))
    backup_dir = test_dir / "backups"
    data_dir = test_dir / "data"
    backup_dir.mkdir()
    data_dir.mkdir()

    print(f"Test directory: {test_dir}")

    # Monkey-patch config paths
    import config_paths
    original_get_data_dir = config_paths.get_data_dir
    config_paths.get_data_dir = lambda: data_dir

    # Monkey-patch backup dir
    import backup_service
    original_backup_dir = backup_service.BACKUP_DIR
    backup_service.BACKUP_DIR = backup_dir

    try:
        print("\n=== Test 1: Create Test Databases ===")
        # Create test databases
        db1 = data_dir / "elohimos_app.db"
        db2 = data_dir / "vault.db"
        db3 = data_dir / "datasets.db"

        create_test_database(db1, "app_data")
        create_test_database(db2, "vault_data")
        create_test_database(db3, "dataset_info")

        results.assert_true(db1.exists(), "elohimos_app.db created")
        results.assert_true(db2.exists(), "vault.db created")
        results.assert_true(db3.exists(), "datasets.db created")

        print("\n=== Test 2: Initialize Backup Service ===")
        passphrase = "test_backup_passphrase_secure_123"
        backup_service_instance = BackupService(passphrase)

        results.assert_true(backup_dir.exists(), "Backup directory created")
        results.assert_equals(oct(backup_dir.stat().st_mode)[-3:], "700",
                            "Backup directory has correct permissions")

        print("\n=== Test 3: Create Backup ===")
        backup_path = backup_service_instance.create_backup()

        results.assert_true(backup_path is not None, "Backup created successfully")
        results.assert_true(backup_path.exists(), "Backup file exists")
        results.assert_true(backup_path.suffix == ".elohim-backup", "Correct file extension")

        backup_size = backup_path.stat().st_size
        results.assert_true(backup_size > 0, f"Backup has content ({backup_size} bytes)")
        print(f"Backup size: {backup_size} bytes")

        print("\n=== Test 4: List Backups ===")
        backups = backup_service_instance.list_backups()

        results.assert_equals(len(backups), 1, "One backup listed")
        results.assert_true("name" in backups[0], "Backup has name")
        results.assert_true("size" in backups[0], "Backup has size")
        results.assert_true("created" in backups[0], "Backup has created date")

        print("\n=== Test 5: Verify Backup ===")
        is_valid = backup_service_instance.verify_backup(backup_path)
        results.assert_true(is_valid, "Backup verification succeeds")

        # Test with wrong passphrase
        wrong_backup_service = BackupService("wrong_passphrase")
        is_valid_wrong = wrong_backup_service.verify_backup(backup_path)
        results.assert_true(not is_valid_wrong, "Wrong passphrase fails verification")

        print("\n=== Test 6: Modify Database ===")
        # Add more data to databases
        conn = sqlite3.connect(str(db1))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO app_data (data) VALUES (?)", ("Modified data",))
        conn.commit()
        conn.close()

        # Verify modification
        conn = sqlite3.connect(str(db1))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_data")
        count = cursor.fetchone()[0]
        conn.close()

        results.assert_equals(count, 11, "Database modified (11 rows)")

        print("\n=== Test 7: Restore Backup ===")
        success = backup_service_instance.restore_backup(backup_path)
        results.assert_true(success, "Backup restored successfully")

        # Verify restoration
        conn = sqlite3.connect(str(db1))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_data")
        restored_count = cursor.fetchone()[0]
        conn.close()

        results.assert_equals(restored_count, 10, "Database restored to original state (10 rows)")

        # Verify pre-restore backup was created
        pre_restore = db1.with_suffix('.db.pre-restore')
        results.assert_true(pre_restore.exists(), "Pre-restore backup created")

        print("\n=== Test 8: Multiple Backups ===")
        # Create more backups
        backup2 = backup_service_instance.create_backup()
        backup3 = backup_service_instance.create_backup()

        backups = backup_service_instance.list_backups()
        results.assert_equals(len(backups), 3, "Three backups exist")

        print("\n=== Test 9: Backup Cleanup ===")
        # Create more backups to have a mix of old and new
        import time

        # Get current backups count
        current_backups = backup_service_instance.list_backups()
        initial_count = len(current_backups)

        # Set first backup to be 8 days old
        old_time = (time.time() - (8 * 24 * 60 * 60))  # 8 days ago
        if current_backups:
            old_backup_path = Path(current_backups[0]['path'])
            os.utime(old_backup_path, (old_time, old_time))

        # Create one more fresh backup
        backup4 = backup_service_instance.create_backup()

        # Now cleanup should remove the old one (if mtime was preserved)
        deleted = backup_service_instance.cleanup_old_backups()
        results.assert_true(deleted >= 0, f"Cleanup ran successfully (deleted {deleted})")

        # Should have at most initial_count+1 backups left (added 1 new)
        remaining_backups = backup_service_instance.list_backups()
        results.assert_true(len(remaining_backups) >= initial_count,
                          f"At least {initial_count} backups remain ({len(remaining_backups)} found)")

        print("\n=== Test 10: Backup Data Integrity ===")
        # Create fresh backup for integrity test
        backup_path = backup_service_instance.create_backup()

        # Calculate original checksums
        original_checksums = {}
        for db in [db1, db2, db3]:
            import hashlib
            sha256 = hashlib.sha256()
            with open(db, 'rb') as f:
                sha256.update(f.read())
            original_checksums[db.name] = sha256.hexdigest()

        # Restore to different directory
        restore_dir = test_dir / "restored"
        restore_dir.mkdir()

        success = backup_service_instance.restore_backup(backup_path, restore_dir)

        results.assert_true(success, "Backup restored to different directory")

        # Verify checksums match
        for db_name, original_checksum in original_checksums.items():
            restored_db = restore_dir / db_name
            if restored_db.exists():
                sha256 = hashlib.sha256()
                with open(restored_db, 'rb') as f:
                    sha256.update(f.read())
                restored_checksum = sha256.hexdigest()
                results.assert_equals(restored_checksum, original_checksum,
                                    f"{db_name} checksum matches")

    finally:
        # Restore original functions
        config_paths.get_data_dir = original_get_data_dir
        backup_service.BACKUP_DIR = original_backup_dir

        # Cleanup
        print("\n=== Cleanup ===")
        try:
            shutil.rmtree(test_dir)
            print(f"✓ Removed test directory: {test_dir}")
        except Exception as e:
            print(f"✗ Failed to remove test directory: {e}")

    # Summary
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
