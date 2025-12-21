"""
P2P Chat Service - E2E Encryption Integration

Handles device key management, peer key storage, safety number generation,
and safety number change tracking for Signal-style E2E encryption.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


def get_e2e_service():
    """Get the E2E encryption service singleton."""
    try:
        from api.e2e_encryption_service import get_e2e_service
        return get_e2e_service()
    except ImportError:
        from e2e_encryption_service import get_e2e_service
        return get_e2e_service()


def init_device_keys(db_path: Path, device_id: str, passphrase: str) -> Dict:
    """
    Initialize E2E encryption keys for this device.

    Args:
        db_path: Path to P2P chat database
        device_id: Unique device identifier
        passphrase: User's passphrase for Secure Enclave

    Returns:
        Dict with public_key and fingerprint
    """
    e2e_service = get_e2e_service()

    try:
        # Try to load existing keys first
        public_key, fingerprint = e2e_service.load_identity_keypair(device_id, passphrase)
        logger.info(f"Loaded existing E2E keys for device {device_id}")
    except (FileNotFoundError, ValueError, KeyError):
        # Generate new keys if they don't exist or are invalid
        public_key, fingerprint = e2e_service.generate_identity_keypair(device_id, passphrase)
        logger.info(f"Generated new E2E keys for device {device_id}")

    # Store in database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO device_keys
        (device_id, public_key, fingerprint, verify_key, created_at, last_used)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        device_id,
        public_key,
        fingerprint,
        bytes(e2e_service._signing_keypair.verify_key) if e2e_service._signing_keypair else b'',
        datetime.now(UTC).isoformat(),
        datetime.now(UTC).isoformat()
    ))

    conn.commit()
    conn.close()

    return {
        "public_key": public_key.hex(),
        "fingerprint": e2e_service.format_fingerprint(fingerprint),
        "device_id": device_id
    }


def store_peer_key(db_path: Path, peer_device_id: str, public_key: bytes, verify_key: bytes) -> Dict:
    """
    Store a peer's public key and generate safety number.

    Args:
        db_path: Path to P2P chat database
        peer_device_id: Peer's device identifier
        public_key: Peer's Curve25519 public key
        verify_key: Peer's Ed25519 verify key

    Returns:
        Dict with safety_number and fingerprint
    """
    e2e_service = get_e2e_service()
    fingerprint = e2e_service.generate_fingerprint(public_key)

    # Get our public key to generate safety number
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT public_key FROM device_keys LIMIT 1")
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise RuntimeError("Device keys not initialized. Call init_device_keys() first.")

    local_public_key = row[0]
    safety_number = e2e_service.generate_safety_number(local_public_key, public_key)

    # Check if this is a key change
    cursor.execute("SELECT safety_number FROM peer_keys WHERE peer_device_id = ?", (peer_device_id,))
    existing = cursor.fetchone()

    if existing and existing[0] != safety_number:
        # Key change detected - log it
        cursor.execute("""
            INSERT INTO safety_number_changes
            (peer_device_id, old_safety_number, new_safety_number, changed_at)
            VALUES (?, ?, ?, ?)
        """, (peer_device_id, existing[0], safety_number, datetime.now(UTC).isoformat()))
        logger.warning(f"⚠️ Safety number changed for peer {peer_device_id}")

    # Store/update peer key
    cursor.execute("""
        INSERT OR REPLACE INTO peer_keys
        (peer_device_id, public_key, fingerprint, verify_key, safety_number, first_seen, last_key_change)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT first_seen FROM peer_keys WHERE peer_device_id = ?), ?), ?)
    """, (
        peer_device_id,
        public_key,
        fingerprint,
        verify_key,
        safety_number,
        peer_device_id,
        datetime.now(UTC).isoformat(),
        datetime.now(UTC).isoformat() if existing else None
    ))

    conn.commit()
    conn.close()

    return {
        "safety_number": safety_number,
        "fingerprint": e2e_service.format_fingerprint(fingerprint),
        "key_changed": bool(existing)
    }


def verify_peer_fingerprint(db_path: Path, peer_device_id: str) -> bool:
    """
    Mark a peer's fingerprint as verified.

    Args:
        db_path: Path to P2P chat database
        peer_device_id: Peer's device identifier

    Returns:
        True if marked verified
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE peer_keys
        SET verified = 1, verified_at = ?
        WHERE peer_device_id = ?
    """, (datetime.now(UTC).isoformat(), peer_device_id))

    conn.commit()
    conn.close()

    logger.info(f"✓ Verified fingerprint for peer {peer_device_id}")
    return True


def get_unacknowledged_safety_changes(db_path: Path) -> List[Dict]:
    """
    Get list of unacknowledged safety number changes (for yellow warning UI).

    Args:
        db_path: Path to P2P chat database

    Returns:
        List of safety number changes that need user acknowledgment
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sc.id,
            sc.peer_device_id,
            pk.public_key,
            sc.old_safety_number,
            sc.new_safety_number,
            sc.changed_at,
            p.display_name
        FROM safety_number_changes sc
        JOIN peer_keys pk ON sc.peer_device_id = pk.peer_device_id
        LEFT JOIN peers p ON pk.peer_device_id = p.peer_id
        WHERE sc.acknowledged = 0
        ORDER BY sc.changed_at DESC
    """)

    changes = []
    for row in cursor.fetchall():
        changes.append({
            "id": row[0],
            "peer_device_id": row[1],
            "peer_name": row[6] or row[1],
            "old_safety_number": row[3],
            "new_safety_number": row[4],
            "changed_at": row[5]
        })

    conn.close()
    return changes


def acknowledge_safety_change(db_path: Path, change_id: int) -> bool:
    """
    Mark a safety number change as acknowledged.

    Args:
        db_path: Path to P2P chat database
        change_id: ID of the safety_number_changes record

    Returns:
        True if acknowledged
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE safety_number_changes
        SET acknowledged = 1, acknowledged_at = ?
        WHERE id = ?
    """, (datetime.now(UTC).isoformat(), change_id))

    conn.commit()
    conn.close()

    logger.info(f"✓ Acknowledged safety number change {change_id}")
    return True
