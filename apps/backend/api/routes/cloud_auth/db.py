"""
Cloud Auth - Database

Database initialization and path management for cloud authentication.
"""

import sqlite3
import logging
from pathlib import Path

from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Database path (uses vault.db for consistency)
PATHS = get_config_paths()
CLOUD_DB_PATH = PATHS.data_dir / "vault.db"


def get_db_path() -> Path:
    """Get cloud auth database path."""
    return CLOUD_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    return sqlite3.connect(str(CLOUD_DB_PATH))


def init_cloud_auth_db() -> None:
    """Initialize cloud auth tables"""
    CLOUD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Cloud device registrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_devices (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT,
                device_platform TEXT,

                -- Cloud credentials
                cloud_device_id TEXT NOT NULL UNIQUE,
                cloud_token_hash TEXT NOT NULL,
                cloud_refresh_token_hash TEXT,

                -- Token expiry
                token_expires_at TEXT NOT NULL,
                refresh_token_expires_at TEXT,

                -- Metadata
                created_at TEXT NOT NULL,
                last_sync_at TEXT,
                is_active INTEGER DEFAULT 1,

                UNIQUE(user_id, device_id)
            )
        """)

        # Cloud sessions (active sync sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_sessions (
                id TEXT PRIMARY KEY,
                cloud_device_id TEXT NOT NULL,
                session_token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT,

                FOREIGN KEY (cloud_device_id) REFERENCES cloud_devices(cloud_device_id)
            )
        """)

        # Cloud sync audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_sync_log (
                id TEXT PRIMARY KEY,
                cloud_device_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL,
                details TEXT,

                FOREIGN KEY (cloud_device_id) REFERENCES cloud_devices(cloud_device_id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_devices_user
            ON cloud_devices(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_devices_active
            ON cloud_devices(is_active, user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_sessions_device
            ON cloud_sessions(cloud_device_id)
        """)

        conn.commit()

    logger.debug("Cloud auth database initialized")


# Initialize on module load
init_cloud_auth_db()
