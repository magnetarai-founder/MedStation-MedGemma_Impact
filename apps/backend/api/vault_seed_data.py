#!/usr/bin/env python3
"""
Vault Seed Data Service
Populates decoy vault with realistic documents for plausible deniability

Security: Decoy vault must look convincing to be effective

Extracted modules (P2 decomposition):
- vault_decoy_documents.py: Static decoy document data and helper functions
"""

import logging
import uuid
import base64
from datetime import datetime, timedelta, UTC
from typing import Dict, Any
import sqlite3

logger = logging.getLogger(__name__)

# Database path
from api.config_paths import get_config_paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"

# Import decoy documents from extracted module (P2 decomposition)
from api.vault_decoy_documents import DECOY_DOCUMENTS


class DecoyVaultSeeder:
    """
    Seed decoy vault with realistic documents

    Goal: Make decoy vault indistinguishable from real vault
    """

    def __init__(self):
        self.db_path = VAULT_DB_PATH

    def seed_decoy_vault(self, user_id: str) -> Dict[str, Any]:
        """
        Populate decoy vault with realistic documents

        Args:
            user_id: User ID to seed decoy vault for

        Returns:
            Summary of seeded documents
        """
        logger.info(f"🌱 Seeding decoy vault for user {user_id}")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if decoy vault already seeded
        cursor.execute("""
            SELECT COUNT(*) FROM vault_documents
            WHERE user_id = ? AND vault_type = 'decoy'
        """, (user_id,))

        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.info(f"Decoy vault already seeded ({existing_count} documents)")
            conn.close()
            return {
                "status": "already_seeded",
                "document_count": existing_count,
                "message": "Decoy vault already contains documents"
            }

        # Seed decoy documents
        seeded_docs = []

        for doc_data in DECOY_DOCUMENTS:
            doc_id = str(uuid.uuid4())
            created_at = self._generate_realistic_timestamp()

            # Create minimal encrypted metadata (just filename)
            metadata = {
                "filename": doc_data["name"],
                "type": doc_data["type"],
                "size": len(doc_data["content"]),
            }

            # In real implementation, this would be encrypted client-side
            # For seeding, we'll store plaintext and let client encrypt on first access
            encrypted_blob = base64.b64encode(doc_data["content"].encode('utf-8')).decode('utf-8')
            encrypted_metadata = base64.b64encode(str(metadata).encode('utf-8')).decode('utf-8')

            cursor.execute("""
                INSERT INTO vault_documents
                (id, user_id, vault_type, encrypted_blob, encrypted_metadata, created_at, updated_at, size_bytes)
                VALUES (?, ?, 'decoy', ?, ?, ?, ?, ?)
            """, (
                doc_id,
                user_id,
                encrypted_blob,
                encrypted_metadata,
                created_at,
                created_at,
                len(doc_data["content"])
            ))

            seeded_docs.append({
                "id": doc_id,
                "name": doc_data["name"],
                "type": doc_data["type"]
            })

        conn.commit()
        conn.close()

        logger.info(f"✅ Seeded {len(seeded_docs)} decoy documents")

        return {
            "status": "success",
            "document_count": len(seeded_docs),
            "documents": seeded_docs,
            "message": f"Decoy vault seeded with {len(seeded_docs)} realistic documents"
        }

    def _generate_realistic_timestamp(self) -> str:
        """Generate realistic timestamp (random date in past 6 months)"""
        days_ago = uuid.uuid4().int % 180  # 0-180 days ago
        timestamp = datetime.now(UTC) - timedelta(days=days_ago)
        return timestamp.isoformat()

    def clear_decoy_vault(self, user_id: str) -> Dict[str, Any]:
        """
        Clear all decoy vault documents (for testing)

        Args:
            user_id: User ID to clear decoy vault for

        Returns:
            Summary of cleared documents
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM vault_documents
            WHERE user_id = ? AND vault_type = 'decoy'
        """, (user_id,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"🗑️ Cleared {deleted_count} decoy documents for user {user_id}")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Cleared {deleted_count} decoy vault documents"
        }


def get_seeder() -> DecoyVaultSeeder:
    """Get global seeder instance"""
    return DecoyVaultSeeder()


if __name__ == "__main__":
    # Test seeding
    seeder = DecoyVaultSeeder()
    result = seeder.seed_decoy_vault("test_user_123")
    print(result)
