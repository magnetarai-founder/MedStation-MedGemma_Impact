"""
Code Operations - Project Library Database

SQLite storage for project library documents.
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from api.config_paths import PATHS

logger = logging.getLogger(__name__)


def get_library_db_path() -> Path:
    """Get path to project library database"""
    return PATHS.data_dir / "project_library.db"


def init_library_db() -> None:
    """Initialize project library database"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,
            file_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_documents(user_id: str) -> List[Dict[str, Any]]:
    """Get all documents for a user"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, content, tags, file_type, created_at, updated_at
        FROM documents
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (user_id,))

    documents = []
    for row in cursor.fetchall():
        documents.append({
            'id': row[0],
            'name': row[1],
            'content': row[2],
            'tags': json.loads(row[3]),
            'file_type': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        })

    conn.close()
    return documents


def create_document(
    user_id: str,
    name: str,
    content: str,
    tags: List[str],
    file_type: str
) -> int:
    """Create a new document and return its ID"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO documents (user_id, name, content, tags, file_type, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, content, json.dumps(tags), file_type, now, now))

    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return doc_id


def update_document(
    user_id: str,
    doc_id: int,
    name: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> bool:
    """Update a document"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)

    if content is not None:
        updates.append("content = ?")
        params.append(content)

    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())

    params.extend([user_id, doc_id])

    cursor.execute(f"""
        UPDATE documents
        SET {', '.join(updates)}
        WHERE user_id = ? AND id = ?
    """, params)

    conn.commit()
    conn.close()

    return True


def delete_document(user_id: str, doc_id: int) -> bool:
    """Delete a document"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM documents
        WHERE user_id = ? AND id = ?
    """, (user_id, doc_id))

    conn.commit()
    conn.close()

    return True


# Initialize on module load
init_library_db()
