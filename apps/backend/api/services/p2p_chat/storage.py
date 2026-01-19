"""
P2P Chat Service - Storage Layer

SQLite database operations for P2P chat:
- Peers, channels, messages, file transfers
- Device keys, peer keys, safety number changes
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from api.db.pool import get_connection_pool

logger = logging.getLogger(__name__)


def init_db(db_path: Path) -> None:
    """
    Initialize SQLite database schema for P2P chat.

    Creates tables for:
    - peers: Connected peer devices
    - channels: Chat channels (group/DM)
    - messages: Chat messages with E2E encryption metadata
    - file_transfers: File transfer progress tracking
    - device_keys: Local device E2E encryption keys
    - peer_keys: Peer public keys and fingerprints
    - safety_number_changes: Safety number change audit log

    Args:
        db_path: Path to SQLite database file
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()

        # Peers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peers (
                peer_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                device_name TEXT NOT NULL,
                public_key TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TEXT,
                avatar_hash TEXT,
                bio TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT,
                created_by TEXT,
                description TEXT,
                topic TEXT,
                members TEXT,  -- JSON array
                admins TEXT,   -- JSON array
                dm_participants TEXT  -- JSON array for DMs
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT TRUE,
                timestamp TEXT NOT NULL,
                edited_at TEXT,
                file_metadata TEXT,  -- JSON
                thread_id TEXT,
                reply_to TEXT,
                reactions TEXT,  -- JSON
                delivered_to TEXT,  -- JSON array
                read_by TEXT,  -- JSON array
                FOREIGN KEY (channel_id) REFERENCES channels (id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")

        # File transfers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_transfers (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                mime_type TEXT,
                sender_id TEXT,
                recipient_ids TEXT,  -- JSON array
                channel_id TEXT,
                chunks_total INTEGER,
                chunks_received INTEGER DEFAULT 0,
                progress_percent REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                local_path TEXT
            )
        """)

        # E2E Encryption: Device keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_keys (
                device_id TEXT PRIMARY KEY,
                public_key BLOB NOT NULL,
                fingerprint BLOB NOT NULL,
                verify_key BLOB NOT NULL,
                created_at TEXT NOT NULL,
                last_used TEXT
            )
        """)

        # E2E Encryption: Peer keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_keys (
                peer_device_id TEXT PRIMARY KEY,
                public_key BLOB NOT NULL,
                fingerprint BLOB NOT NULL,
                verify_key BLOB NOT NULL,
                verified BOOLEAN DEFAULT 0,
                verified_at TEXT,
                safety_number TEXT,
                first_seen TEXT NOT NULL,
                last_key_change TEXT
            )
        """)

        # E2E Encryption: Safety number changes tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_number_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_device_id TEXT NOT NULL,
                old_safety_number TEXT,
                new_safety_number TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT 0,
                acknowledged_at TEXT,
                FOREIGN KEY (peer_device_id) REFERENCES peer_keys(peer_device_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_safety_changes_peer ON safety_number_changes(peer_device_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_safety_changes_ack ON safety_number_changes(acknowledged)")

        conn.commit()

    logger.info("Database initialized")


# ===== Peer Storage Operations =====

def save_peer(db_path: Path, peer_id: str, display_name: str, device_name: str,
              public_key: Optional[str] = None, status: str = 'online') -> None:
    """Save or update a peer in the database."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO peers
            (peer_id, display_name, device_name, public_key, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (peer_id, display_name, device_name, public_key, status, datetime.now(UTC).isoformat()))
        conn.commit()


def update_peer_status(db_path: Path, peer_id: str, status: str) -> None:
    """Update peer status (online/offline)."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE peers SET status = ?, last_seen = ? WHERE peer_id = ?
        """, (status, datetime.now(UTC).isoformat(), peer_id))
        conn.commit()


def get_peers(db_path: Path) -> List[Dict[str, Any]]:
    """Get all peers from database."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM peers ORDER BY last_seen DESC")
        rows = cursor.fetchall()
    return [dict(row) for row in rows]


# ===== Channel Storage Operations =====

def save_channel(db_path: Path, channel_id: str, name: str, channel_type: str,
                 created_by: str, members: List[str], admins: List[str],
                 dm_participants: Optional[List[str]] = None,
                 description: Optional[str] = None, topic: Optional[str] = None) -> None:
    """Save a channel to the database."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO channels
            (id, name, type, created_at, created_by, description, topic, members, admins, dm_participants)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            channel_id, name, channel_type, datetime.now(UTC).isoformat(), created_by,
            description, topic, json.dumps(members), json.dumps(admins),
            json.dumps(dm_participants) if dm_participants else None
        ))
        conn.commit()


def get_channel(db_path: Path, channel_id: str) -> Optional[Dict[str, Any]]:
    """Get a channel by ID."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()

    if row:
        channel = dict(row)
        # Parse JSON fields
        channel['members'] = json.loads(channel['members']) if channel['members'] else []
        channel['admins'] = json.loads(channel['admins']) if channel['admins'] else []
        if channel['dm_participants']:
            channel['dm_participants'] = json.loads(channel['dm_participants'])
        return channel
    return None


def list_channels(db_path: Path) -> List[Dict[str, Any]]:
    """List all channels."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels ORDER BY created_at DESC")
        rows = cursor.fetchall()

    channels = []
    for row in rows:
        channel = dict(row)
        channel['members'] = json.loads(channel['members']) if channel['members'] else []
        channel['admins'] = json.loads(channel['admins']) if channel['admins'] else []
        if channel['dm_participants']:
            channel['dm_participants'] = json.loads(channel['dm_participants'])
        channels.append(channel)

    return channels


# ===== Message Storage Operations =====

