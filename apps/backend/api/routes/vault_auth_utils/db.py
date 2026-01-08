"""
Vault Auth Database Initialization

Schema and indexes for vault authentication metadata.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def init_vault_auth_db(vault_db_path: Path) -> None:
    """Initialize vault auth metadata tables and indexes."""
    vault_db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(vault_db_path)) as conn:
        cursor = conn.cursor()

        # Vault authentication metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_auth_metadata (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_id TEXT NOT NULL,

                -- Biometric (WebAuthn) fields
                webauthn_credential_id TEXT,
                webauthn_public_key TEXT,
                webauthn_counter INTEGER DEFAULT 0,

                -- Real vault fields
                salt_real TEXT,
                wrapped_kek_real TEXT,

                -- Decoy vault fields (optional)
                salt_decoy TEXT,
                wrapped_kek_decoy TEXT,
                decoy_enabled INTEGER DEFAULT 0,

                -- Key wrapping method (aes_kw, xchacha20p, xor_legacy)
                wrap_method TEXT DEFAULT 'aes_kw',

                -- Metadata
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE(user_id, vault_id)
            )
        """)

        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_auth_user
            ON vault_auth_metadata(user_id, vault_id)
        """)

        # Unlock attempt tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_unlock_attempts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_id TEXT NOT NULL,
                attempt_time TEXT NOT NULL,
                success INTEGER NOT NULL,
                method TEXT NOT NULL CHECK(method IN ('biometric', 'passphrase'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unlock_attempts_user
            ON vault_unlock_attempts(user_id, vault_id, attempt_time DESC)
        """)

        # Migration: Add wrap_method column if it doesn't exist
        cursor.execute("PRAGMA table_info(vault_auth_metadata)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'wrap_method' not in columns:
            cursor.execute("""
                ALTER TABLE vault_auth_metadata
                ADD COLUMN wrap_method TEXT DEFAULT 'xor_legacy'
            """)
            logger.info("Migration: Added wrap_method column (defaulting existing entries to xor_legacy)")

        conn.commit()
