"""
Offline Sync Database - Database utilities for offline data sync

Provides:
- Database initialization functions
- Reusable query functions for sync operations
- Sync state persistence utilities

Extracted from offline_data_sync.py during P2 decomposition.

Note: Unlike cloud_sync_db.py which has a single fixed database path,
this module works with dynamic paths since each user's sync database
is derived from their main database path.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, UTC

from .offline_sync_models import (
    SyncOperation,
    SyncState,
    SYNC_OPERATIONS_SCHEMA,
    PEER_SYNC_STATE_SCHEMA,
    VERSION_TRACKING_SCHEMA,
)

logger = logging.getLogger(__name__)


def get_sync_db_path(main_db_path: Path) -> Path:
    """
    Derive sync database path from main database path.

    The sync database is stored alongside the main database with '_sync' suffix.
    Example: /data/app.db -> /data/app_sync.db

    Args:
        main_db_path: Path to the main application database

    Returns:
        Path to the sync metadata database
    """
    return main_db_path.parent / f"{main_db_path.stem}_sync.db"


def init_sync_db(sync_db_path: Path) -> None:
    """
    Initialize sync metadata database with required tables.

    Creates tables for:
    - sync_operations: Log of all sync operations
    - peer_sync_state: Sync state tracking per peer
    - version_tracking: Vector clocks for conflict detection

    Args:
        sync_db_path: Path to the sync database file
    """
    sync_db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    # Create tables using schema definitions from models
    cursor.execute(SYNC_OPERATIONS_SCHEMA)
    cursor.execute(PEER_SYNC_STATE_SCHEMA)
    cursor.execute(VERSION_TRACKING_SCHEMA)

    conn.commit()
    conn.close()

    logger.info(f"Sync database initialized: {sync_db_path}")


# ===== Operation Persistence =====

def save_sync_operation(sync_db_path: Path, op: SyncOperation) -> None:
    """
    Save a sync operation to the database.

    Args:
        sync_db_path: Path to the sync database
        op: SyncOperation to persist
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sync_operations
        (op_id, table_name, operation, row_id, data, timestamp, peer_id, version, team_id, signature)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        op.op_id,
        op.table_name,
        op.operation,
        op.row_id,
        json.dumps(op.data) if op.data else None,
        op.timestamp,
        op.peer_id,
        op.version,
        op.team_id,
        op.signature
    ))

    conn.commit()
    conn.close()


def load_pending_operations(sync_db_path: Path, local_peer_id: str) -> List[SyncOperation]:
    """
    Load pending (unsynced) operations from database.

    Tier 10.4: Ensures sync operations survive app restarts.

    Args:
        sync_db_path: Path to the sync database
        local_peer_id: ID of the local peer

    Returns:
        List of pending SyncOperation objects ordered by version
    """
    conn = sqlite3.connect(str(sync_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT op_id, table_name, operation, row_id, data, timestamp,
               peer_id, version, team_id, signature
        FROM sync_operations
        WHERE synced = 0 AND peer_id = ?
        ORDER BY version ASC
    """, (local_peer_id,))

    operations = []
    for row in cursor.fetchall():
        op = SyncOperation(
            op_id=row['op_id'],
            table_name=row['table_name'],
            operation=row['operation'],
            row_id=row['row_id'],
            data=json.loads(row['data']) if row['data'] else None,
            timestamp=row['timestamp'],
            peer_id=row['peer_id'],
            version=row['version'],
            team_id=row['team_id'],
            signature=row['signature'] or ''
        )
        operations.append(op)

    conn.close()
    return operations


def mark_operations_synced(sync_db_path: Path, op_ids: List[str]) -> None:
    """
    Mark operations as successfully synced.

    Tier 10.4: Called after successful exchange with peer.
    Prevents duplicate syncing of same operations.

    Args:
        sync_db_path: Path to the sync database
        op_ids: List of operation IDs that were synced
    """
    if not op_ids:
        return

    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    placeholders = ','.join('?' for _ in op_ids)
    cursor.execute(f"""
        UPDATE sync_operations
        SET synced = 1
        WHERE op_id IN ({placeholders})
    """, op_ids)

    conn.commit()
    conn.close()

    logger.debug(f"Marked {len(op_ids)} operations as synced")


def get_max_version(sync_db_path: Path, local_peer_id: str) -> int:
    """
    Get the highest version number for local operations.

    Args:
        sync_db_path: Path to the sync database
        local_peer_id: ID of the local peer

    Returns:
        Highest version number, or 0 if no operations
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MAX(version) FROM sync_operations WHERE peer_id = ?
    """, (local_peer_id,))

    row = cursor.fetchone()
    conn.close()

    return row[0] if row[0] else 0


# ===== Sync State Persistence =====

def get_peer_last_sync(sync_db_path: Path, peer_id: str) -> Optional[str]:
    """
    Get the last sync timestamp for a peer.

    Args:
        sync_db_path: Path to the sync database
        peer_id: ID of the peer

    Returns:
        ISO8601 timestamp of last sync, or None if never synced
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT last_sync FROM peer_sync_state WHERE peer_id = ?
    """, (peer_id,))

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def save_sync_state(sync_db_path: Path, state: SyncState) -> None:
    """
    Save sync state for a peer.

    Args:
        sync_db_path: Path to the sync database
        state: SyncState to persist
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO peer_sync_state
        (peer_id, last_sync, operations_sent, operations_received, conflicts_resolved, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        state.peer_id,
        state.last_sync,
        state.operations_sent,
        state.operations_received,
        state.conflicts_resolved,
        state.status
    ))

    conn.commit()
    conn.close()


def load_sync_state(sync_db_path: Path, peer_id: str) -> Optional[SyncState]:
    """
    Load sync state for a peer.

    Args:
        sync_db_path: Path to the sync database
        peer_id: ID of the peer

    Returns:
        SyncState if found, None otherwise
    """
    conn = sqlite3.connect(str(sync_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT peer_id, last_sync, operations_sent, operations_received,
               conflicts_resolved, status
        FROM peer_sync_state
        WHERE peer_id = ?
    """, (peer_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return SyncState(
        peer_id=row['peer_id'],
        last_sync=row['last_sync'] or '',
        operations_sent=row['operations_sent'],
        operations_received=row['operations_received'],
        conflicts_resolved=row['conflicts_resolved'],
        status=row['status']
    )


def load_all_sync_states(sync_db_path: Path) -> List[SyncState]:
    """
    Load all peer sync states.

    Args:
        sync_db_path: Path to the sync database

    Returns:
        List of SyncState objects
    """
    conn = sqlite3.connect(str(sync_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT peer_id, last_sync, operations_sent, operations_received,
               conflicts_resolved, status
        FROM peer_sync_state
        ORDER BY last_sync DESC
    """)

    states = [
        SyncState(
            peer_id=row['peer_id'],
            last_sync=row['last_sync'] or '',
            operations_sent=row['operations_sent'],
            operations_received=row['operations_received'],
            conflicts_resolved=row['conflicts_resolved'],
            status=row['status']
        )
        for row in cursor.fetchall()
    ]

    conn.close()
    return states


# ===== Version Tracking (Conflict Detection) =====

def get_version_info(sync_db_path: Path, table_name: str, row_id: str) -> Optional[tuple]:
    """
    Get version tracking info for a specific row.

    Args:
        sync_db_path: Path to the sync database
        table_name: Table name
        row_id: Row identifier

    Returns:
        Tuple of (version, timestamp) if found, None otherwise
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT version, timestamp FROM version_tracking
        WHERE table_name = ? AND row_id = ?
        ORDER BY version DESC LIMIT 1
    """, (table_name, row_id))

    row = cursor.fetchone()
    conn.close()

    return (row[0], row[1]) if row else None


def check_version_conflict(
    sync_db_path: Path,
    table_name: str,
    row_id: str,
    peer_id: str
) -> bool:
    """
    Check if there's a version conflict for a row.

    Args:
        sync_db_path: Path to the sync database
        table_name: Table name
        row_id: Row identifier
        peer_id: Peer ID to exclude from check

    Returns:
        True if conflict exists, False otherwise
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM version_tracking
        WHERE table_name = ? AND row_id = ? AND peer_id != ?
    """, (table_name, row_id, peer_id))

    count = cursor.fetchone()[0]
    conn.close()

    return count > 0


