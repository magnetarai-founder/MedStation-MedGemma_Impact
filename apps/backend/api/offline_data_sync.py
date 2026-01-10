#!/usr/bin/env python3
"""
Offline Data Sync for ElohimOS - Facade Module

Sync databases, query results, chat history across missionary team
Uses CRDTs for conflict-free synchronization.

This module serves as a backward-compatible facade that re-exports dataclasses
and constants from extracted modules. Direct imports from extracted modules
are preferred for new code.

Extracted modules (P2 decomposition):
- offline_sync_models.py: Dataclasses, constants, and schema definitions
- offline_sync_db.py: Database utilities and query functions
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from pathlib import Path

# Re-export models for backward compatibility
from .offline_sync_models import (
    SYNCABLE_TABLES,
    SyncOperation,
    SyncState,
    SYNC_OPERATIONS_SCHEMA,
    PEER_SYNC_STATE_SCHEMA,
    VERSION_TRACKING_SCHEMA,
)

# Import database utilities
from .offline_sync_db import (
    get_sync_db_path,
    init_sync_db,
    save_sync_operation,
    load_pending_operations,
    mark_operations_synced,
    get_max_version,
    get_peer_last_sync,
    save_sync_state,
    load_sync_state,
    check_version_conflict,
    update_version_tracking,
    get_operations_since,
)

# Phase 4: Team cryptography for P2P sync
try:
    from team_crypto import sign_payload, verify_payload
    from api.services.team import is_team_member
except ImportError:
    # Fallback for standalone testing
    def sign_payload(payload, team_id): return ""
    def verify_payload(payload, signature, team_id): return True
    def is_team_member(team_id, user_id): return "member"

# SQL Safety for identifier quoting
try:
    from api.security.sql_safety import quote_identifier
except ImportError:
    # Fallback: basic identifier quoting (double-quote escaping)
    def quote_identifier(name: str) -> str:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(f"Invalid identifier: {name}")
        return f'"{name.replace(chr(34), chr(34)+chr(34))}"'

logger = logging.getLogger(__name__)


class OfflineDataSync:
    """
    Offline data synchronization using CRDTs

    Features:
    - Automatic conflict resolution (Last-Write-Wins with vector clocks)
    - Selective sync (choose what to sync)
    - Delta sync (only changes since last sync)
    - Bidirectional sync
    """

    def __init__(self, db_path: Path, local_peer_id: str):
        self.db_path = db_path
        self.local_peer_id = local_peer_id

        # Sync state
        self.sync_states: Dict[str, SyncState] = {}
        self.pending_operations: List[SyncOperation] = []

        # Vector clock for this peer
        self.local_version = 0

        # Initialize sync metadata database using extracted utility
        self.sync_db_path = get_sync_db_path(db_path)
        init_sync_db(self.sync_db_path)

        # Load any pending operations from previous session (Tier 10.4)
        self._load_pending_operations()

        logger.info(f"🔄 Data sync initialized for peer {local_peer_id}")

    def _init_sync_db(self) -> None:
        """Initialize sync metadata database (delegates to extracted module)."""
        init_sync_db(self.sync_db_path)

    def _load_pending_operations(self) -> None:
        """
        Load pending (unsynced) operations from database on startup.

        Tier 10.4: Ensures sync operations survive app restarts.
        Operations are retried automatically when sync resumes.
        """
        operations = load_pending_operations(self.sync_db_path, self.local_peer_id)

        for op in operations:
            self.pending_operations.append(op)
            # Update local_version to highest seen version
            if op.version > self.local_version:
                self.local_version = op.version

        if operations:
            logger.info(f"📥 Loaded {len(operations)} pending sync operations from previous session")

    def _mark_operations_synced(self, op_ids: list[str]) -> None:
        """
        Mark operations as successfully synced.

        Tier 10.4: Called after successful exchange with peer.
        Prevents duplicate syncing of same operations.

        Args:
            op_ids: List of operation IDs that were synced
        """
        mark_operations_synced(self.sync_db_path, op_ids)

    async def track_operation(self,
                             table_name: str,
                             operation: str,
                             row_id: Any,
                             data: Optional[dict] = None,
                             team_id: Optional[str] = None) -> None:
        """
        Track a local database operation for syncing

        Call this after INSERT, UPDATE, DELETE operations

        Phase 4: If team_id is provided, signs the operation payload
        """
        self.local_version += 1

        op = SyncOperation(
            op_id=self._generate_op_id(),
            table_name=table_name,
            operation=operation,
            row_id=str(row_id),
            data=data,
            timestamp=datetime.now(UTC).isoformat(),
            peer_id=self.local_peer_id,
            version=self.local_version,
            team_id=team_id
        )

        # Phase 4: Sign payload for team operations
        if team_id:
            op.signature = sign_payload(op.to_payload(), team_id)
            logger.debug(f"🔐 Signed team operation {op.op_id} for team {team_id}")
        else:
            op.signature = ""

        # Save to sync log using extracted function
        save_sync_operation(self.sync_db_path, op)

        self.pending_operations.append(op)
        logger.debug(f"📝 Tracked {operation} on {table_name}:{row_id}")

    async def sync_with_peer(self,
                            peer_id: str,
                            tables: Optional[List[str]] = None) -> SyncState:
        """
        Synchronize data with a peer

        Args:
            peer_id: ID of peer to sync with
            tables: Optional list of tables to sync (None = all)

        Returns:
            SyncState after sync
        """
        logger.info(f"🔄 Starting sync with peer {peer_id}...")

        # Get or create sync state
        if peer_id not in self.sync_states:
            self.sync_states[peer_id] = SyncState(
                peer_id=peer_id,
                last_sync=None,
                operations_sent=0,
                operations_received=0,
                conflicts_resolved=0,
                status='idle'
            )

        state = self.sync_states[peer_id]
        state.status = 'syncing'

        try:
            # Step 1: Get operations to send
            ops_to_send = await self._get_operations_since_last_sync(peer_id, tables)

            # Step 2: Send operations to peer
            logger.info(f"📤 Sending {len(ops_to_send)} operations to {peer_id}")
            ops_received = await self._exchange_operations_with_peer(peer_id, ops_to_send)
            state.operations_sent += len(ops_to_send)

            # Step 2.5: Mark sent operations as synced (Tier 10.4)
            if ops_to_send:
                synced_op_ids = [op.op_id for op in ops_to_send]
                self._mark_operations_synced(synced_op_ids)
                # Remove from in-memory queue
                self.pending_operations = [
                    op for op in self.pending_operations
                    if op.op_id not in synced_op_ids
                ]

            # Step 3: Operations received from peer during exchange
            logger.info(f"📥 Received {len(ops_received)} operations from {peer_id}")

            # Step 4: Apply received operations
            conflicts = await self._apply_operations(ops_received)
            state.operations_received += len(ops_received)
            state.conflicts_resolved += conflicts

            # Step 5: Update sync state
            state.last_sync = datetime.now(UTC).isoformat()
            state.status = 'idle'

            await self._save_sync_state(state)

            logger.info(f"✅ Sync completed with {peer_id}")
            return state

        except Exception as e:
            state.status = 'error'
            logger.error(f"❌ Sync failed with {peer_id}: {e}")
            raise

    async def _get_operations_since_last_sync(self,
                                             peer_id: str,
                                             tables: Optional[List[str]] = None) -> List[SyncOperation]:
        """Get operations that haven't been synced to peer yet"""
        last_sync = get_peer_last_sync(self.sync_db_path, peer_id)
        return get_operations_since(
            self.sync_db_path,
            self.local_peer_id,
            last_sync=last_sync,
            tables=tables
        )

    async def _apply_operations(self, operations: List[SyncOperation], user_id: Optional[str] = None) -> int:
        """
        Apply operations from peer to local database

        Phase 4: Validates team signatures and team membership before applying

        Args:
            operations: Operations to apply
            user_id: Optional user ID for team membership checks

        Returns:
            Number of conflicts resolved
        """
        conflicts = 0
        conn = sqlite3.connect(str(self.db_path))

        for op in operations:
            try:
                # Phase 4: Team boundary enforcement
                if op.team_id:
                    # Verify signature
                    payload_to_verify = {
                        "op_id": op.op_id,
                        "table_name": op.table_name,
                        "operation": op.operation,
                        "row_id": op.row_id,
                        "data": op.data,
                        "timestamp": op.timestamp,
                        "peer_id": op.peer_id,
                        "version": op.version,
                        "team_id": op.team_id
                    }

                    if not verify_payload(payload_to_verify, op.signature, op.team_id):
                        logger.warning(f"🚫 Rejected operation {op.op_id}: invalid team signature for team {op.team_id}")
                        continue

                    # Check team membership (if user_id provided)
                    if user_id and not is_team_member(op.team_id, user_id):
                        logger.warning(f"🚫 Rejected operation {op.op_id}: user {user_id} not in team {op.team_id}")
                        continue

                    logger.debug(f"✅ Team operation {op.op_id} verified for team {op.team_id}")

                # Check for conflict
                if await self._has_conflict(op):
                    # Resolve conflict using Last-Write-Wins
                    if await self._should_apply_operation(op):
                        await self._execute_operation(conn, op)
                        conflicts += 1
                        logger.debug(f"⚠️ Conflict resolved: {op.table_name}:{op.row_id}")
                    else:
                        logger.debug(f"⚠️ Conflict ignored (older): {op.table_name}:{op.row_id}")
                else:
                    # No conflict - apply directly
                    await self._execute_operation(conn, op)

                # Update version tracking
                await self._update_version_tracking(op)

            except Exception as e:
                logger.error(f"Failed to apply operation {op.op_id}: {e}")

        conn.commit()
        conn.close()

        return conflicts

    async def _has_conflict(self, op: SyncOperation) -> bool:
        """Check if operation conflicts with local data"""
        return check_version_conflict(
            self.sync_db_path,
            op.table_name,
            op.row_id,
            op.peer_id
        )

    async def _should_apply_operation(self, op: SyncOperation) -> bool:
        """
        Determine if conflicting operation should be applied (Last-Write-Wins)
        """
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version, timestamp FROM version_tracking
            WHERE table_name = ? AND row_id = ?
            ORDER BY version DESC LIMIT 1
        """, (op.table_name, op.row_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return True  # No existing version - apply

        existing_version, existing_timestamp = row

        # Compare timestamps (Last-Write-Wins)
        if op.timestamp > existing_timestamp:
            return True

        # If timestamps equal, use peer_id as tiebreaker
        if op.timestamp == existing_timestamp:
            return op.peer_id > self.local_peer_id

        return False

    async def _execute_operation(self, conn: sqlite3.Connection, op: SyncOperation) -> None:
        """Execute database operation with SQL injection protection"""
        cursor = conn.cursor()

        # SECURITY: Validate table name against allowlist (critical for P2P data)
        if op.table_name not in SYNCABLE_TABLES:
            logger.error(f"⛔ Blocked sync to non-syncable table: {op.table_name}")
            raise ValueError(f"Table not syncable: {op.table_name}")

        # Defense-in-depth: quote the table name
        safe_table = quote_identifier(op.table_name)

        try:
            if op.operation == 'insert':
                # Build INSERT statement
                columns = list(op.data.keys())

                # Validate and quote column names
                safe_columns = []
                for col in columns:
                    if not re.match(r'^[a-zA-Z0-9_]+$', col):
                        logger.error(f"Invalid column name from P2P: {col}")
                        raise ValueError(f"Invalid column name: {col}")
                    safe_columns.append(quote_identifier(col))

                placeholders = ','.join('?' * len(columns))
                column_names = ','.join(safe_columns)

                cursor.execute(f"""
                    INSERT OR REPLACE INTO {safe_table} ({column_names})
                    VALUES ({placeholders})
                """, list(op.data.values()))

            elif op.operation == 'update':
                # Validate and quote column names
                set_parts = []
                for col in op.data.keys():
                    if not re.match(r'^[a-zA-Z0-9_]+$', col):
                        logger.error(f"Invalid column name from P2P: {col}")
                        raise ValueError(f"Invalid column name: {col}")
                    set_parts.append(f"{quote_identifier(col)} = ?")

                set_clause = ','.join(set_parts)

                cursor.execute(f"""
                    UPDATE {safe_table}
                    SET {set_clause}
                    WHERE rowid = ?
                """, list(op.data.values()) + [op.row_id])

            elif op.operation == 'delete':
                cursor.execute(f"""
                    DELETE FROM {safe_table}
                    WHERE rowid = ?
                """, (op.row_id,))

        except Exception as e:
            logger.error(f"Failed to execute {op.operation} on {op.table_name}: {e}")
            raise

    async def _update_version_tracking(self, op: SyncOperation) -> None:
        """Update version tracking for conflict detection"""
        update_version_tracking(self.sync_db_path, op)

    async def _exchange_operations_with_peer(self,
                                             peer_id: str,
                                             operations_to_send: List[SyncOperation]) -> List[SyncOperation]:
        """
        Exchange sync operations with peer via HTTP

        Args:
            peer_id: Peer to sync with
            operations_to_send: Our operations to send

        Returns:
            Operations received from peer
        """
        try:
            # Import here to avoid circular dependency
            from offline_mesh_discovery import get_mesh_discovery

            # Get peer info from discovery
            discovery = get_mesh_discovery()
            peer = discovery.get_peer_by_id(peer_id)

            if not peer:
                logger.warning(f"Peer {peer_id} not found in discovery")
                return []

            # Prepare payload
            import aiohttp
            payload = {
                'sender_peer_id': self.local_peer_id,
                'operations': [
                    {
                        'op_id': op.op_id,
                        'table_name': op.table_name,
                        'operation': op.operation,
                        'row_id': op.row_id,
                        'data': op.data,
                        'timestamp': op.timestamp,
                        'peer_id': op.peer_id,
                        'version': op.version,
                        'team_id': op.team_id,
                        'signature': op.signature
                    }
                    for op in operations_to_send
                ]
            }

            # Send to peer's sync endpoint
            url = f"http://{peer.ip_address}:{peer.port}/api/v1/mesh/sync/exchange"
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Sync exchange failed with {peer_id}: HTTP {response.status}")
                        return []

                    result = await response.json()

                    # Parse received operations
                    received_ops = []
                    for op_data in result.get('operations', []):
                        op = SyncOperation(
                            op_id=op_data['op_id'],
                            table_name=op_data['table_name'],
                            operation=op_data['operation'],
                            row_id=op_data['row_id'],
                            data=op_data.get('data'),
                            timestamp=op_data['timestamp'],
                            peer_id=op_data['peer_id'],
                            version=op_data['version'],
                            team_id=op_data.get('team_id'),
                            signature=op_data.get('signature', '')
                        )
                        received_ops.append(op)

                    logger.info(f"✅ Exchanged operations with {peer_id}: sent {len(operations_to_send)}, received {len(received_ops)}")
                    return received_ops

        except Exception as e:
            logger.error(f"Failed to exchange operations with {peer_id}: {e}")
            return []

    async def _save_sync_state(self, state: SyncState) -> None:
        """Save sync state to database"""
        save_sync_state(self.sync_db_path, state)

    def _generate_op_id(self) -> str:
        """Generate unique operation ID using UUID"""
        import uuid
        return str(uuid.uuid4())

    def get_sync_state(self, peer_id: str) -> Optional[SyncState]:
        """Get sync state with a specific peer by ID"""
        return self.sync_states.get(peer_id)

    def get_all_sync_states(self) -> List[SyncState]:
        """Get all peer sync states as a list"""
        return list(self.sync_states.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get sync statistics"""
        total_sent = sum(s.operations_sent for s in self.sync_states.values())
        total_received = sum(s.operations_received for s in self.sync_states.values())
        total_conflicts = sum(s.conflicts_resolved for s in self.sync_states.values())

        return {
            'local_peer_id': self.local_peer_id,
            'local_version': self.local_version,
            'synced_peers': len(self.sync_states),
            'pending_operations': len(self.pending_operations),
            'total_operations_sent': total_sent,
            'total_operations_received': total_received,
            'total_conflicts_resolved': total_conflicts,
            'db_path': str(self.db_path),
            'sync_db_path': str(self.sync_db_path)
        }


