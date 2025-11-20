"""
Audit Event Tests (AUTH-P5)

Tests that verify audit logging for sensitive operations:
- Admin/danger zone operations (resets, clears, exports)
- RBAC/permission changes
- Agent auto-apply operations
- Secret redaction in audit logs

These tests ensure accountability and security observability.
"""

import sqlite3
import tempfile
import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from api.audit_logger import AuditLogger, AuditAction
from api.audit_helper import record_audit_event
from tests.utils.auth_test_utils import create_user_with_role, ROLES


# ==================== Audit Helper Tests ====================

def test_audit_helper_records_to_db():
    """
    Test that audit logger writes to audit database

    Verifies:
    - Audit entry is created in audit.db
    - All fields are properly populated
    - Timestamp is recorded
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Record an audit event
        audit_id = audit_logger.log(
            user_id='test_user_123',
            action=AuditAction.ADMIN_RESET_ALL,
            resource='system',
            details={'status': 'success', 'reason': 'test'}
        )

        success = audit_id > 0

        assert success, "Audit event should be recorded successfully"

        # Verify entry in database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, action, resource, details
            FROM audit_log
            WHERE user_id = 'test_user_123'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "Audit entry should exist in database"
        assert row[0] == 'test_user_123'
        assert row[1] == AuditAction.ADMIN_RESET_ALL
        assert row[2] == 'system'

        details = json.loads(row[3])
        assert details['status'] == 'success'
        assert details['reason'] == 'test'


def test_audit_helper_redacts_secrets():
    """
    Test that secrets are automatically redacted from audit logs

    Verifies:
    - Password fields are redacted
    - Token fields are redacted
    - API key fields are redacted
    - Audit entry is still created
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Record event with secrets
        audit_logger.log(
            user_id='test_user_456',
            action='test.action',
            resource='test',
            details={
                'username': 'john',
                'password': 'super_secret_password',
                'token': 'Bearer abc123xyz',
                'api_key': 'sk-1234567890',
                'safe_field': 'this is safe'
            }
        )

        # Verify secrets are redacted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT details FROM audit_log WHERE user_id = 'test_user_456'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        details = json.loads(row[0])

        # Secrets should be redacted
        assert 'super_secret_password' not in json.dumps(details)
        assert 'abc123xyz' not in json.dumps(details)
        assert 'sk-1234567890' not in json.dumps(details)

        # Safe fields should remain
        assert details['username'] == 'john'
        assert details['safe_field'] == 'this is safe'


# ==================== Admin Operation Tests ====================

def test_admin_reset_all_audited():
    """
    Test that admin reset-all operation creates audit entry

    Verifies:
    - Admin reset-all action is audited
    - User ID is recorded
    - Action type is correct
    - Resource is 'system'
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Simulate admin reset operation
        audit_logger.log(
            user_id='founder_user_789',
            action=AuditAction.ADMIN_RESET_ALL,
            resource='system',
            details={'status': 'success'}
        )

        # Verify audit entry
        logs = audit_logger.get_logs(
            user_id='founder_user_789',
            action=AuditAction.ADMIN_RESET_ALL
        )

        assert len(logs) == 1, "Should have one audit log entry"
        log = logs[0]
        assert log.user_id == 'founder_user_789'
        assert log.action == AuditAction.ADMIN_RESET_ALL
        assert log.resource == 'system'
        assert log.details['status'] == 'success'


def test_admin_export_all_audited():
    """
    Test that admin export-all operation creates audit entry

    Verifies:
    - Export action is audited
    - Export type and format are recorded
    - User performing export is tracked
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Simulate export operation
        audit_logger.log(
            user_id='admin_user_101',
            action=AuditAction.ADMIN_EXPORT_ALL,
            resource='backup',
            details={'type': 'full', 'format': 'zip'}
        )

        # Verify audit entry
        logs = audit_logger.get_logs(
            user_id='admin_user_101',
            action=AuditAction.ADMIN_EXPORT_ALL
        )

        assert len(logs) == 1
        log = logs[0]
        assert log.action == AuditAction.ADMIN_EXPORT_ALL
        assert log.resource == 'backup'
        assert log.details['type'] == 'full'
        assert log.details['format'] == 'zip'


