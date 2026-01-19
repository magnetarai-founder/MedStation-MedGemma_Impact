"""
Cloud Sync Database - Database utilities for cloud sync service

Provides:
- Database path configuration
- Schema initialization
- Reusable database query functions

Extracted from cloud_sync.py during P2 decomposition.
"""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, UTC

from api.config_paths import get_config_paths
from api.db.pool import get_connection_pool

from .cloud_sync_models import ConflictInfo, ChangeLogEntry

logger = logging.getLogger(__name__)


# ===== Configuration =====

PATHS = get_config_paths()
SYNC_DB_PATH = PATHS.data_dir / "cloud_sync.db"


def _get_pool():
    """Get the connection pool for cloud sync database."""
    return get_connection_pool(SYNC_DB_PATH)


# ===== Database Initialization =====

def init_sync_db() -> None:
    """Initialize sync database tables"""
    SYNC_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()

        # Sync state - tracks last sync for each resource
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                local_version INTEGER DEFAULT 0,
                remote_version INTEGER DEFAULT 0,
                local_hash TEXT,
                remote_hash TEXT,
                last_synced_at TEXT,
                sync_status TEXT DEFAULT 'pending',
                error_message TEXT,
                PRIMARY KEY (resource_type, resource_id, user_id)
            )
        """)

        # Sync conflicts - unresolved conflicts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                conflict_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                local_data TEXT,
                remote_data TEXT,
                local_modified_at TEXT,
                remote_modified_at TEXT,
                detected_at TEXT NOT NULL,
                resolved_at TEXT,
                resolution TEXT,
                resolved_by TEXT
            )
        """)

        # Sync log - history of sync operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                direction TEXT,
                status TEXT NOT NULL,
                bytes_transferred INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT
            )
        """)

        # Pending changes queue - offline changes to sync
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_changes (
                change_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                operation TEXT NOT NULL,  -- create, update, delete
                change_data TEXT,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_state_user ON sync_state(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_user ON sync_conflicts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_user ON pending_changes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_user ON sync_log(user_id)")

        conn.commit()


# ===== Status Queries =====

def get_sync_counts(user_id: str) -> Dict[str, Any]:
    """
    Get sync status counts for a user.

    Returns dict with:
    - pending_uploads: count of pending changes
    - pending_downloads: count of items needing download
    - conflicts: count of unresolved conflicts
    - last_sync_at: timestamp of last sync
    """
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()

        # Count pending uploads
        cursor.execute("""
            SELECT COUNT(*) FROM pending_changes WHERE user_id = ?
        """, (user_id,))
        pending_uploads = cursor.fetchone()[0]

        # Count items needing download (remote_version > local_version)
        cursor.execute("""
            SELECT COUNT(*) FROM sync_state
            WHERE user_id = ? AND remote_version > local_version
        """, (user_id,))
        pending_downloads = cursor.fetchone()[0]

        # Count unresolved conflicts
        cursor.execute("""
            SELECT COUNT(*) FROM sync_conflicts
            WHERE user_id = ? AND resolved_at IS NULL
        """, (user_id,))
        conflicts = cursor.fetchone()[0]

        # Get last sync time
        cursor.execute("""
            SELECT MAX(last_synced_at) FROM sync_state WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        last_sync_at = row[0] if row else None

    return {
        "pending_uploads": pending_uploads,
        "pending_downloads": pending_downloads,
        "conflicts": conflicts,
        "last_sync_at": last_sync_at,
    }


# ===== Sync Operations =====

def log_sync_operation(
    log_id: str,
    user_id: str,
    operation: str,
    resource_type: str,
    direction: str,
    status: str,
    started_at: datetime
) -> None:
    """Log a sync operation to the sync_log table."""
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log
            (log_id, user_id, operation, resource_type, direction, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, operation, resource_type, direction, status, started_at.isoformat()))
        conn.commit()


def complete_sync_operation(log_id: str, status: str = "completed") -> None:
    """Mark a sync operation as completed."""
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sync_log
            SET status = ?, completed_at = ?
            WHERE log_id = ?
        """, (status, datetime.now(UTC).isoformat(), log_id))
        conn.commit()


def check_for_conflict(
    user_id: str,
    resource_type: str,
    resource_id: str,
    last_sync_version: int
) -> Optional[int]:
    """
    Check if there's a conflict for a resource.

    Returns remote_version if conflict detected, None otherwise.
    """
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT remote_version FROM sync_state
            WHERE resource_type = ? AND resource_id = ? AND user_id = ?
        """, (resource_type, resource_id, user_id))
        row = cursor.fetchone()

        if row and row[0] > last_sync_version:
            return row[0]
        return None


