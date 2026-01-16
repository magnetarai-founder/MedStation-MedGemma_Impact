"""
P2P Mesh Database - Database operations for connection codes

Provides persistent storage for:
- Connection codes (survives app restarts)
- Code expiration tracking

Extracted from p2p_mesh_service.py during P2 decomposition.
"""

from __future__ import annotations

import json
import sqlite3
import logging
import secrets
import string
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from api.config_paths import get_config_paths
from api.p2p_mesh.models import ConnectionCode

logger = logging.getLogger(__name__)


# ===== Configuration =====

PATHS = get_config_paths()
CODES_DB_PATH = PATHS.data_dir / "p2p_connection_codes.db"


# ===== Database Initialization =====

def init_codes_db() -> None:
    """
    Initialize database for connection codes.

    Creates the connection_codes table if it doesn't exist.
    Safe to call multiple times (idempotent).
    """
    CODES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS connection_codes (
                code TEXT PRIMARY KEY,
                peer_id TEXT NOT NULL,
                multiaddrs TEXT NOT NULL,
                expires_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_connection_code(code: str, connection: ConnectionCode) -> None:
    """
    Save connection code to persistent storage.

    Uses INSERT OR REPLACE for upsert behavior.

    Args:
        code: The connection code string
        connection: ConnectionCode model with peer info
    """
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO connection_codes (code, peer_id, multiaddrs, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            code,
            connection.peer_id,
            json.dumps(connection.multiaddrs),
            connection.expires_at,
            datetime.now().isoformat()
        ))
        conn.commit()


def load_connection_codes() -> Dict[str, ConnectionCode]:
    """
    Load all valid (non-expired) connection codes from database.

    Returns:
        Dict mapping code strings to ConnectionCode models
    """
    codes: Dict[str, ConnectionCode] = {}
    try:
        with sqlite3.connect(str(CODES_DB_PATH)) as conn:
            cursor = conn.execute("""
                SELECT code, peer_id, multiaddrs, expires_at
                FROM connection_codes
                WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')
            """)
            for row in cursor.fetchall():
                code, peer_id, multiaddrs_json, expires_at = row
                codes[code] = ConnectionCode(
                    code=code,
                    peer_id=peer_id,
                    multiaddrs=json.loads(multiaddrs_json),
                    expires_at=expires_at
                )
    except Exception as e:
        logger.error(f"Failed to load connection codes: {e}")
    return codes


def delete_connection_code(code: str) -> bool:
    """
    Delete a connection code from the database.

    Args:
        code: The connection code to delete

    Returns:
        True if code was deleted, False if not found
    """
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        cursor = conn.execute(
            "DELETE FROM connection_codes WHERE code = ?",
            (code,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_connection_code(code: str) -> Optional[ConnectionCode]:
    """
    Get a single connection code by its code string.

    Args:
        code: The connection code to look up

    Returns:
        ConnectionCode if found and not expired, None otherwise
    """
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        cursor = conn.execute("""
            SELECT code, peer_id, multiaddrs, expires_at
            FROM connection_codes
            WHERE code = ? AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
        """, (code,))
        row = cursor.fetchone()
        if row:
            code_str, peer_id, multiaddrs_json, expires_at = row
            return ConnectionCode(
                code=code_str,
                peer_id=peer_id,
                multiaddrs=json.loads(multiaddrs_json),
                expires_at=expires_at
            )
    return None


def cleanup_expired_codes() -> int:
    """
    Remove expired connection codes from the database.

    Returns:
        Number of codes removed
    """
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        cursor = conn.execute("""
            DELETE FROM connection_codes
            WHERE expires_at IS NOT NULL AND datetime(expires_at) <= datetime('now')
        """)
        conn.commit()
        return cursor.rowcount


def count_connection_codes() -> int:
    """
    Count total valid connection codes.

    Returns:
        Number of non-expired codes
    """
    with sqlite3.connect(str(CODES_DB_PATH)) as conn:
        cursor = conn.execute("""
            SELECT COUNT(*) FROM connection_codes
            WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')
        """)
        return cursor.fetchone()[0]


# ===== Code Generation =====

def generate_connection_code() -> str:
    """
    Generate a human-readable connection code.

    Format: OMNI-XXXX-XXXX (8 random alphanumeric characters)

    Returns:
        Generated connection code string
    """
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"OMNI-{part1}-{part2}"


__all__ = [
    # Configuration
    "PATHS",
    "CODES_DB_PATH",
    # Initialization
    "init_codes_db",
    # CRUD operations
    "save_connection_code",
    "load_connection_codes",
    "delete_connection_code",
    "get_connection_code",
    # Maintenance
    "cleanup_expired_codes",
    "count_connection_codes",
    # Generation
    "generate_connection_code",
]
