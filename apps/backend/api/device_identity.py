"""
Device Identity (AUTH-P6)

Provides stable device identification separate from user accounts.
This identity persists across:
- User account changes (creation, deletion, all users deleted)
- Auth data resets
- App reinstalls (if machine_id can be recovered)

The device identity:
- Is machine-stable (based on hardware characteristics)
- Is independent of user accounts
- Enables future update server integration
- Tracks device lifecycle (first boot, last boot)

Usage:
    from api.device_identity import ensure_device_identity

    device_id = ensure_device_identity(conn)
    # Returns stable device_id, creates entry if needed
"""

import sqlite3
import logging
import platform
import socket
import uuid
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _generate_machine_id() -> str:
    """
    Generate a stable machine identifier based on hardware characteristics.

    This attempts to create an identifier that:
    - Is stable across reboots
    - Survives user account changes
    - Is reasonably unique per machine

    Strategy:
    1. Try to read existing machine_id from .elohimos/machine_id
    2. If not found, generate from hardware characteristics
    3. Cache to .elohimos/machine_id for stability

    Returns:
        A stable machine identifier (hex string)
    """
    # Try to read cached machine_id first
    cache_dir = Path.home() / ".elohimos"
    cache_file = cache_dir / "machine_id"

    if cache_file.exists():
        try:
            cached_id = cache_file.read_text().strip()
            if cached_id and len(cached_id) == 64:  # SHA256 hex length
                logger.debug(f"Using cached machine_id from {cache_file}")
                return cached_id
        except Exception as e:
            logger.warning(f"Failed to read cached machine_id: {e}")

    # Generate new machine_id from hardware characteristics
    try:
        # Collect hardware identifiers
        identifiers = []

        # 1. Hostname (relatively stable)
        try:
            hostname = socket.gethostname()
            identifiers.append(f"hostname:{hostname}")
        except (OSError, socket.error):
            pass

        # 2. Platform info (stable)
        identifiers.append(f"platform:{platform.system()}")
        identifiers.append(f"machine:{platform.machine()}")
        identifiers.append(f"processor:{platform.processor()}")

        # 3. Node name (MAC address based on some systems)
        try:
            node = platform.node()
            identifiers.append(f"node:{node}")
        except (OSError, AttributeError):
            pass

        # 4. getnode() - MAC address as integer
        try:
            mac = uuid.getnode()
            identifiers.append(f"mac:{mac}")
        except:
            pass

        # Hash all identifiers together
        machine_data = "|".join(identifiers)
        machine_id = hashlib.sha256(machine_data.encode()).hexdigest()

        # Cache for future use
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(machine_id)
            logger.info(f"Generated and cached new machine_id to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache machine_id: {e}")

        return machine_id

    except Exception as e:
        logger.error(f"Failed to generate machine_id: {e}", exc_info=True)
        # Fallback: Use UUID based on getnode()
        fallback_id = hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()
        logger.warning(f"Using fallback machine_id based on uuid.getnode()")
        return fallback_id


def _get_device_metadata() -> Dict[str, Any]:
    """
    Collect metadata about this device.

    Returns:
        Dict with platform info, hostname, etc.
    """
    try:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
    except Exception as e:
        logger.warning(f"Failed to collect device metadata: {e}")
        return {"error": str(e)}


def ensure_device_identity(conn: sqlite3.Connection) -> str:
    """
    Ensure this device has a stable identity.

    This function:
    1. Checks if device_identity row exists
    2. If not, generates device_id and machine_id, inserts row
    3. If exists, updates last_boot_at timestamp
    4. Returns device_id

    Safe to call on every startup - idempotent.

    Args:
        conn: SQLite database connection

    Returns:
        device_id (UUID string)

    Raises:
        Exception if device identity cannot be ensured
    """
    cursor = conn.cursor()

    try:
        # Generate stable machine_id
        machine_id = _generate_machine_id()

        # Check if device identity exists by machine_id
        cursor.execute("""
            SELECT device_id, created_at
            FROM device_identity
            WHERE machine_id = ?
        """, (machine_id,))

        row = cursor.fetchone()

        now = datetime.now(UTC).isoformat()

        if row:
            # Device identity exists - update last_boot_at
            device_id = row[0]
            created_at = row[1]

            cursor.execute("""
                UPDATE device_identity
                SET last_boot_at = ?,
                    hostname = ?,
                    platform = ?,
                    architecture = ?
                WHERE machine_id = ?
            """, (
                now,
                socket.gethostname(),
                platform.system(),
                platform.machine(),
                machine_id
            ))

            conn.commit()

            logger.info(f"Device identity exists: {device_id} (first boot: {created_at})")
            return device_id

        else:
            # Create new device identity
            device_id = str(uuid.uuid4())
            metadata = _get_device_metadata()

            cursor.execute("""
                INSERT INTO device_identity (
                    device_id,
                    machine_id,
                    created_at,
                    last_boot_at,
                    hostname,
                    platform,
                    architecture,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                machine_id,
                now,
                now,
                socket.gethostname(),
                platform.system(),
                platform.machine(),
                json.dumps(metadata)
            ))

            conn.commit()

            logger.info(f"Created new device identity: {device_id}")
            logger.info(f"  Machine ID: {machine_id[:16]}... (cached to ~/.elohimos/machine_id)")
            logger.info(f"  Platform: {platform.system()} {platform.machine()}")

            return device_id

    except Exception as e:
        logger.error(f"Failed to ensure device identity: {e}", exc_info=True)
        raise


def get_device_identity(conn: sqlite3.Connection) -> Optional[str]:
    """
    Get the current device_id if it exists.

    Args:
        conn: SQLite database connection

    Returns:
        device_id if exists, None otherwise
    """
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT device_id FROM device_identity LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.warning(f"Failed to get device identity: {e}")
        return None
