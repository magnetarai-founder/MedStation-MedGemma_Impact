"""
MagnetarTrust - Storage Layer

SQLite-based storage for trust network data.
Local-first, encrypted, offline-capable.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import UTC, datetime

from api.trust.models import (
    TrustNode,
    TrustRelationship,
    NodeType,
    TrustLevel,
    DisplayMode
)

logger = logging.getLogger(__name__)


class TrustStorage:
    """
    Storage layer for MagnetarTrust.
    Uses SQLite for local-first, offline-capable storage.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize trust storage"""
        if db_path is None:
            # Default: store in .neutron_data directory
            base_dir = Path(__file__).parent.parent.parent / ".neutron_data"
            base_dir.mkdir(exist_ok=True)
            db_path = base_dir / "trust_network.db"

        self.db_path = db_path
        self._init_db()
        logger.info(f"📡 Trust network storage initialized: {db_path}")

    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trust_nodes (
                    id TEXT PRIMARY KEY,
                    public_key TEXT NOT NULL UNIQUE,
                    public_name TEXT NOT NULL,
                    alias TEXT,
                    type TEXT NOT NULL,
                    display_mode TEXT NOT NULL DEFAULT 'peacetime',
                    bio TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    is_hub INTEGER NOT NULL DEFAULT 0,
                    vouched_by TEXT,
                    FOREIGN KEY (vouched_by) REFERENCES trust_nodes(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS trust_relationships (
                    id TEXT PRIMARY KEY,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    level TEXT NOT NULL,
                    vouched_by TEXT,
                    established TEXT NOT NULL,
                    last_verified TEXT NOT NULL,
                    note TEXT,
                    is_mutual INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (from_node) REFERENCES trust_nodes(id),
                    FOREIGN KEY (to_node) REFERENCES trust_nodes(id),
                    FOREIGN KEY (vouched_by) REFERENCES trust_nodes(id),
                    UNIQUE(from_node, to_node)
                )
            """)

            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trust_from
                ON trust_relationships(from_node)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trust_to
                ON trust_relationships(to_node)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trust_level
                ON trust_relationships(level)
            """)

            conn.commit()

    # ===== Node Operations =====

    def create_node(self, node: TrustNode) -> TrustNode:
        """Create a new trust node"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trust_nodes
                (id, public_key, public_name, alias, type, display_mode,
                 bio, location, created_at, last_seen, is_hub, vouched_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.id, node.public_key, node.public_name, node.alias,
                node.type.value, node.display_mode.value,
                node.bio, node.location, node.created_at, node.last_seen,
                1 if node.is_hub else 0, node.vouched_by
            ))
            conn.commit()

        logger.info(f"✓ Created trust node: {node.id} ({node.public_name})")
        return node

    def get_node(self, node_id: str) -> Optional[TrustNode]:
        """Get a trust node by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM trust_nodes WHERE id = ?",
                (node_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_node(row)

    def get_node_by_public_key(self, public_key: str) -> Optional[TrustNode]:
        """Get a trust node by public key"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM trust_nodes WHERE public_key = ?",
                (public_key,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_node(row)

    def list_nodes(self, node_type: Optional[NodeType] = None) -> List[TrustNode]:
        """List all trust nodes, optionally filtered by type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if node_type:
                rows = conn.execute(
                    "SELECT * FROM trust_nodes WHERE type = ? ORDER BY created_at DESC",
                    (node_type.value,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trust_nodes ORDER BY created_at DESC"
                ).fetchall()

        return [self._row_to_node(row) for row in rows]

    def update_node(self, node: TrustNode) -> TrustNode:
        """Update a trust node"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE trust_nodes SET
                    public_name = ?,
                    alias = ?,
                    display_mode = ?,
                    bio = ?,
                    location = ?,
                    last_seen = ?,
                    is_hub = ?
                WHERE id = ?
            """, (
                node.public_name, node.alias, node.display_mode.value,
                node.bio, node.location, node.last_seen,
                1 if node.is_hub else 0, node.id
            ))
            conn.commit()

        logger.info(f"✓ Updated trust node: {node.id}")
        return node

    # ===== Relationship Operations =====

    def create_relationship(self, relationship: TrustRelationship) -> TrustRelationship:
        """Create a trust relationship"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trust_relationships
                (id, from_node, to_node, level, vouched_by, established,
                 last_verified, note, is_mutual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                relationship.id, relationship.from_node, relationship.to_node,
                relationship.level.value, relationship.vouched_by,
                relationship.established, relationship.last_verified,
                relationship.note, 1 if relationship.is_mutual else 0
            ))
            conn.commit()

        logger.info(f"✓ Created trust relationship: {relationship.from_node} → {relationship.to_node}")
        return relationship

    def get_relationships(self, node_id: str, level: Optional[TrustLevel] = None) -> List[TrustRelationship]:
        """Get all trust relationships for a node"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if level:
                rows = conn.execute("""
                    SELECT * FROM trust_relationships
                    WHERE from_node = ? AND level = ?
                    ORDER BY established DESC
                """, (node_id, level.value)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM trust_relationships
                    WHERE from_node = ?
                    ORDER BY established DESC
                """, (node_id,)).fetchall()

        return [self._row_to_relationship(row) for row in rows]

    def get_trusted_nodes(self, node_id: str, max_degrees: int = 3) -> Dict[str, List[TrustNode]]:
        """
        Get all nodes trusted by this node, up to max_degrees of separation.
        Returns dict with keys: direct, vouched, network
        """
        direct_trusts = []
        vouched_trusts = []
        network_trusts = []

        # Get direct trusts (degree 1)
        direct_relationships = self.get_relationships(node_id, TrustLevel.DIRECT)
        for rel in direct_relationships:
            node = self.get_node(rel.to_node)
            if node:
                direct_trusts.append(node)

        # Get vouched trusts (degree 2)
        if max_degrees >= 2:
            vouched_relationships = self.get_relationships(node_id, TrustLevel.VOUCHED)
            for rel in vouched_relationships:
                node = self.get_node(rel.to_node)
                if node:
                    vouched_trusts.append(node)

        # Get network trusts (degree 3+)
        if max_degrees >= 3:
            # For each directly trusted node, get their direct trusts
            for direct_node in direct_trusts:
                their_relationships = self.get_relationships(direct_node.id, TrustLevel.DIRECT)
                for rel in their_relationships:
                    # Don't include nodes we already have
                    if rel.to_node != node_id and rel.to_node not in [n.id for n in direct_trusts]:
                        node = self.get_node(rel.to_node)
                        if node and node.id not in [n.id for n in network_trusts]:
                            network_trusts.append(node)

        return {
            "direct": direct_trusts,
            "vouched": vouched_trusts,
            "network": network_trusts
        }

    # ===== Helper Methods =====

    def _row_to_node(self, row: sqlite3.Row) -> TrustNode:
        """Convert SQLite row to TrustNode"""
        return TrustNode(
            id=row["id"],
            public_key=row["public_key"],
            public_name=row["public_name"],
            alias=row["alias"],
            type=NodeType(row["type"]),
            display_mode=DisplayMode(row["display_mode"]),
            bio=row["bio"],
            location=row["location"],
            created_at=row["created_at"],
            last_seen=row["last_seen"],
            is_hub=bool(row["is_hub"]),
            vouched_by=row["vouched_by"]
        )

    def _row_to_relationship(self, row: sqlite3.Row) -> TrustRelationship:
        """Convert SQLite row to TrustRelationship"""
        return TrustRelationship(
            id=row["id"],
            from_node=row["from_node"],
            to_node=row["to_node"],
            level=TrustLevel(row["level"]),
            vouched_by=row["vouched_by"],
            established=row["established"],
            last_verified=row["last_verified"],
            note=row["note"],
            is_mutual=bool(row["is_mutual"])
        )


# Global storage instance
_storage: Optional[TrustStorage] = None


def get_trust_storage() -> TrustStorage:
    """Get global trust storage instance"""
    global _storage
    if _storage is None:
        _storage = TrustStorage()
    return _storage
