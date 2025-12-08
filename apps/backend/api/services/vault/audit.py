"""
Vault Audit Logging

Handles comprehensive audit trail for security and compliance.
"""

import sqlite3
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Configuration paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


def log_audit(
    vault_service,
    user_id: str,
    vault_type: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> str:
    """
    Log an audit event.

    Args:
        vault_service: VaultService instance
        user_id: User ID performing the action
        vault_type: 'real' or 'decoy'
        action: Action performed (e.g., 'create', 'read', 'update', 'delete', 'share')
        resource_type: Type of resource (e.g., 'file', 'folder', 'document')
        resource_id: ID of the resource (optional)
        details: Additional details about the action (optional)
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)

    Returns:
        Audit log ID

    Security:
        - Immutable audit trail
        - Captures security-relevant actions
        - Includes client context (IP, user agent)
        - Vault-type scoped for isolation
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        log_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO vault_audit_logs (
                id, user_id, vault_type, action, resource_type,
                resource_id, details, ip_address, user_agent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, vault_type, action, resource_type,
              resource_id, details, ip_address, user_agent, now))

        conn.commit()
        return log_id

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log audit: {e}")
        raise
    finally:
        conn.close()


def get_audit_logs(
    vault_service,
    user_id: str,
    vault_type: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get audit logs with optional filters.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: Filter by vault type (optional)
        action: Filter by action (optional)
        resource_type: Filter by resource type (optional)
        date_from: Filter by start date ISO format (optional)
        date_to: Filter by end date ISO format (optional)
        limit: Maximum number of logs to return (default: 100)

    Returns:
        List of audit log dictionaries with:
        - id, user_id, vault_type, action, resource_type
        - resource_id, details, ip_address, user_agent, created_at

    Security:
        - Returns only user's audit logs
        - Supports filtering for compliance queries
        - Time-bounded queries supported
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        sql = """
            SELECT id, user_id, vault_type, action, resource_type,
                   resource_id, details, ip_address, user_agent, created_at
            FROM vault_audit_logs
            WHERE user_id = ?
        """
        params = [user_id]

        if vault_type:
            sql += " AND vault_type = ?"
            params.append(vault_type)

        if action:
            sql += " AND action = ?"
            params.append(action)

        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)

        if date_from:
            sql += " AND created_at >= ?"
            params.append(date_from)

        if date_to:
            sql += " AND created_at <= ?"
            params.append(date_to)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)

        logs = []
        for row in cursor.fetchall():
            logs.append({
                "id": row[0],
                "user_id": row[1],
                "vault_type": row[2],
                "action": row[3],
                "resource_type": row[4],
                "resource_id": row[5],
                "details": row[6],
                "ip_address": row[7],
                "user_agent": row[8],
                "created_at": row[9]
            })

        return logs

    finally:
        conn.close()
