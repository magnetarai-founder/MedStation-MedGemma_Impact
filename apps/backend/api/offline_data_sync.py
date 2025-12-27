#!/usr/bin/env python3
"""
Offline Data Sync for ElohimOS
Sync databases, query results, chat history across missionary team
Uses CRDTs for conflict-free synchronization
"""

import asyncio
import json
import sqlite3
import logging
import re
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
import hashlib

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
    """A single sync operation"""
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


@dataclass
class SyncState:
    """Synchronization state with a peer"""
    peer_id: str
    last_sync: str
    operations_sent: int
    operations_received: int
    conflicts_resolved: int
    status: str  # 'syncing', 'idle', 'error'


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

        # Initialize sync metadata database
        self.sync_db_path = db_path.parent / f"{db_path.stem}_sync.db"
        self._init_sync_db()

        # Load any pending operations from previous session (Tier 10.4)
        self._load_pending_operations()

        logger.info(f"🔄 Data sync initialized for peer {local_peer_id}")

    def _init_sync_db(self) -> None:
        """Initialize sync metadata database"""
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        # Sync operations log
        cursor.execute("""
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
        """)

        # Peer sync state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_sync_state (
                peer_id TEXT PRIMARY KEY,
                last_sync TEXT,
                operations_sent INTEGER DEFAULT 0,
                operations_received INTEGER DEFAULT 0,
                conflicts_resolved INTEGER DEFAULT 0,
                status TEXT DEFAULT 'idle',
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Version tracking (vector clocks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_tracking (
                table_name TEXT,
                row_id TEXT,
                peer_id TEXT,
                version INTEGER,
                timestamp TEXT,
                PRIMARY KEY (table_name, row_id, peer_id)
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"✅ Sync database initialized: {self.sync_db_path}")

    def _load_pending_operations(self) -> None:
        """
        Load pending (unsynced) operations from database on startup.

        Tier 10.4: Ensures sync operations survive app restarts.
        Operations are retried automatically when sync resumes.
        """
        conn = sqlite3.connect(str(self.sync_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT op_id, table_name, operation, row_id, data, timestamp,
                   peer_id, version, team_id, signature
            FROM sync_operations
            WHERE synced = 0 AND peer_id = ?
            ORDER BY version ASC
        """, (self.local_peer_id,))

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
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
            self.pending_operations.append(op)

            # Update local_version to highest seen version
            if row['version'] > self.local_version:
                self.local_version = row['version']

        if rows:
            logger.info(f"📥 Loaded {len(rows)} pending sync operations from previous session")

    def _mark_operations_synced(self, op_ids: list[str]) -> None:
        """
        Mark operations as successfully synced.

        Tier 10.4: Called after successful exchange with peer.
        Prevents duplicate syncing of same operations.

        Args:
            op_ids: List of operation IDs that were synced
        """
        if not op_ids:
            return

        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        placeholders = ','.join('?' for _ in op_ids)
        cursor.execute(f"""
            UPDATE sync_operations
            SET synced = 1
            WHERE op_id IN ({placeholders})
        """, op_ids)

        conn.commit()
        conn.close()

        logger.debug(f"✅ Marked {len(op_ids)} operations as synced")

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
            payload_to_sign = {
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
            op.signature = sign_payload(payload_to_sign, team_id)
            logger.debug(f"🔐 Signed team operation {op.op_id} for team {team_id}")
        else:
            op.signature = ""

        # Save to sync log
        conn = sqlite3.connect(str(self.sync_db_path))
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
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        # Get last sync time
        cursor.execute("""
            SELECT last_sync FROM peer_sync_state WHERE peer_id = ?
        """, (peer_id,))

        row = cursor.fetchone()
        last_sync = row[0] if row else None

        # Build query
        query = """
            SELECT op_id, table_name, operation, row_id, data, timestamp, peer_id, version, team_id, signature
            FROM sync_operations
            WHERE peer_id = ?
        """
        params = [self.local_peer_id]

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
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM version_tracking
            WHERE table_name = ? AND row_id = ? AND peer_id != ?
        """, (op.table_name, op.row_id, op.peer_id))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

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
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO version_tracking
            (table_name, row_id, peer_id, version, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (op.table_name, op.row_id, op.peer_id, op.version, op.timestamp))

        conn.commit()
        conn.close()

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
        conn = sqlite3.connect(str(self.sync_db_path))
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
