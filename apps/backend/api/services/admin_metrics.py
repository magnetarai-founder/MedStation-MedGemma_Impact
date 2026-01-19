"""
Admin Metrics Operations

Provides Founder Rights support capabilities for system metrics:
- Vault status metadata (document counts only, no decrypted content)
- Device overview metrics (system-wide statistics)
- Workflow metadata

Does NOT expose decrypted vault content or sensitive data.

Extracted from admin_support.py during P2 decomposition.
"""

import sqlite3
import logging
from typing import Dict, Any
from datetime import datetime, UTC
from pathlib import Path
from fastapi import HTTPException

from api.errors import http_404, http_500, http_503

logger = logging.getLogger(__name__)


def _get_memory() -> Any:
    """Get memory (chat) service instance."""
    from api.chat_memory import get_memory
    return get_memory()


# ===== Vault Status Functions =====

async def get_vault_status(target_user_id: str) -> Dict[str, Any]:
    """
    Get user's vault status for support.

    Returns vault METADATA only:
    - Number of documents in real vault
    - Number of documents in decoy vault
    - Last access time

    Does NOT return:
    - Encrypted vault contents
    - Vault passphrase
    - Decrypted data

    Args:
        target_user_id: User identifier

    Returns:
        Dict with vault metadata

    Raises:
        HTTPException: If user not found
    """
    try:
        memory = _get_memory()
        conn = memory.memory.conn

        # Check if user exists
        user = conn.execute(
            "SELECT user_id, username FROM users WHERE user_id = ?",
            (target_user_id,)
        ).fetchone()

        if not user:
            raise http_404("User not found", resource="user")

        # Get document count for real vault
        doc_count_real = conn.execute("""
            SELECT COUNT(*) FROM documents
            WHERE user_id = ? AND vault_type = 'real' AND deleted_at IS NULL
        """, (target_user_id,)).fetchone()[0]

        # Get document count for decoy vault (if enabled)
        doc_count_decoy = conn.execute("""
            SELECT COUNT(*) FROM documents
            WHERE user_id = ? AND vault_type = 'decoy' AND deleted_at IS NULL
        """, (target_user_id,)).fetchone()[0]

        # Get last vault access time (approximate via last document update)
        last_access = conn.execute("""
            SELECT MAX(updated_at) FROM documents
            WHERE user_id = ?
        """, (target_user_id,)).fetchone()[0]

        return {
            "user_id": target_user_id,
            "username": user[1],
            "real_vault": {
                "document_count": doc_count_real
            },
            "decoy_vault": {
                "document_count": doc_count_decoy
            },
            "last_access": last_access,
            "note": "Metadata only - vault contents remain encrypted and inaccessible"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vault status for {target_user_id}: {e}")
        raise http_500(f"Failed to get vault status: {str(e)}")


# ===== Device Overview Functions =====

async def get_device_overview_metrics() -> Dict[str, Any]:
    """
    Gather device-wide overview statistics.

    Returns ONLY real metrics from authoritative databases.
    Never returns phantom or assumed data.

    This function does NOT perform rate limiting or audit logging.
    The router layer handles those concerns.

    Returns:
        Dict with device_overview and timestamp
    """
    from api.config_paths import PATHS

    memory = _get_memory()
    overview = {}

    # 1. Total users from auth DB
    try:
        conn = memory.memory.conn
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        overview["total_users"] = user_count
    except Exception as e:
        logger.error(f"Failed to count users: {e}")
        overview["total_users"] = None

    # 2. Total chat sessions from memory DB
    try:
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
        overview["total_chat_sessions"] = chat_count
    except Exception as e:
        logger.debug(f"No chat_sessions table or error: {e}")
        overview["total_chat_sessions"] = None

    # 3. Total workflows from workflows DB
    try:
        workflows_db_path = PATHS.data_dir / "workflows.db"
        if workflows_db_path.exists():
            workflows_conn = sqlite3.connect(str(workflows_db_path))
            workflow_count = workflows_conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            workflows_conn.close()
            overview["total_workflows"] = workflow_count
        else:
            overview["total_workflows"] = None
    except Exception as e:
        logger.debug(f"No workflows DB or error: {e}")
        overview["total_workflows"] = None

    # 4. Total work items from workflows DB
    try:
        workflows_db_path = PATHS.data_dir / "workflows.db"
        if workflows_db_path.exists():
            workflows_conn = sqlite3.connect(str(workflows_db_path))
            work_item_count = workflows_conn.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
            workflows_conn.close()
            overview["total_work_items"] = work_item_count
        else:
            overview["total_work_items"] = None
    except Exception as e:
        logger.debug(f"No work_items table or error: {e}")
        overview["total_work_items"] = None

    # 5. Total documents from memory DB
    try:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL").fetchone()[0]
        overview["total_documents"] = doc_count
    except Exception as e:
        logger.debug(f"No documents table or error: {e}")
        overview["total_documents"] = None

    # 6. Data directory size
    try:
        import os
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(PATHS.data_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        overview["data_dir_size_bytes"] = total_size
        overview["data_dir_size_mb"] = round(total_size / (1024 * 1024), 2)
    except Exception as e:
        logger.error(f"Failed to calculate data dir size: {e}")
        overview["data_dir_size_bytes"] = None
        overview["data_dir_size_mb"] = None

    return {
        "device_overview": overview,
        "timestamp": datetime.now(UTC).isoformat()
    }


# ===== Workflow Metadata Functions =====

async def get_user_workflows(target_user_id: str) -> Dict[str, Any]:
    """
    Get user's workflows for support purposes.

    Returns workflow metadata (id, name, description, category, enabled)
    and work items (id, workflow_id, status, priority).
    Does NOT return workflow execution details or sensitive data.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with user_id, workflows list, work_items list, and totals

    Raises:
        HTTPException: If workflows DB not available
    """
    # Try multiple possible paths for workflows DB
    workflow_db = Path(".") / "apps" / "backend" / "api" / "data" / "workflows.db"
    if not workflow_db.exists():
        workflow_db = Path("data") / "workflows.db"

    try:
        from api.config_paths import PATHS
        if not workflow_db.exists():
            workflow_db = PATHS.data_dir / "workflows.db"
    except ImportError:
        pass

    if not workflow_db.exists():
        raise http_503("Workflow database not available")

    try:
        wf_conn = sqlite3.connect(str(workflow_db))
        wf_conn.row_factory = sqlite3.Row

        # Get user's workflows
        cursor = wf_conn.execute("""
            SELECT id, name, description, category, enabled, created_at, updated_at
            FROM workflows
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (target_user_id,))

        workflows = []
        for row in cursor.fetchall():
            workflows.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })

        # Get user's work items
        cursor = wf_conn.execute("""
            SELECT id, workflow_id, status, priority, created_at, updated_at
            FROM work_items
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 100
        """, (target_user_id,))

        work_items = []
        for row in cursor.fetchall():
            work_items.append({
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "status": row["status"],
                "priority": row["priority"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })

        wf_conn.close()

        return {
            "user_id": target_user_id,
            "workflows": workflows,
            "work_items": work_items,
            "total_workflows": len(workflows),
            "total_work_items": len(work_items)
        }

    except Exception as e:
        logger.error(f"Failed to get workflows for user {target_user_id}: {e}")
        raise http_500(f"Failed to retrieve user workflows: {str(e)}")


__all__ = [
    "get_vault_status",
    "get_device_overview_metrics",
    "get_user_workflows",
]
