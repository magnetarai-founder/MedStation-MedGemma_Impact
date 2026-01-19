"""
Admin Audit Operations

Provides Founder Rights support capabilities for audit logs:
- Query audit logs with filters
- Export audit logs as CSV

Extracted from admin_support.py during P2 decomposition.
"""

import sqlite3
import logging
from typing import Dict, Optional, Any

from api.errors import http_404, http_500

logger = logging.getLogger(__name__)


# ===== Audit Log Functions =====

async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query audit logs with filters.

    Args:
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        user_id: Filter by user_id
        action: Filter by action type
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)

    Returns:
        Dict with logs list and total count
    """
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

    audit_db_path = PATHS.data_dir / "audit_log.db"
    if not audit_db_path.exists():
        return {"logs": [], "total": 0}

    try:
        conn = sqlite3.connect(str(audit_db_path))
        conn.row_factory = sqlite3.Row

        # Build query with filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if action:
            query += " AND action = ?"
            params.append(action)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]

        # Get total count
        count_query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
        count_params = []

        if user_id:
            count_query += " AND user_id = ?"
            count_params.append(user_id)

        if action:
            count_query += " AND action = ?"
            count_params.append(action)

        if start_date:
            count_query += " AND timestamp >= ?"
            count_params.append(start_date)

        if end_date:
            count_query += " AND timestamp <= ?"
            count_params.append(end_date)

        total = conn.execute(count_query, count_params).fetchone()[0]

        conn.close()

        return {"logs": logs, "total": total}

    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        raise http_500("Failed to retrieve audit logs")


async def export_audit_logs(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Export audit logs as CSV.

    Args:
        user_id: Filter by user_id
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)

    Returns:
        CSV string of audit logs

    Raises:
        HTTPException: If audit DB not available
    """
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

    audit_db_path = PATHS.data_dir / "audit_log.db"
    if not audit_db_path.exists():
        raise http_404("Audit log database not found", resource="audit_log_db")

    try:
        import csv
        import io

        conn = sqlite3.connect(str(audit_db_path))
        conn.row_factory = sqlite3.Row

        # Build query with filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Generate CSV
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        conn.close()

        return output.getvalue()

    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        raise http_500("Failed to export audit logs")


__all__ = [
    "get_audit_logs",
    "export_audit_logs",
]