def record_conflict(
    conflict_id: str,
    resource_type: str,
    resource_id: str,
    user_id: str,
    local_data: Optional[Dict[str, Any]],
    local_modified_at: str
) -> ConflictInfo:
    """Record a sync conflict in the database."""
    detected_at = datetime.now(UTC).isoformat()

    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_conflicts
            (conflict_id, resource_type, resource_id, user_id,
             local_data, local_modified_at, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            conflict_id,
            resource_type,
            resource_id,
            user_id,
            json.dumps(local_data) if local_data else None,
            local_modified_at,
            detected_at
        ))
        conn.commit()

    return ConflictInfo(
        conflict_id=conflict_id,
        resource_type=resource_type,
        resource_id=resource_id,
        local_modified_at=local_modified_at,
        remote_modified_at=detected_at,
        detected_at=detected_at
    )


def update_sync_state(
    resource_type: str,
    resource_id: str,
    user_id: str,
    version: int
) -> None:
    """Update sync state for a resource after successful sync."""
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_state
            (resource_type, resource_id, user_id, local_version,
             remote_version, last_synced_at, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, 'completed')
        """, (
            resource_type,
            resource_id,
            user_id,
            version,
            version,
            datetime.now(UTC).isoformat()
        ))
        conn.commit()


def get_remote_changes(user_id: str, since_version: int) -> List[ChangeLogEntry]:
    """Get remote changes since a given version."""
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT resource_type, resource_id, remote_version
            FROM sync_state
            WHERE user_id = ? AND remote_version > ?
        """, (user_id, since_version))

        changes = [
            ChangeLogEntry(
                resource_type=row[0],
                resource_id=row[1],
                operation="update",
                modified_at=datetime.now(UTC).isoformat(),
                version=row[2]
            )
            for row in cursor.fetchall()
        ]

    return changes


# ===== Conflict Management =====

def list_unresolved_conflicts(user_id: str) -> List[ConflictInfo]:
    """List all unresolved conflicts for a user."""
    with _get_pool().get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT conflict_id, resource_type, resource_id,
                   local_modified_at, remote_modified_at, detected_at
            FROM sync_conflicts
            WHERE user_id = ? AND resolved_at IS NULL
            ORDER BY detected_at DESC
        """, (user_id,))

        conflicts = [
            ConflictInfo(
                conflict_id=row["conflict_id"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                local_modified_at=row["local_modified_at"] or "",
                remote_modified_at=row["remote_modified_at"] or "",
                detected_at=row["detected_at"]
            )
            for row in cursor.fetchall()
        ]

    return conflicts


def get_conflict(user_id: str, conflict_id: str) -> Optional[Tuple[str, str]]:
    """
    Get a conflict by ID.

    Returns (resource_type, resource_id) if found, None otherwise.
    """
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT resource_type, resource_id FROM sync_conflicts
            WHERE conflict_id = ? AND user_id = ? AND resolved_at IS NULL
        """, (conflict_id, user_id))
        row = cursor.fetchone()

        if row:
            return row[0], row[1]
        return None


def resolve_conflict_in_db(
    conflict_id: str,
    user_id: str,
    resolution: str,
    bump_local_version: bool = False
) -> None:
    """
    Mark a conflict as resolved in the database.

    If bump_local_version is True, also increments the local_version
    for the affected resource (for LOCAL_WINS or MANUAL resolution).
    """
    with _get_pool().get_connection() as conn:
        cursor = conn.cursor()

        # Get resource info for version bump
        cursor.execute("""
            SELECT resource_type, resource_id FROM sync_conflicts
            WHERE conflict_id = ?
        """, (conflict_id,))
        row = cursor.fetchone()

        if not row:
            return

        resource_type, resource_id = row

        # Mark as resolved
        cursor.execute("""
            UPDATE sync_conflicts
            SET resolved_at = ?, resolution = ?, resolved_by = ?
            WHERE conflict_id = ?
        """, (
            datetime.now(UTC).isoformat(),
            resolution,
            user_id,
            conflict_id
        ))

        # Optionally bump local version
        if bump_local_version:
            cursor.execute("""
                UPDATE sync_state
                SET sync_status = 'pending', local_version = local_version + 1
                WHERE resource_type = ? AND resource_id = ? AND user_id = ?
            """, (resource_type, resource_id, user_id))

        conn.commit()


# Initialize on module load (safe, idempotent)
init_sync_db()


__all__ = [
    # Configuration
    "PATHS",
    "SYNC_DB_PATH",
    # Initialization
    "init_sync_db",
    # Status queries
    "get_sync_counts",
    # Sync operations
    "log_sync_operation",
    "complete_sync_operation",
    "check_for_conflict",
    "record_conflict",
    "update_sync_state",
    "get_remote_changes",
    # Conflict management
    "list_unresolved_conflicts",
    "get_conflict",
    "resolve_conflict_in_db",
]
