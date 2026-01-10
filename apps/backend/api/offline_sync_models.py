"""
Offline Sync Models - Dataclasses and constants for offline data sync

Provides:
- SYNCABLE_TABLES security allowlist
- SyncOperation dataclass for tracking sync operations
- SyncState dataclass for peer sync state
- Database schema definitions for sync tables

Extracted from offline_data_sync.py during P2 decomposition.
"""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass, asdict


# SECURITY: Allowlist of tables that can be synced via P2P
# Only these tables can be modified by incoming sync operations
# This prevents SQL injection via malicious table names from peers
SYNCABLE_TABLES: frozenset[str] = frozenset({
    # Chat and messages
    "chat_sessions",
    "chat_messages",
    "chat_context",
    # Vault and files
    "vault_files",
    "vault_folders",
    "vault_metadata",
    # Workflows
    "workflows",
    "work_items",
    # Team collaboration
    "team_notes",
    "team_documents",
    "shared_queries",
    # Query history
    "query_history",
})


@dataclass
class SyncOperation:
    """
    A single sync operation for CRDT-based synchronization.

    Attributes:
        op_id: Unique identifier for this operation (UUID)
        table_name: Target table (must be in SYNCABLE_TABLES)
        operation: One of 'insert', 'update', 'delete'
        row_id: Primary key of affected row
        data: Row data for insert/update operations
        timestamp: ISO8601 timestamp for Last-Write-Wins conflict resolution
        peer_id: ID of peer that created this operation
        version: Vector clock value for ordering
        team_id: Optional team ID for team-scoped operations (Phase 4)
        signature: HMAC signature for team operations (Phase 4)
    """
    op_id: str
    table_name: str
    operation: str  # 'insert', 'update', 'delete'
    row_id: Any
    data: Optional[dict]
    timestamp: str
    peer_id: str
    version: int  # Vector clock for conflict resolution
    team_id: Optional[str] = None  # Phase 4: Team isolation
    signature: str = ""  # Phase 4: HMAC signature for team ops

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_payload(self) -> dict:
        """Get payload dict for signature verification (excludes signature field)."""
        return {
            "op_id": self.op_id,
            "table_name": self.table_name,
            "operation": self.operation,
            "row_id": self.row_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "peer_id": self.peer_id,
            "version": self.version,
            "team_id": self.team_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncOperation":
        """Create SyncOperation from dictionary."""
        return cls(
            op_id=data['op_id'],
            table_name=data['table_name'],
            operation=data['operation'],
            row_id=data['row_id'],
            data=data.get('data'),
            timestamp=data['timestamp'],
            peer_id=data['peer_id'],
            version=data['version'],
            team_id=data.get('team_id'),
            signature=data.get('signature', '')
        )


@dataclass
class SyncState:
    """
    Synchronization state with a peer.

    Tracks the history and status of sync operations with a specific peer.

    Attributes:
        peer_id: Unique identifier for the peer
        last_sync: ISO8601 timestamp of last successful sync
        operations_sent: Total count of operations sent to peer
        operations_received: Total count of operations received from peer
        conflicts_resolved: Total count of conflicts resolved with this peer
        status: Current status - 'syncing', 'idle', 'error'
    """
    peer_id: str
    last_sync: str
    operations_sent: int
    operations_received: int
    conflicts_resolved: int
    status: str  # 'syncing', 'idle', 'error'

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        """Create SyncState from dictionary."""
        return cls(
            peer_id=data['peer_id'],
            last_sync=data.get('last_sync', ''),
            operations_sent=data.get('operations_sent', 0),
            operations_received=data.get('operations_received', 0),
            conflicts_resolved=data.get('conflicts_resolved', 0),
            status=data.get('status', 'idle')
        )


# ===== Database Schema Definitions =====
# These can be used by any module that needs to create sync tables

SYNC_OPERATIONS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS sync_operations (
        op_id TEXT PRIMARY KEY,
        table_name TEXT NOT NULL,
        operation TEXT NOT NULL,
        row_id TEXT NOT NULL,
        data TEXT,
        timestamp TEXT NOT NULL,
        peer_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        team_id TEXT,
        signature TEXT,
        synced INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )
"""

PEER_SYNC_STATE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS peer_sync_state (
        peer_id TEXT PRIMARY KEY,
        last_sync TEXT,
        operations_sent INTEGER DEFAULT 0,
        operations_received INTEGER DEFAULT 0,
        conflicts_resolved INTEGER DEFAULT 0,
        status TEXT DEFAULT 'idle',
        updated_at TEXT DEFAULT (datetime('now'))
    )
"""

VERSION_TRACKING_SCHEMA = """
    CREATE TABLE IF NOT EXISTS version_tracking (
        table_name TEXT,
        row_id TEXT,
        peer_id TEXT,
        version INTEGER,
        timestamp TEXT,
        PRIMARY KEY (table_name, row_id, peer_id)
    )
"""


__all__ = [
    # Security constants
    "SYNCABLE_TABLES",
    # Dataclasses
    "SyncOperation",
    "SyncState",
    # Schema definitions
    "SYNC_OPERATIONS_SCHEMA",
    "PEER_SYNC_STATE_SCHEMA",
    "VERSION_TRACKING_SCHEMA",
]
