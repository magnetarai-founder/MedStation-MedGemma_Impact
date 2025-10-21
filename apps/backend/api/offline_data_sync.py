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
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


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

        logger.info(f"🔄 Data sync initialized for peer {local_peer_id}")

    def _init_sync_db(self):
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

    async def track_operation(self,
                             table_name: str,
                             operation: str,
                             row_id: Any,
                             data: Optional[dict] = None):
        """
        Track a local database operation for syncing

        Call this after INSERT, UPDATE, DELETE operations
        """
        self.local_version += 1

        op = SyncOperation(
            op_id=self._generate_op_id(),
            table_name=table_name,
            operation=operation,
            row_id=str(row_id),
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            peer_id=self.local_peer_id,
            version=self.local_version
        )

        # Save to sync log
        conn = sqlite3.connect(str(self.sync_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sync_operations
            (op_id, table_name, operation, row_id, data, timestamp, peer_id, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            op.op_id,
            op.table_name,
            op.operation,
            op.row_id,
            json.dumps(op.data) if op.data else None,
            op.timestamp,
            op.peer_id,
            op.version
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
            # TODO: Implement actual network send via WebSocket/HTTP
            logger.info(f"📤 Sending {len(ops_to_send)} operations to {peer_id}")
            state.operations_sent += len(ops_to_send)

            # Step 3: Receive operations from peer
            # TODO: Implement actual network receive
            ops_received = []  # Placeholder
            logger.info(f"📥 Received {len(ops_received)} operations from {peer_id}")

            # Step 4: Apply received operations
            conflicts = await self._apply_operations(ops_received)
            state.operations_received += len(ops_received)
            state.conflicts_resolved += conflicts

            # Step 5: Update sync state
            state.last_sync = datetime.utcnow().isoformat()
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
            SELECT op_id, table_name, operation, row_id, data, timestamp, peer_id, version
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
                version=row[7]
            )
            operations.append(op)

        conn.close()
        return operations

    async def _apply_operations(self, operations: List[SyncOperation]) -> int:
        """
        Apply operations from peer to local database

        Returns number of conflicts resolved
        """
        conflicts = 0
        conn = sqlite3.connect(str(self.db_path))

        for op in operations:
            try:
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

    async def _execute_operation(self, conn: sqlite3.Connection, op: SyncOperation):
        """Execute database operation"""
        cursor = conn.cursor()

        try:
            if op.operation == 'insert':
                # Build INSERT statement
                columns = list(op.data.keys())
                placeholders = ','.join('?' * len(columns))
                column_names = ','.join(columns)

                cursor.execute(f"""
                    INSERT OR REPLACE INTO {op.table_name} ({column_names})
                    VALUES ({placeholders})
                """, list(op.data.values()))

            elif op.operation == 'update':
                # Build UPDATE statement
                set_clause = ','.join(f"{k} = ?" for k in op.data.keys())

                cursor.execute(f"""
                    UPDATE {op.table_name}
                    SET {set_clause}
                    WHERE rowid = ?
                """, list(op.data.values()) + [op.row_id])

            elif op.operation == 'delete':
                cursor.execute(f"""
                    DELETE FROM {op.table_name}
                    WHERE rowid = ?
                """, (op.row_id,))

        except Exception as e:
            logger.error(f"Failed to execute {op.operation} on {op.table_name}: {e}")
            raise

    async def _update_version_tracking(self, op: SyncOperation):
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

    async def _save_sync_state(self, state: SyncState):
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
        """Generate unique operation ID"""
        import uuid
        return str(uuid.uuid4())

    def get_sync_state(self, peer_id: str) -> Optional[SyncState]:
        """Get sync state with a specific peer"""
        return self.sync_states.get(peer_id)

    def get_all_sync_states(self) -> List[SyncState]:
        """Get all peer sync states"""
        return list(self.sync_states.values())

    def get_stats(self) -> dict:
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
            db_path = Path.home() / ".omnistudio" / "omnistudio.db"

        if not local_peer_id:
            import hashlib
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            local_peer_id = hashlib.sha256(mac.encode()).hexdigest()[:16]

        _data_sync = OfflineDataSync(db_path, local_peer_id)
        logger.info("🔄 Offline data sync ready")

    return _data_sync
