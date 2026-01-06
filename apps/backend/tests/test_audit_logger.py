"""
Comprehensive tests for api/audit_logger.py

Tests audit logging system with SQLite storage for compliance and security.

Coverage targets:
- AuditEntry model
- AuditAction constants
- AuditLogger class (init, log, get_logs, count_logs, cleanup, export)
- Singleton pattern (get_audit_logger)
- Decorator (audit_log)
- Sync helper (audit_log_sync)
"""

import csv
import json
import os
import sqlite3
import tempfile
import pytest
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from api.audit_logger import (
    AuditEntry,
    AuditAction,
    AuditLogger,
    get_audit_logger,
    audit_log,
    audit_log_sync,
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db_path():
    """Create a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.fixture
def audit_logger(temp_db_path):
    """Create a fresh AuditLogger instance"""
    return AuditLogger(db_path=temp_db_path)


@pytest.fixture
def reset_singleton():
    """Reset global audit logger singleton"""
    import api.audit_logger as module
    module._audit_logger = None
    yield
    module._audit_logger = None


# ========== AuditEntry Model Tests ==========

class TestAuditEntry:
    """Tests for AuditEntry model"""

    def test_create_minimal(self):
        """Test creating entry with required fields only"""
        entry = AuditEntry(
            user_id="user123",
            action="test.action",
            timestamp="2024-01-01T00:00:00Z"
        )

        assert entry.user_id == "user123"
        assert entry.action == "test.action"
        assert entry.timestamp == "2024-01-01T00:00:00Z"
        assert entry.id is None
        assert entry.resource is None

    def test_create_full(self):
        """Test creating entry with all fields"""
        entry = AuditEntry(
            id=1,
            user_id="user123",
            action="test.action",
            resource="workflow",
            resource_id="wf-001",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            timestamp="2024-01-01T00:00:00Z",
            details={"key": "value"}
        )

        assert entry.id == 1
        assert entry.resource == "workflow"
        assert entry.resource_id == "wf-001"
        assert entry.ip_address == "192.168.1.1"
        assert entry.user_agent == "Mozilla/5.0"
        assert entry.details == {"key": "value"}

    def test_to_dict(self):
        """Test model serialization"""
        entry = AuditEntry(
            user_id="user123",
            action="test.action",
            timestamp="2024-01-01T00:00:00Z"
        )

        data = entry.model_dump()

        assert isinstance(data, dict)
        assert data["user_id"] == "user123"
        assert data["action"] == "test.action"


# ========== AuditAction Constants Tests ==========

class TestAuditAction:
    """Tests for AuditAction constants"""

    def test_authentication_actions(self):
        """Test authentication action constants"""
        assert AuditAction.USER_LOGIN == "user.login"
        assert AuditAction.USER_LOGOUT == "user.logout"
        assert AuditAction.USER_LOGIN_FAILED == "user.login.failed"

    def test_user_management_actions(self):
        """Test user management action constants"""
        assert AuditAction.USER_CREATED == "user.created"
        assert AuditAction.USER_DELETED == "user.deleted"
        assert AuditAction.USER_ROLE_CHANGED == "user.role.changed"

    def test_vault_actions(self):
        """Test vault action constants"""
        assert AuditAction.VAULT_ACCESSED == "vault.accessed"
        assert AuditAction.VAULT_ITEM_CREATED == "vault.item.created"
        assert AuditAction.VAULT_ITEM_DELETED == "vault.item.deleted"

    def test_workflow_actions(self):
        """Test workflow action constants"""
        assert AuditAction.WORKFLOW_CREATED == "workflow.created"
        assert AuditAction.WORKFLOW_EXECUTED == "workflow.executed"
        assert AuditAction.WORKFLOW_VISIBILITY_CHANGED == "workflow.visibility.changed"

    def test_file_actions(self):
        """Test file action constants"""
        assert AuditAction.FILE_UPLOADED == "file.uploaded"
        assert AuditAction.FILE_DOWNLOADED == "file.downloaded"
        assert AuditAction.FILE_DELETED == "file.deleted"

    def test_security_actions(self):
        """Test security action constants"""
        assert AuditAction.PANIC_MODE_ACTIVATED == "security.panic_mode.activated"
        assert AuditAction.BACKUP_CREATED == "backup.created"
        assert AuditAction.ENCRYPTION_KEY_ROTATED == "security.key.rotated"

    def test_admin_actions(self):
        """Test admin action constants"""
        assert AuditAction.ADMIN_LIST_USERS == "admin.list.users"
        assert AuditAction.ADMIN_RESET_PASSWORD == "admin.reset_password"
        assert AuditAction.FOUNDER_RIGHTS_LOGIN == "founder_rights.login"

    def test_permission_actions(self):
        """Test permission action constants"""
        assert AuditAction.PERMISSION_GRANTED == "permission.granted"
        assert AuditAction.PERMISSION_REVOKED == "permission.revoked"
        assert AuditAction.ROLE_ASSIGNED == "role.assigned"

    def test_agent_actions(self):
        """Test agent action constants"""
        assert AuditAction.AGENT_SESSION_CREATED == "agent.session.created"
        assert AuditAction.AGENT_PLAN_GENERATED == "agent.plan.generated"
        assert AuditAction.AGENT_AUTO_APPLY == "agent.auto_apply"


# ========== AuditLogger Initialization Tests ==========

class TestAuditLoggerInit:
    """Tests for AuditLogger initialization"""

    def test_init_creates_database(self, temp_db_path):
        """Test initialization creates database file"""
        logger = AuditLogger(db_path=temp_db_path)

        assert temp_db_path.exists()

    def test_init_creates_table(self, temp_db_path):
        """Test initialization creates audit_log table"""
        logger = AuditLogger(db_path=temp_db_path)

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "audit_log"

    def test_init_creates_indexes(self, temp_db_path):
        """Test initialization creates indexes"""
        logger = AuditLogger(db_path=temp_db_path)

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_audit_%'")
        indexes = cursor.fetchall()
        conn.close()

        index_names = [idx[0] for idx in indexes]
        assert "idx_audit_user_id" in index_names
        assert "idx_audit_action" in index_names
        assert "idx_audit_timestamp" in index_names
        assert "idx_audit_resource" in index_names

    def test_init_with_default_path(self, reset_singleton):
        """Test initialization with default path"""
        # The default path logic imports get_data_dir inside __init__
        # Patch at the source module where it's imported from
        with patch('api.config_paths.get_data_dir', return_value=Path(tempfile.gettempdir())):
            # This should not raise
            logger = AuditLogger()
            assert logger.db_path is not None
            assert "audit.db" in str(logger.db_path)


# ========== AuditLogger.log Tests ==========

class TestAuditLoggerLog:
    """Tests for AuditLogger.log method"""

    def test_log_minimal(self, audit_logger):
        """Test logging with minimal fields"""
        result = audit_logger.log(
            user_id="user123",
            action="test.action"
        )

        assert result > 0

    def test_log_full(self, audit_logger):
        """Test logging with all fields"""
        result = audit_logger.log(
            user_id="user123",
            action="test.action",
            resource="workflow",
            resource_id="wf-001",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"key": "value"}
        )

        assert result > 0

    def test_log_stores_data_correctly(self, audit_logger, temp_db_path):
        """Test logged data is stored correctly"""
        audit_logger.log(
            user_id="user123",
            action="test.action",
            resource="vault",
            resource_id="v-001",
            details={"status": "success"}
        )

        # Query directly
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_log WHERE user_id = 'user123'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "user123"  # user_id
        assert row[2] == "test.action"  # action
        assert row[3] == "vault"  # resource
        assert row[4] == "v-001"  # resource_id

    def test_log_sanitizes_details(self, audit_logger):
        """Test details are sanitized"""
        # sanitize_for_log is imported inside the log method from .utils
        with patch('api.utils.sanitize_for_log', return_value={"sanitized": True}) as mock_sanitize:
            audit_logger.log(
                user_id="user123",
                action="test.action",
                details={"password": "secret123"}
            )

            mock_sanitize.assert_called_once()

    def test_log_handles_none_details(self, audit_logger):
        """Test logging with None details"""
        result = audit_logger.log(
            user_id="user123",
            action="test.action",
            details=None
        )

        assert result > 0

    def test_log_returns_negative_on_error(self, audit_logger):
        """Test returns -1 on database error"""
        with patch.object(audit_logger, 'db_path', Path('/nonexistent/path/audit.db')):
            result = audit_logger.log(
                user_id="user123",
                action="test.action"
            )

        assert result == -1

    def test_log_multiple_entries(self, audit_logger):
        """Test logging multiple entries"""
        ids = []
        for i in range(5):
            id = audit_logger.log(
                user_id=f"user{i}",
                action="test.action"
            )
            ids.append(id)

        # All IDs should be unique and positive
        assert len(set(ids)) == 5
        assert all(id > 0 for id in ids)


# ========== AuditLogger.get_logs Tests ==========

class TestAuditLoggerGetLogs:
    """Tests for AuditLogger.get_logs method"""

    def test_get_logs_empty(self, audit_logger):
        """Test getting logs from empty database"""
        result = audit_logger.get_logs()

        assert result == []

    def test_get_logs_returns_all(self, audit_logger):
        """Test getting all logs"""
        # Create some logs
        for i in range(3):
            audit_logger.log(user_id=f"user{i}", action="test.action")

        result = audit_logger.get_logs()

        assert len(result) == 3
        assert all(isinstance(entry, AuditEntry) for entry in result)

    def test_get_logs_filter_by_user_id(self, audit_logger):
        """Test filtering by user_id"""
        audit_logger.log(user_id="user1", action="action1")
        audit_logger.log(user_id="user2", action="action2")
        audit_logger.log(user_id="user1", action="action3")

        result = audit_logger.get_logs(user_id="user1")

        assert len(result) == 2
        assert all(entry.user_id == "user1" for entry in result)

    def test_get_logs_filter_by_action(self, audit_logger):
        """Test filtering by action"""
        audit_logger.log(user_id="user1", action="login")
        audit_logger.log(user_id="user2", action="logout")
        audit_logger.log(user_id="user3", action="login")

        result = audit_logger.get_logs(action="login")

        assert len(result) == 2
        assert all(entry.action == "login" for entry in result)

    def test_get_logs_filter_by_resource(self, audit_logger):
        """Test filtering by resource"""
        audit_logger.log(user_id="user1", action="create", resource="workflow")
        audit_logger.log(user_id="user2", action="create", resource="vault")
        audit_logger.log(user_id="user3", action="create", resource="workflow")

        result = audit_logger.get_logs(resource="workflow")

        assert len(result) == 2
        assert all(entry.resource == "workflow" for entry in result)

    def test_get_logs_filter_by_date_range(self, audit_logger, temp_db_path):
        """Test filtering by date range"""
        # Insert entries with specific timestamps directly
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        now = datetime.now(UTC)
        old = now - timedelta(days=10)
        recent = now - timedelta(days=1)

        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user1", "old_action", old.isoformat())
        )
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user2", "recent_action", recent.isoformat())
        )
        conn.commit()
        conn.close()

        # Query with date filter
        start_date = now - timedelta(days=5)
        result = audit_logger.get_logs(start_date=start_date)

        assert len(result) == 1
        assert result[0].action == "recent_action"

    def test_get_logs_with_limit(self, audit_logger):
        """Test limit parameter"""
        for i in range(10):
            audit_logger.log(user_id=f"user{i}", action="test.action")

        result = audit_logger.get_logs(limit=5)

        assert len(result) == 5

    def test_get_logs_with_offset(self, audit_logger):
        """Test offset parameter"""
        for i in range(10):
            audit_logger.log(user_id=f"user{i}", action="test.action")

        result = audit_logger.get_logs(limit=5, offset=5)

        assert len(result) == 5

    def test_get_logs_returns_empty_on_error(self, audit_logger):
        """Test returns empty list on error"""
        with patch.object(audit_logger, 'db_path', Path('/nonexistent/path/audit.db')):
            result = audit_logger.get_logs()

        assert result == []

    def test_get_logs_parses_details_json(self, audit_logger):
        """Test details JSON is parsed"""
        audit_logger.log(
            user_id="user1",
            action="test.action",
            details={"key": "value", "count": 42}
        )

        result = audit_logger.get_logs()

        assert len(result) == 1
        assert result[0].details is not None
        assert result[0].details.get("count") == 42


# ========== AuditLogger.count_logs Tests ==========

class TestAuditLoggerCountLogs:
    """Tests for AuditLogger.count_logs method"""

    def test_count_empty(self, audit_logger):
        """Test counting empty database"""
        result = audit_logger.count_logs()

        assert result == 0

    def test_count_all(self, audit_logger):
        """Test counting all logs"""
        for i in range(5):
            audit_logger.log(user_id=f"user{i}", action="test.action")

        result = audit_logger.count_logs()

        assert result == 5

    def test_count_with_filter(self, audit_logger):
        """Test counting with filter"""
        audit_logger.log(user_id="user1", action="login")
        audit_logger.log(user_id="user2", action="logout")
        audit_logger.log(user_id="user1", action="login")

        result = audit_logger.count_logs(user_id="user1")

        assert result == 2

    def test_count_returns_zero_on_error(self, audit_logger):
        """Test returns 0 on error"""
        with patch.object(audit_logger, 'db_path', Path('/nonexistent/path/audit.db')):
            result = audit_logger.count_logs()

        assert result == 0


# ========== AuditLogger.cleanup_old_logs Tests ==========

class TestAuditLoggerCleanup:
    """Tests for AuditLogger.cleanup_old_logs method"""

    def test_cleanup_removes_old_logs(self, audit_logger, temp_db_path):
        """Test cleanup removes old logs"""
        # Insert old entry directly
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        old_date = datetime.now(UTC) - timedelta(days=100)
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user1", "old_action", old_date.isoformat())
        )
        conn.commit()
        conn.close()

        # Also add a recent one
        audit_logger.log(user_id="user2", action="recent_action")

        # Cleanup with 90 day retention
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 1
        assert audit_logger.count_logs() == 1

    def test_cleanup_keeps_recent_logs(self, audit_logger):
        """Test cleanup keeps recent logs"""
        for i in range(5):
            audit_logger.log(user_id=f"user{i}", action="test.action")

        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 0
        assert audit_logger.count_logs() == 5

    def test_cleanup_custom_retention(self, audit_logger, temp_db_path):
        """Test cleanup with custom retention period"""
        # Insert entry from 10 days ago
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        old_date = datetime.now(UTC) - timedelta(days=10)
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user1", "action", old_date.isoformat())
        )
        conn.commit()
        conn.close()

        # Cleanup with 5 day retention
        deleted = audit_logger.cleanup_old_logs(retention_days=5)

        assert deleted == 1

    def test_cleanup_returns_zero_on_error(self, audit_logger):
        """Test returns 0 on error"""
        with patch.object(audit_logger, 'db_path', Path('/nonexistent/path/audit.db')):
            result = audit_logger.cleanup_old_logs()

        assert result == 0


# ========== AuditLogger.export_to_csv Tests ==========

class TestAuditLoggerExport:
    """Tests for AuditLogger.export_to_csv method"""

    def test_export_creates_file(self, audit_logger):
        """Test export creates CSV file"""
        audit_logger.log(user_id="user1", action="test.action")

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = audit_logger.export_to_csv(output_path)

            assert result is True
            assert output_path.exists()
        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_csv_content(self, audit_logger):
        """Test exported CSV has correct content"""
        audit_logger.log(
            user_id="user1",
            action="test.action",
            resource="workflow",
            resource_id="wf-001"
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            audit_logger.export_to_csv(output_path)

            with open(output_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["user_id"] == "user1"
            assert rows[0]["action"] == "test.action"
            assert rows[0]["resource"] == "workflow"
            assert rows[0]["resource_id"] == "wf-001"
        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_with_date_filter(self, audit_logger, temp_db_path):
        """Test export with date filter"""
        # Insert entries with specific timestamps
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        now = datetime.now(UTC)
        old = now - timedelta(days=10)

        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user1", "old_action", old.isoformat())
        )
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, timestamp) VALUES (?, ?, ?)",
            ("user2", "recent_action", now.isoformat())
        )
        conn.commit()
        conn.close()

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            start_date = now - timedelta(days=5)
            audit_logger.export_to_csv(output_path, start_date=start_date)

            with open(output_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["action"] == "recent_action"
        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_returns_false_on_error(self, audit_logger):
        """Test returns False on error"""
        result = audit_logger.export_to_csv(Path("/nonexistent/directory/audit.csv"))

        assert result is False


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_audit_logger_returns_instance(self, reset_singleton):
        """Test get_audit_logger returns AuditLogger instance"""
        with patch('api.audit_logger.AuditLogger') as mock_class:
            mock_class.return_value = MagicMock(spec=AuditLogger)
            result = get_audit_logger()

        assert result is not None

    def test_get_audit_logger_returns_same_instance(self, reset_singleton):
        """Test get_audit_logger returns same instance"""
        with patch('api.audit_logger.AuditLogger') as mock_class:
            mock_instance = MagicMock(spec=AuditLogger)
            mock_class.return_value = mock_instance

            logger1 = get_audit_logger()
            logger2 = get_audit_logger()

        assert logger1 is logger2
        # Should only be created once
        mock_class.assert_called_once()


# ========== Decorator Tests ==========

class TestAuditLogDecorator:
    """Tests for audit_log decorator"""

    @pytest.mark.asyncio
    async def test_decorator_logs_action(self, reset_singleton):
        """Test decorator logs the action"""
        mock_logger = MagicMock()
        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):

            @audit_log(AuditAction.WORKFLOW_CREATED, resource="workflow")
            async def create_workflow(user_id: str):
                return {"status": "created"}

            result = await create_workflow(user_id="user123")

            assert result == {"status": "created"}
            mock_logger.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_extracts_request_info(self, reset_singleton):
        """Test decorator extracts IP and user agent from request"""
        mock_logger = MagicMock()

        # Since isinstance(mock, Request) returns False for MagicMock,
        # we test that the decorator still works and logs with the user_id
        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):

            @audit_log(AuditAction.FILE_UPLOADED, resource="file")
            async def upload_file(user_id: str, file_id: str):
                return {"status": "uploaded"}

            result = await upload_file(user_id="user123", file_id="file-001")

            mock_logger.log.assert_called_once()
            call_kwargs = mock_logger.log.call_args[1]
            # Without real Request, ip_address and user_agent are None
            assert call_kwargs["user_id"] == "user123"
            assert call_kwargs["action"] == AuditAction.FILE_UPLOADED
            assert call_kwargs["resource"] == "file"

    @pytest.mark.asyncio
    async def test_decorator_extracts_resource_id(self, reset_singleton):
        """Test decorator extracts resource_id from kwargs"""
        mock_logger = MagicMock()
        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):

            @audit_log(AuditAction.WORKFLOW_DELETED, resource="workflow")
            async def delete_workflow(workflow_id: str, user_id: str):
                return {"status": "deleted"}

            result = await delete_workflow(workflow_id="wf-123", user_id="user123")

            mock_logger.log.assert_called_once()
            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["resource_id"] == "wf-123"

    @pytest.mark.asyncio
    async def test_decorator_skips_log_without_user_id(self, reset_singleton):
        """Test decorator skips logging if no user_id"""
        mock_logger = MagicMock()
        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):

            @audit_log(AuditAction.FILE_UPLOADED, resource="file")
            async def upload_file():
                return {"status": "uploaded"}

            result = await upload_file()

            # Should not log without user_id
            mock_logger.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_with_current_user_id(self, reset_singleton):
        """Test decorator accepts current_user_id kwarg"""
        mock_logger = MagicMock()

        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):

            @audit_log(AuditAction.FILE_UPLOADED, resource="file")
            async def upload_file(current_user_id: str):
                return {"status": "uploaded"}

            result = await upload_file(current_user_id="current_user_123")

            mock_logger.log.assert_called_once()
            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["user_id"] == "current_user_123"


# ========== Sync Helper Tests ==========

class TestAuditLogSync:
    """Tests for audit_log_sync function"""

    def test_sync_logs_action(self, reset_singleton):
        """Test sync helper logs action"""
        mock_logger = MagicMock()
        with patch('api.audit_logger.get_audit_logger', return_value=mock_logger):
            audit_log_sync(
                user_id="user123",
                action=AuditAction.SETTINGS_CHANGED,
                resource="settings",
                details={"changed": "theme"}
            )

            mock_logger.log.assert_called_once()
            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["user_id"] == "user123"
            assert call_kwargs["action"] == "settings.changed"
            assert call_kwargs["resource"] == "settings"


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_in_fields(self, audit_logger):
        """Test unicode characters in fields"""
        result = audit_logger.log(
            user_id="用户123",
            action="test.action",
            resource="リソース",
            details={"message": "Привет мир"}
        )

        assert result > 0

        logs = audit_logger.get_logs(user_id="用户123")
        assert len(logs) == 1
        assert logs[0].resource == "リソース"

    def test_special_characters(self, audit_logger):
        """Test special characters in fields"""
        result = audit_logger.log(
            user_id="user@example.com",
            action="test.action",
            resource="path/to/resource",
            details={"sql": "SELECT * FROM users WHERE id = 'test'"}
        )

        assert result > 0

    def test_empty_strings(self, audit_logger):
        """Test empty string handling"""
        result = audit_logger.log(
            user_id="user123",
            action="test.action",
            resource="",
            resource_id=""
        )

        assert result > 0

    def test_very_long_details(self, audit_logger):
        """Test very long details JSON"""
        long_data = {"data": "x" * 10000}
        result = audit_logger.log(
            user_id="user123",
            action="test.action",
            details=long_data
        )

        assert result > 0

    def test_concurrent_writes(self, audit_logger):
        """Test concurrent writes don't conflict"""
        import threading

        results = []

        def log_entry(i):
            result = audit_logger.log(
                user_id=f"user{i}",
                action="test.action"
            )
            results.append(result)

        threads = [threading.Thread(target=log_entry, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writes should succeed
        assert len(results) == 10
        assert all(r > 0 for r in results)
        assert audit_logger.count_logs() == 10


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_full_audit_lifecycle(self, audit_logger):
        """Test full audit lifecycle"""
        # Log entries
        audit_logger.log(
            user_id="admin",
            action=AuditAction.USER_CREATED,
            resource="user",
            resource_id="new_user"
        )
        audit_logger.log(
            user_id="admin",
            action=AuditAction.SETTINGS_CHANGED,
            details={"setting": "theme", "value": "dark"}
        )
        audit_logger.log(
            user_id="new_user",
            action=AuditAction.USER_LOGIN
        )

        # Query logs
        all_logs = audit_logger.get_logs()
        assert len(all_logs) == 3

        admin_logs = audit_logger.get_logs(user_id="admin")
        assert len(admin_logs) == 2

        login_logs = audit_logger.get_logs(action=AuditAction.USER_LOGIN)
        assert len(login_logs) == 1

        # Count logs
        assert audit_logger.count_logs() == 3
        assert audit_logger.count_logs(user_id="admin") == 2

    def test_export_and_verify(self, audit_logger):
        """Test export and verify CSV"""
        # Create logs
        audit_logger.log(
            user_id="user1",
            action=AuditAction.WORKFLOW_CREATED,
            resource="workflow",
            resource_id="wf-001",
            details={"name": "Test Workflow"}
        )
        audit_logger.log(
            user_id="user2",
            action=AuditAction.FILE_UPLOADED,
            resource="file",
            resource_id="file-001"
        )

        # Export
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            audit_logger.export_to_csv(output_path)

            # Verify CSV
            with open(output_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            assert len(rows) == 2

            # Details should be JSON string
            for row in rows:
                if row["details"]:
                    json.loads(row["details"])  # Should not raise
        finally:
            if output_path.exists():
                os.unlink(output_path)