# Singleton instance
_data_sync = None


def get_data_sync(db_path: Path = None, local_peer_id: str = None) -> OfflineDataSync:
    """Get singleton data sync instance"""
    global _data_sync

    if _data_sync is None:
        if not db_path:
            from config_paths import get_config_paths
            paths = get_config_paths()
            db_path = paths.app_db

        if not local_peer_id:
            import hashlib
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            local_peer_id = hashlib.sha256(mac.encode()).hexdigest()[:16]

        _data_sync = OfflineDataSync(db_path, local_peer_id)
        logger.info("🔄 Offline data sync ready")

    return _data_sync


__all__ = [
    # Re-exported from offline_sync_models.py (backward compatibility)
    "SYNCABLE_TABLES",
    "SyncOperation",
    "SyncState",
    "SYNC_OPERATIONS_SCHEMA",
    "PEER_SYNC_STATE_SCHEMA",
    "VERSION_TRACKING_SCHEMA",
    # Re-exported from offline_sync_db.py (backward compatibility)
    "get_sync_db_path",
    "init_sync_db",
    "save_sync_operation",
    "load_pending_operations",
    "mark_operations_synced",
    "get_max_version",
    "get_peer_last_sync",
    "save_sync_state",
    "load_sync_state",
    "check_version_conflict",
    "update_version_tracking",
    "get_operations_since",
    # Main class and singleton
    "OfflineDataSync",
    "get_data_sync",
]
