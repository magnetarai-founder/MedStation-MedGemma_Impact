"""
Audit Logging System

Always-on logging of all data access and sensitive operations.
SQLite storage, admin-viewable only.

Features:
- Always on (cannot be disabled)
- Logs: user_id, action, resource, timestamp, ip_address
- Persistent storage in separate audit.db (SQLite)
- Admin-only viewing (Super Admin + Admin roles)
- 90-day retention with automatic cleanup
- CSV export for compliance reviews

Note: Currently uses unencrypted SQLite. For production deployments requiring
encryption at rest, enable filesystem-level encryption (LUKS, FileVault, BitLocker)
or use SQLCipher as a drop-in replacement for sqlite3.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps
import logging

from fastapi import Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """Audit log entry model"""
    id: Optional[int] = None
    user_id: str
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class AuditAction:
    """Standard audit action types"""
    # Authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login.failed"

    # User Management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role.changed"

    # Vault Operations
    VAULT_ACCESSED = "vault.accessed"
    VAULT_ITEM_CREATED = "vault.item.created"
    VAULT_ITEM_VIEWED = "vault.item.viewed"
    VAULT_ITEM_UPDATED = "vault.item.updated"
    VAULT_ITEM_DELETED = "vault.item.deleted"

    # Workflow Operations
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_VIEWED = "workflow.viewed"
    WORKFLOW_UPDATED = "workflow.updated"
    WORKFLOW_DELETED = "workflow.deleted"
    WORKFLOW_EXECUTED = "workflow.executed"

    # File Operations
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_DELETED = "file.deleted"

    # Database Operations
    SQL_QUERY_EXECUTED = "sql.query.executed"
    DATABASE_EXPORTED = "database.exported"

    # Security Operations
    PANIC_MODE_ACTIVATED = "security.panic_mode.activated"
    BACKUP_CREATED = "backup.created"
    BACKUP_RESTORED = "backup.restored"
    ENCRYPTION_KEY_ROTATED = "security.key.rotated"

    # Settings
    SETTINGS_CHANGED = "settings.changed"

    # Code & Agent Operations
    CODE_ASSIST = "code.assist"
    CODE_EDIT = "code.edit"
    CODE_FILE_OPENED = "code.file.opened"
    CODE_FILE_SAVED = "code.file.saved"

    # Terminal Operations
    TERMINAL_SPAWN = "terminal.spawn"
    TERMINAL_CLOSE = "terminal.close"
    TERMINAL_COMMAND = "terminal.command"

    # Admin/Founder Rights Operations
    ADMIN_LIST_USERS = "admin.list.users"
    ADMIN_VIEW_USER = "admin.view.user"
    ADMIN_VIEW_USER_CHATS = "admin.view.user_chats"
    ADMIN_LIST_ALL_CHATS = "admin.list.all_chats"
    ADMIN_RESET_PASSWORD = "admin.reset_password"
    ADMIN_UNLOCK_ACCOUNT = "admin.unlock_account"
    ADMIN_VIEW_VAULT_STATUS = "admin.view.vault_status"
    ADMIN_VIEW_DEVICE_OVERVIEW = "admin.view.device_overview"
    ADMIN_VIEW_USER_WORKFLOWS = "admin.view.user_workflows"
    FOUNDER_RIGHTS_LOGIN = "founder_rights.login"


class AuditLogger:
    """
    Audit logging service with persistent SQLite storage

    Storage is unencrypted by default. For encryption at rest in production:
    - Use filesystem-level encryption (LUKS, FileVault, BitLocker)
    - Or replace sqlite3 with pysqlcipher3 for database-level encryption
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize audit logger

        Args:
            db_path: Path to audit database (defaults to data dir)
        """
        if db_path is None:
            from config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "audit.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize audit database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT,
                resource_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT NOT NULL,
                details TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user_id
            ON audit_log(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_action
            ON audit_log(action)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_resource
            ON audit_log(resource, resource_id)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Audit logger initialized: {self.db_path}")

    def log(
        self,
        user_id: str,
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an audit event

        Args:
            user_id: User performing the action
            action: Action being performed (use AuditAction constants)
            resource: Resource type (e.g., "workflow", "vault")
            resource_id: Specific resource identifier
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional context as JSON (will be sanitized)

        Returns:
            ID of created audit log entry
        """
        try:
            # Import sanitization utility
            try:
                from .utils import sanitize_for_log
            except ImportError:
                from utils import sanitize_for_log

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.utcnow().isoformat()

            # Sanitize details before storing
            sanitized_details = sanitize_for_log(details) if details else None
            details_json = json.dumps(sanitized_details) if sanitized_details else None

            cursor.execute("""
                INSERT INTO audit_log
                (user_id, action, resource, resource_id, ip_address, user_agent, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                action,
                resource,
                resource_id,
                ip_address,
                user_agent,
                timestamp,
                details_json
            ))

            audit_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.debug(f"Audit log created: {action} by {user_id}")
            return audit_id

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't raise - audit failures shouldn't break the app
            return -1

    def get_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEntry]:
        """
        Query audit logs

        Args:
            user_id: Filter by user
            action: Filter by action type
            resource: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of audit entries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Build query dynamically
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if action:
                query += " AND action = ?"
                params.append(action)

            if resource:
                query += " AND resource = ?"
                params.append(resource)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Convert to AuditEntry objects
            entries = []
            for row in rows:
                details = json.loads(row[8]) if row[8] else None
                entries.append(AuditEntry(
                    id=row[0],
                    user_id=row[1],
                    action=row[2],
                    resource=row[3],
                    resource_id=row[4],
                    ip_address=row[5],
                    user_agent=row[6],
                    timestamp=row[7],
                    details=details
                ))

            return entries

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []

    def count_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count audit logs matching filters

        Args:
            user_id: Filter by user
            action: Filter by action type
            resource: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Count of matching entries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Build query dynamically
            query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if action:
                query += " AND action = ?"
                params.append(action)

            if resource:
                query += " AND resource = ?"
                params.append(resource)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            conn.close()

            return count

        except Exception as e:
            logger.error(f"Failed to count audit logs: {e}")
            return 0

    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Delete audit logs older than retention period

        Args:
            retention_days: Number of days to keep (default: 90)

        Returns:
            Number of logs deleted
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            cursor.execute("""
                DELETE FROM audit_log
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old audit logs")

            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup audit logs: {e}")
            return 0

    def export_to_csv(
        self,
        output_path: Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> bool:
        """
        Export audit logs to CSV file

        Args:
            output_path: Path to output CSV file
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if export successful
        """
        try:
            import csv

            logs = self.get_logs(
                start_date=start_date,
                end_date=end_date,
                limit=1000000  # Export all matching logs
            )

            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = [
                    'id', 'user_id', 'action', 'resource', 'resource_id',
                    'ip_address', 'user_agent', 'timestamp', 'details'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for log in logs:
                    writer.writerow({
                        'id': log.id,
                        'user_id': log.user_id,
                        'action': log.action,
                        'resource': log.resource or '',
                        'resource_id': log.resource_id or '',
                        'ip_address': log.ip_address or '',
                        'user_agent': log.user_agent or '',
                        'timestamp': log.timestamp,
                        'details': json.dumps(log.details) if log.details else ''
                    })

            logger.info(f"Exported {len(logs)} audit logs to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return False


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get or create global audit logger instance

    Returns:
        AuditLogger instance
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger


def audit_log(
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None
):
    """
    Decorator to automatically log API endpoint calls

    Usage:
        @router.delete("/workflows/{workflow_id}")
        @audit_log(AuditAction.WORKFLOW_DELETED, resource="workflow")
        async def delete_workflow(workflow_id: str, request: Request):
            ...

    Args:
        action: Action being performed (use AuditAction constants)
        resource: Resource type
        resource_id: Resource ID (if not in path params)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user info
            request = kwargs.get('request')
            user_id = kwargs.get('user_id') or kwargs.get('current_user_id')

            # Get IP and user agent from request
            ip_address = None
            user_agent = None
            if request and isinstance(request, Request):
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get('user-agent')

                # Try to get user_id from headers if not in kwargs
                if not user_id:
                    user_id = request.headers.get('X-User-ID')

            # Get resource_id from path params if not provided
            actual_resource_id = resource_id
            if not actual_resource_id and resource:
                # Try to find resource_id in kwargs
                for key in kwargs:
                    if key.endswith('_id'):
                        actual_resource_id = kwargs[key]
                        break

            # Execute the function first
            result = await func(*args, **kwargs)

            # Log the audit entry (after successful execution)
            if user_id:
                logger_instance = get_audit_logger()
                logger_instance.log(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    resource_id=actual_resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

            return result

        return wrapper
    return decorator


def audit_log_sync(
    user_id: str,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Synchronous audit logging (for non-decorator use)

    Args:
        user_id: User performing the action
        action: Action being performed
        resource: Resource type
        resource_id: Resource identifier
        details: Additional context
    """
    logger_instance = get_audit_logger()
    logger_instance.log(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details
    )
