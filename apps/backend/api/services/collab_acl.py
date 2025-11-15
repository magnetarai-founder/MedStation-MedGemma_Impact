"""
Collaboration ACL helper utilities (skeleton).

Provides minimal per-document access control stored in app_db:
- doc_acl(doc_id TEXT, user_id TEXT, role TEXT CHECK(role IN ('owner','edit','view')), PRIMARY KEY(doc_id, user_id))

Functions:
- ensure_schema()
- user_can_access_doc(user_id, doc_id, min_role='view') -> bool
- upsert_acl(doc_id, user_id, role)
- list_acl(doc_id) -> list rows
"""

from __future__ import annotations

import sqlite3
from typing import List, Tuple

from api.config_paths import PATHS


ROLES = ("owner", "edit", "view")
ROLE_ORDER = {"view": 0, "edit": 1, "owner": 2}


def ensure_schema() -> None:
    with sqlite3.connect(str(PATHS.app_db)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS doc_acl (
                doc_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('owner','edit','view')),
                PRIMARY KEY(doc_id, user_id)
            )
            """
        )
        conn.commit()


def user_can_access_doc(user_id: str, doc_id: str, min_role: str = "view") -> bool:
    """Check if user has at least min_role on doc.

    If no ACL rows exist for the doc, default allow (first iteration, optional policy).
    """
    ensure_schema()
    with sqlite3.connect(str(PATHS.app_db)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM doc_acl WHERE doc_id = ?", (doc_id,))
        count = cur.fetchone()[0]
        if count == 0:
            # No ACL set → allow by default (adjust policy later if needed)
            return True

        cur.execute("SELECT role FROM doc_acl WHERE doc_id = ? AND user_id = ?", (doc_id, user_id))
        row = cur.fetchone()
        if not row:
            return False
        have = row[0]
        return ROLE_ORDER.get(have, -1) >= ROLE_ORDER.get(min_role, 0)


def upsert_acl(doc_id: str, user_id: str, role: str) -> None:
    if role not in ROLES:
        raise ValueError("invalid role")
    ensure_schema()
    with sqlite3.connect(str(PATHS.app_db)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO doc_acl (doc_id, user_id, role) VALUES (?,?,?)",
            (doc_id, user_id, role),
        )
        conn.commit()


def list_acl(doc_id: str) -> List[Tuple[str, str]]:
    ensure_schema()
    with sqlite3.connect(str(PATHS.app_db)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, role FROM doc_acl WHERE doc_id = ? ORDER BY role DESC", (doc_id,))
        return cur.fetchall()