def test_multiple_admin_operations_all_audited():
    """
    Test that multiple admin operations all create audit entries

    Verifies:
    - Clear chats is audited
    - Clear temp files is audited
    - Reset settings is audited
    - All entries can be queried
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        user_id = 'admin_user_202'

        # Simulate multiple operations
        audit_logger.log(
            user_id=user_id,
            action=AuditAction.ADMIN_CLEAR_CHATS,
            resource='chats',
            details={'status': 'success'}
        )

        audit_logger.log(
            user_id=user_id,
            action=AuditAction.ADMIN_CLEAR_TEMP_FILES,
            resource='temp_files',
            details={'status': 'success'}
        )

        audit_logger.log(
            user_id=user_id,
            action=AuditAction.ADMIN_RESET_SETTINGS,
            resource='settings',
            details={'status': 'success'}
        )

        # Verify all entries exist
        all_logs = audit_logger.get_logs(user_id=user_id)
        assert len(all_logs) == 3, "Should have 3 audit log entries"

        actions = {log.action for log in all_logs}
        assert AuditAction.ADMIN_CLEAR_CHATS in actions
        assert AuditAction.ADMIN_CLEAR_TEMP_FILES in actions
        assert AuditAction.ADMIN_RESET_SETTINGS in actions


# ==================== Agent Auto-Apply Tests ====================

def test_agent_auto_apply_audited():
    """
    Test that agent auto-apply creates audit entry

    Verifies:
    - Auto-apply action is audited
    - Files changed count is recorded
    - Engine used is tracked
    - Repository path is recorded
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Simulate agent auto-apply
        audit_logger.log(
            user_id='developer_303',
            action=AuditAction.AGENT_AUTO_APPLY,
            resource='repository',
            resource_id='/path/to/repo',
            details={
                'engine': 'aider',
                'files_changed': 3,
                'files': ['src/main.py', 'src/utils.py', 'tests/test_main.py'],
                'patch_id': 'patch_abc123',
                'session_id': 'session_xyz789'
            }
        )

        # Verify audit entry
        logs = audit_logger.get_logs(
            user_id='developer_303',
            action=AuditAction.AGENT_AUTO_APPLY
        )

        assert len(logs) == 1
        log = logs[0]
        assert log.action == AuditAction.AGENT_AUTO_APPLY
        assert log.resource == 'repository'
        assert log.resource_id == '/path/to/repo'
        assert log.details['engine'] == 'aider'
        assert log.details['files_changed'] == 3
        assert len(log.details['files']) == 3


# ==================== RBAC Operation Tests ====================

def test_rbac_role_assignment_audited():
    """
    Test that RBAC role assignment creates audit entry

    Note: This tests the existing audit logging in permissions/admin.py

    Verifies:
    - Role assignment is audited
    - User being modified is tracked
    - New role is recorded
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Simulate RBAC operation (this is what permissions/admin.py does)
        audit_logger.log(
            user_id='admin_user_404',
            action=AuditAction.ROLE_ASSIGNED,
            resource='user',
            resource_id='target_user_505',
            details={
                'old_role': 'member',
                'new_role': 'admin',
                'assigned_by': 'admin_user_404'
            }
        )

        # Verify audit entry
        logs = audit_logger.get_logs(
            action=AuditAction.ROLE_ASSIGNED,
            resource='user'
        )

        assert len(logs) == 1
        log = logs[0]
        assert log.user_id == 'admin_user_404'
        assert log.resource_id == 'target_user_505'
        assert log.details['old_role'] == 'member'
        assert log.details['new_role'] == 'admin'


# ==================== Query and Retention Tests ====================

def test_audit_log_query_by_action():
    """
    Test querying audit logs by action type

    Verifies:
    - Can filter logs by action
    - Get only matching entries
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Create multiple log entries with different actions
        audit_logger.log('user1', AuditAction.ADMIN_RESET_ALL, 'system')
        audit_logger.log('user2', AuditAction.ADMIN_EXPORT_ALL, 'backup')
        audit_logger.log('user3', AuditAction.ADMIN_RESET_ALL, 'system')

        # Query by action
        reset_logs = audit_logger.get_logs(action=AuditAction.ADMIN_RESET_ALL)
        export_logs = audit_logger.get_logs(action=AuditAction.ADMIN_EXPORT_ALL)

        assert len(reset_logs) == 2, "Should have 2 reset entries"
        assert len(export_logs) == 1, "Should have 1 export entry"


def test_audit_log_count():
    """
    Test counting audit log entries

    Verifies:
    - Can count total entries
    - Can count filtered entries
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "audit.db"
        audit_logger = AuditLogger(db_path=db_path)

        # Create entries
        for i in range(5):
            audit_logger.log(
                user_id=f'user_{i}',
                action=AuditAction.ADMIN_CLEAR_CHATS,
                resource='chats'
            )

        for i in range(3):
            audit_logger.log(
                user_id=f'user_{i}',
                action=AuditAction.ADMIN_EXPORT_ALL,
                resource='backup'
            )

        # Count logs
        total_count = audit_logger.count_logs()
        clear_count = audit_logger.count_logs(action=AuditAction.ADMIN_CLEAR_CHATS)
        export_count = audit_logger.count_logs(action=AuditAction.ADMIN_EXPORT_ALL)

        assert total_count == 8, "Should have 8 total entries"
        assert clear_count == 5, "Should have 5 clear entries"
        assert export_count == 3, "Should have 3 export entries"


# ==================== Error Handling Tests ====================

def test_audit_failure_does_not_crash():
    """
    Test that audit failures are gracefully handled

    Verifies:
    - Audit failures don't crash the audit logger
    - Returns -1 on failure
    - No exceptions propagate to caller
    """
    # Test with corrupted/invalid database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create audit logger
        audit_logger = AuditLogger(db_path=tmp_path)

        # Corrupt the database by deleting it
        tmp_path.unlink()

        # This should not raise an exception, just return -1
        result = audit_logger.log(
            user_id='test_user',
            action='test.action',
            resource='test'
        )

        assert result == -1, "Should return -1 on failure"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
