#!/usr/bin/env python3
"""
Stress test for audit logging system
Tests logging, querying, filtering, CSV export, and cleanup
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import csv

# Add backend API to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/backend/api'))

from audit_logger import AuditLogger, AuditAction, audit_log_sync


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

    def assert_greater_than(self, actual, expected, message):
        if actual > expected:
            self.passed += 1
            print(f"✓ {message}")
        else:
            self.failed += 1
            self.errors.append(f"{message} - Expected > {expected}, Got: {actual}")
            print(f"✗ {message} - Expected > {expected}, Got: {actual}")

    def summary(self):
        print("\n" + "="*60)
        print(f"Test Results: {self.passed} passed, {self.failed} failed")
        if self.failed > 0:
            print("\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print("="*60)
        return self.failed == 0


def main():
    results = TestResults()

    # Create temp directory for test
    test_dir = Path(tempfile.mkdtemp(prefix="audit_test_"))
    audit_db_path = test_dir / "audit.db"

    print(f"Test directory: {test_dir}")

    try:
        print("\n=== Test 1: Initialize Audit Logger ===")
        audit_logger = AuditLogger(db_path=audit_db_path)

        results.assert_true(audit_db_path.exists(), "Audit database created")

        # Verify schema
        conn = sqlite3.connect(str(audit_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        results.assert_true("audit_log" in tables, "audit_log table exists")

        print("\n=== Test 2: Log Basic Audit Entry ===")
        audit_id = audit_logger.log(
            user_id="user-123",
            action=AuditAction.USER_LOGIN,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )

        results.assert_true(audit_id > 0, f"Audit entry created (ID: {audit_id})")

        # Verify entry was stored
        logs = audit_logger.get_logs(limit=1)
        results.assert_equals(len(logs), 1, "One audit log retrieved")
        results.assert_equals(logs[0].user_id, "user-123", "Correct user_id")
        results.assert_equals(logs[0].action, AuditAction.USER_LOGIN, "Correct action")
        results.assert_equals(logs[0].ip_address, "192.168.1.100", "Correct IP address")

        print("\n=== Test 3: Log Entry with Resource ===")
        audit_id = audit_logger.log(
            user_id="user-456",
            action=AuditAction.WORKFLOW_DELETED,
            resource="workflow",
            resource_id="wf-789",
            ip_address="10.0.0.5"
        )

        results.assert_true(audit_id > 0, "Audit entry with resource created")

        logs = audit_logger.get_logs(user_id="user-456")
        results.assert_equals(len(logs), 1, "One log for user-456")
        results.assert_equals(logs[0].resource, "workflow", "Correct resource")
        results.assert_equals(logs[0].resource_id, "wf-789", "Correct resource_id")

        print("\n=== Test 4: Log Entry with Details ===")
        details = {
            "workflow_name": "Test Workflow",
            "field_count": 5,
            "deleted_reason": "Test cleanup"
        }

        audit_id = audit_logger.log(
            user_id="user-789",
            action=AuditAction.WORKFLOW_DELETED,
            resource="workflow",
            resource_id="wf-999",
            details=details
        )

        results.assert_true(audit_id > 0, "Audit entry with details created")

        logs = audit_logger.get_logs(user_id="user-789")
        results.assert_equals(len(logs), 1, "One log for user-789")
        results.assert_true(logs[0].details is not None, "Details stored")
        results.assert_equals(logs[0].details["workflow_name"], "Test Workflow", "Correct workflow_name in details")
        results.assert_equals(logs[0].details["field_count"], 5, "Correct field_count in details")

        print("\n=== Test 5: Multiple Logs ===")
        # Create 10 audit entries
        for i in range(10):
            audit_logger.log(
                user_id=f"user-{i}",
                action=AuditAction.VAULT_ACCESSED,
                resource="vault",
                resource_id=f"vault-{i}"
            )

        logs = audit_logger.get_logs(action=AuditAction.VAULT_ACCESSED)
        results.assert_equals(len(logs), 10, "10 vault access logs created")

        print("\n=== Test 6: Filter by Action ===")
        # Add different action types
        audit_logger.log(user_id="user-filter", action=AuditAction.USER_LOGIN)
        audit_logger.log(user_id="user-filter", action=AuditAction.VAULT_ACCESSED)
        audit_logger.log(user_id="user-filter", action=AuditAction.WORKFLOW_CREATED)

        login_logs = audit_logger.get_logs(action=AuditAction.USER_LOGIN)
        results.assert_greater_than(len(login_logs), 0, "Login logs found")

        vault_logs = audit_logger.get_logs(action=AuditAction.VAULT_ACCESSED)
        results.assert_greater_than(len(vault_logs), 10, "Vault access logs found (>10)")

        print("\n=== Test 7: Filter by User ===")
        user_logs = audit_logger.get_logs(user_id="user-filter")
        results.assert_equals(len(user_logs), 3, "3 logs for user-filter")

        print("\n=== Test 8: Filter by Resource ===")
        resource_logs = audit_logger.get_logs(resource="workflow")
        results.assert_greater_than(len(resource_logs), 0, "Workflow resource logs found")

        print("\n=== Test 9: Count Logs ===")
        total_count = audit_logger.count_logs()
        results.assert_greater_than(total_count, 15, f"Total log count > 15 ({total_count})")

        user_count = audit_logger.count_logs(user_id="user-filter")
        results.assert_equals(user_count, 3, "Correct count for user-filter")

        action_count = audit_logger.count_logs(action=AuditAction.VAULT_ACCESSED)
        results.assert_equals(action_count, 11, "Correct count for vault access")

        print("\n=== Test 10: Pagination ===")
        # Create more logs
        for i in range(50):
            audit_logger.log(
                user_id="pagination-user",
                action=AuditAction.WORKFLOW_VIEWED,
                resource="workflow",
                resource_id=f"wf-page-{i}"
            )

        page1 = audit_logger.get_logs(user_id="pagination-user", limit=10, offset=0)
        page2 = audit_logger.get_logs(user_id="pagination-user", limit=10, offset=10)
        page3 = audit_logger.get_logs(user_id="pagination-user", limit=10, offset=20)

        results.assert_equals(len(page1), 10, "Page 1 has 10 logs")
        results.assert_equals(len(page2), 10, "Page 2 has 10 logs")
        results.assert_equals(len(page3), 10, "Page 3 has 10 logs")

        # Verify pages have different IDs
        page1_ids = {log.id for log in page1}
        page2_ids = {log.id for log in page2}
        results.assert_equals(len(page1_ids & page2_ids), 0, "Pages don't overlap")

        print("\n=== Test 11: Date Filtering ===")
        # Create log with specific timestamp
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        audit_logger.log(
            user_id="date-filter-user",
            action=AuditAction.BACKUP_CREATED
        )

        # Filter by date range
        recent_logs = audit_logger.get_logs(
            user_id="date-filter-user",
            start_date=yesterday,
            end_date=tomorrow
        )

        results.assert_equals(len(recent_logs), 1, "One log in date range")

        # Filter with narrow date range (should get nothing)
        old_logs = audit_logger.get_logs(
            user_id="date-filter-user",
            start_date=yesterday - timedelta(days=10),
            end_date=yesterday
        )

        results.assert_equals(len(old_logs), 0, "No logs in old date range")

        print("\n=== Test 12: Cleanup Old Logs ===")
        # Manually insert old log into database
        conn = sqlite3.connect(str(audit_db_path))
        cursor = conn.cursor()

        old_timestamp = (datetime.utcnow() - timedelta(days=95)).isoformat()
        cursor.execute("""
            INSERT INTO audit_log
            (user_id, action, timestamp)
            VALUES (?, ?, ?)
        """, ("old-user", AuditAction.USER_LOGIN, old_timestamp))

        conn.commit()
        conn.close()

        # Verify old log exists
        old_log_count = audit_logger.count_logs(user_id="old-user")
        results.assert_equals(old_log_count, 1, "Old log exists before cleanup")

        # Cleanup logs older than 90 days
        deleted = audit_logger.cleanup_old_logs(retention_days=90)
        results.assert_greater_than(deleted, 0, f"Deleted old logs ({deleted})")

        # Verify old log was deleted
        old_log_count_after = audit_logger.count_logs(user_id="old-user")
        results.assert_equals(old_log_count_after, 0, "Old log deleted after cleanup")

        print("\n=== Test 13: CSV Export ===")
        csv_path = test_dir / "audit_export.csv"

        # Create some test logs
        for i in range(5):
            audit_logger.log(
                user_id=f"export-user-{i}",
                action=AuditAction.FILE_UPLOADED,
                resource="file",
                resource_id=f"file-{i}.txt",
                details={"size": i * 1024}
            )

        success = audit_logger.export_to_csv(csv_path)
        results.assert_true(success, "CSV export succeeded")
        results.assert_true(csv_path.exists(), "CSV file created")

        # Verify CSV contents
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        results.assert_greater_than(len(rows), 5, f"CSV has >5 rows ({len(rows)})")

        # Check CSV headers
        expected_headers = [
            'id', 'user_id', 'action', 'resource', 'resource_id',
            'ip_address', 'user_agent', 'timestamp', 'details'
        ]
        actual_headers = list(rows[0].keys())
        results.assert_equals(actual_headers, expected_headers, "CSV has correct headers")

        print("\n=== Test 14: Synchronous Logging ===")
        # Test direct logging (sync)
        audit_logger.log(
            user_id="sync-user",
            action=AuditAction.PANIC_MODE_ACTIVATED,
            resource="security",
            details={"reason": "Test"}
        )

        sync_logs = audit_logger.get_logs(user_id="sync-user")
        results.assert_equals(len(sync_logs), 1, "Sync log created")
        results.assert_equals(sync_logs[0].action, AuditAction.PANIC_MODE_ACTIVATED, "Correct action")

        print("\n=== Test 15: High Volume Logging ===")
        import time

        start_time = time.time()

        # Create 1000 logs
        for i in range(1000):
            audit_logger.log(
                user_id=f"bulk-user-{i % 10}",
                action=AuditAction.WORKFLOW_VIEWED,
                resource="workflow",
                resource_id=f"wf-bulk-{i}"
            )

        end_time = time.time()
        duration = end_time - start_time

        results.assert_true(duration < 5.0, f"1000 logs created in < 5s ({duration:.2f}s)")

        bulk_count = audit_logger.count_logs(action=AuditAction.WORKFLOW_VIEWED)
        results.assert_greater_than(bulk_count, 1000, f"Bulk logs counted ({bulk_count})")

        print(f"Logging rate: {1000 / duration:.0f} logs/second")

        print("\n=== Test 16: Indexes Performance ===")
        # Query by indexed field (should be fast)
        start_time = time.time()
        indexed_logs = audit_logger.get_logs(user_id="bulk-user-5", limit=100)
        indexed_duration = time.time() - start_time

        results.assert_true(indexed_duration < 0.1, f"Indexed query fast ({indexed_duration:.3f}s)")
        results.assert_greater_than(len(indexed_logs), 0, "Indexed query returned results")

    finally:
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
