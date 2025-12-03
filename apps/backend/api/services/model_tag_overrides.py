"""
Model Tag Overrides Database Service
Stores user-defined manual tag assignments that override auto-detection
"""

import json
import sqlite3
from typing import List, Set, Optional
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path.home() / ".magnetar_studio" / "model_tags.db"


def init_database():
    """Initialize the model tags override database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_tag_overrides (
            model_name TEXT PRIMARY KEY,
            manual_tags TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_manual_tags(model_name: str) -> Optional[Set[str]]:
    """
    Get manual tag overrides for a model

    Args:
        model_name: Model name (e.g., "qwen2.5-coder:3b")

    Returns:
        Set of manual tags, or None if no overrides exist
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT manual_tags FROM model_tag_overrides WHERE model_name = ?",
        (model_name,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return set(json.loads(row[0]))
    return None


def set_manual_tags(model_name: str, tags: List[str]) -> None:
    """
    Set manual tag overrides for a model

    Args:
        model_name: Model name (e.g., "qwen2.5-coder:3b")
        tags: List of tag IDs to assign
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()
    tags_json = json.dumps(sorted(tags))

    # Check if exists
    cursor.execute(
        "SELECT created_at FROM model_tag_overrides WHERE model_name = ?",
        (model_name,)
    )
    existing = cursor.fetchone()

    if existing:
        # Update existing
        cursor.execute("""
            UPDATE model_tag_overrides
            SET manual_tags = ?, updated_at = ?
            WHERE model_name = ?
        """, (tags_json, now, model_name))
    else:
        # Insert new
        cursor.execute("""
            INSERT INTO model_tag_overrides (model_name, manual_tags, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (model_name, tags_json, now, now))

    conn.commit()
    conn.close()


def delete_manual_tags(model_name: str) -> bool:
    """
    Delete manual tag overrides for a model

    Args:
        model_name: Model name

    Returns:
        True if deleted, False if didn't exist
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM model_tag_overrides WHERE model_name = ?",
        (model_name,)
    )

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def get_merged_tags(model_name: str, auto_detected_tags: Set[str]) -> Set[str]:
    """
    Get merged tags combining auto-detection with manual overrides

    Strategy:
    - If manual overrides exist, use them ENTIRELY (replace auto-detected)
    - If no manual overrides, return auto-detected tags

    Args:
        model_name: Model name
        auto_detected_tags: Tags detected by pattern matching

    Returns:
        Final set of tags to use
    """
    manual_tags = get_manual_tags(model_name)

    if manual_tags is not None:
        # Manual overrides completely replace auto-detected
        return manual_tags
    else:
        # No overrides, use auto-detected
        return auto_detected_tags


# Initialize database on module import
init_database()