def save_message(db_path: Path, message_id: str, channel_id: str, sender_id: str,
                 sender_name: str, message_type: str, content: str, timestamp: str,
                 encrypted: bool = True, file_metadata: Optional[Dict] = None,
                 thread_id: Optional[str] = None, reply_to: Optional[str] = None) -> None:
    """Save a message to the database."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO messages
            (id, channel_id, sender_id, sender_name, type, content, encrypted,
             timestamp, file_metadata, thread_id, reply_to, delivered_to, read_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, channel_id, sender_id, sender_name, message_type, content,
            encrypted, timestamp,
            json.dumps(file_metadata) if file_metadata else None,
            thread_id, reply_to, json.dumps([]), json.dumps([])
        ))
        conn.commit()


def get_messages(db_path: Path, channel_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get messages for a channel."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (channel_id, limit, offset))
        rows = cursor.fetchall()

    messages = []
    for row in rows:
        msg = dict(row)
        # Parse JSON fields
        if msg['file_metadata']:
            msg['file_metadata'] = json.loads(msg['file_metadata'])
        if msg['reactions']:
            msg['reactions'] = json.loads(msg['reactions'])
        msg['delivered_to'] = json.loads(msg['delivered_to']) if msg['delivered_to'] else []
        msg['read_by'] = json.loads(msg['read_by']) if msg['read_by'] else []
        messages.append(msg)

    return messages


def mark_message_delivered(db_path: Path, message_id: str, peer_id: str) -> None:
    """Mark a message as delivered to a peer."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        # Get current delivered_to list
        cursor.execute("SELECT delivered_to FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()

        if row:
            delivered_to = json.loads(row[0]) if row[0] else []
            if peer_id not in delivered_to:
                delivered_to.append(peer_id)
                cursor.execute("UPDATE messages SET delivered_to = ? WHERE id = ?",
                             (json.dumps(delivered_to), message_id))
                conn.commit()


def mark_message_read(db_path: Path, message_id: str, peer_id: str) -> None:
    """Mark a message as read by a peer."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        # Get current read_by list
        cursor.execute("SELECT read_by FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()

        if row:
            read_by = json.loads(row[0]) if row[0] else []
            if peer_id not in read_by:
                read_by.append(peer_id)
                cursor.execute("UPDATE messages SET read_by = ? WHERE id = ?",
                             (json.dumps(read_by), message_id))
                conn.commit()


# ===== File Transfer Storage Operations =====

def save_file_transfer(db_path: Path, transfer_id: str, file_name: str, file_size: int,
                       mime_type: str, sender_id: str, channel_id: str,
                       recipient_ids: List[str], chunks_total: int) -> None:
    """Save a file transfer record."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO file_transfers
            (id, file_name, file_size, mime_type, sender_id, recipient_ids, channel_id,
             chunks_total, started_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transfer_id, file_name, file_size, mime_type, sender_id,
            json.dumps(recipient_ids), channel_id, chunks_total,
            datetime.now(UTC).isoformat(), 'active'
        ))
        conn.commit()


def update_file_transfer_progress(db_path: Path, transfer_id: str, chunks_received: int,
                                  progress_percent: float, status: str = 'active') -> None:
    """Update file transfer progress."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        completed_at = datetime.now(UTC).isoformat() if status == 'completed' else None
        cursor.execute("""
            UPDATE file_transfers
            SET chunks_received = ?, progress_percent = ?, status = ?, completed_at = ?
            WHERE id = ?
        """, (chunks_received, progress_percent, status, completed_at, transfer_id))
        conn.commit()


def get_file_transfer(db_path: Path, transfer_id: str) -> Optional[Dict[str, Any]]:
    """Get file transfer by ID."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM file_transfers WHERE id = ?", (transfer_id,))
        row = cursor.fetchone()

    if row:
        transfer = dict(row)
        transfer['recipient_ids'] = json.loads(transfer['recipient_ids']) if transfer['recipient_ids'] else []
        return transfer
    return None


def list_active_transfers(db_path: Path) -> List[Dict[str, Any]]:
    """List all active (non-completed) file transfers."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM file_transfers
            WHERE status IN ('pending', 'active', 'paused')
            ORDER BY started_at DESC
        """)
        rows = cursor.fetchall()

    transfers = []
    for row in rows:
        transfer = dict(row)
        transfer['recipient_ids'] = json.loads(transfer['recipient_ids']) if transfer['recipient_ids'] else []
        transfers.append(transfer)
    return transfers


def set_transfer_local_path(db_path: Path, transfer_id: str, local_path: str) -> None:
    """Set the local file path for a transfer (used when receiving)."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE file_transfers SET local_path = ? WHERE id = ?", (local_path, transfer_id))
        conn.commit()


def set_transfer_hash(db_path: Path, transfer_id: str, file_hash: str) -> None:
    """Set the SHA-256 hash for a file transfer."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE file_transfers SET file_hash = ? WHERE id = ?", (file_hash, transfer_id))
        conn.commit()


def cancel_transfer(db_path: Path, transfer_id: str) -> None:
    """Cancel a file transfer."""
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE file_transfers
            SET status = 'cancelled', completed_at = ?
            WHERE id = ?
        """, (datetime.now(UTC).isoformat(), transfer_id))
        conn.commit()


def get_pending_chunks(db_path: Path, transfer_id: str) -> List[int]:
    """Get list of chunk indices that haven't been received yet."""
    transfer = get_file_transfer(db_path, transfer_id)
    if not transfer:
        return []

    chunks_total = transfer.get('chunks_total', 0)
    chunks_received = transfer.get('chunks_received', 0)

    # For simplicity, assume sequential receiving (chunk 0, 1, 2...)
    # In production, you'd track individual chunk indices
    return list(range(chunks_received, chunks_total))