def update_version_tracking(sync_db_path: Path, op: SyncOperation) -> None:
    """
    Update version tracking for an operation.

    Args:
        sync_db_path: Path to the sync database
        op: SyncOperation to track
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO version_tracking
        (table_name, row_id, peer_id, version, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (op.table_name, op.row_id, op.peer_id, op.version, op.timestamp))

    conn.commit()
    conn.close()


# ===== Operations Query =====

def get_operations_since(
    sync_db_path: Path,
    local_peer_id: str,
    last_sync: Optional[str] = None,
    tables: Optional[List[str]] = None
) -> List[SyncOperation]:
    """
    Get operations since a specific sync time.

    Args:
        sync_db_path: Path to the sync database
        local_peer_id: ID of the local peer
        last_sync: Optional timestamp to filter from
        tables: Optional list of tables to filter

    Returns:
        List of SyncOperation objects ordered by version
    """
    conn = sqlite3.connect(str(sync_db_path))
    cursor = conn.cursor()

    # Build query
    query = """
        SELECT op_id, table_name, operation, row_id, data, timestamp, peer_id, version, team_id, signature
        FROM sync_operations
        WHERE peer_id = ?
    """
    params = [local_peer_id]

    if last_sync:
        query += " AND timestamp > ?"
        params.append(last_sync)

    if tables:
        placeholders = ','.join('?' * len(tables))
        query += f" AND table_name IN ({placeholders})"
        params.extend(tables)

    query += " ORDER BY version ASC"

    cursor.execute(query, params)

    operations = []
    for row in cursor.fetchall():
        op = SyncOperation(
            op_id=row[0],
            table_name=row[1],
            operation=row[2],
            row_id=row[3],
            data=json.loads(row[4]) if row[4] else None,
            timestamp=row[5],
            peer_id=row[6],
            version=row[7],
            team_id=row[8],
            signature=row[9] or ""
        )
        operations.append(op)

    conn.close()
    return operations


__all__ = [
    # Path utilities
    "get_sync_db_path",
    "init_sync_db",
    # Operation persistence
    "save_sync_operation",
    "load_pending_operations",
    "mark_operations_synced",
    "get_max_version",
    # Sync state persistence
    "get_peer_last_sync",
    "save_sync_state",
    "load_sync_state",
    "load_all_sync_states",
    # Version tracking
    "get_version_info",
    "check_version_conflict",
    "update_version_tracking",
    # Operations query
    "get_operations_since",
]
