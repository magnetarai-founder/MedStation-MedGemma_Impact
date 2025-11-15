"""
Collaboration Snapshots Routes (skeleton).

Provides list/restore operations for Y.Doc snapshots.

GET  /api/v1/collab/docs/{doc_id}/snapshots
POST /api/v1/collab/docs/{doc_id}/restore  {"snapshot_id": "<filename>"}
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user, User
from api.config_paths import PATHS
from api.services.collab_state import apply_snapshot
from api.services.collab_acl import upsert_acl, list_acl


router = APIRouter(prefix="/api/v1/collab", tags=["collab-snapshots"], dependencies=[Depends(get_current_user)])


SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _snap_dir(doc_id: str) -> Path:
    base = PATHS.cache_dir / "collab_docs" / doc_id
    base.mkdir(parents=True, exist_ok=True)
    return base


class SnapshotItem(BaseModel):
    id: str
    size_bytes: int
    modified_ts: float


@router.get("/docs/{doc_id}/snapshots", response_model=List[SnapshotItem])
async def list_snapshots(doc_id: str):
    if not SAFE_ID.match(doc_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doc_id")
    d = _snap_dir(doc_id)
    items: List[SnapshotItem] = []
    for p in sorted(d.glob("*.json")):
        try:
            stat = p.stat()
            items.append(SnapshotItem(id=p.name, size_bytes=stat.st_size, modified_ts=stat.st_mtime))
        except Exception:
            continue
    return items


class RestoreRequest(BaseModel):
    snapshot_id: str


@router.post("/docs/{doc_id}/restore")
async def restore_snapshot(doc_id: str, body: RestoreRequest):
    if not SAFE_ID.match(doc_id) or not SAFE_ID.match(body.snapshot_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")
    snap_path = _snap_dir(doc_id) / body.snapshot_id
    if not snap_path.exists() or not snap_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    data = snap_path.read_bytes()
    try:
        ok = apply_snapshot(doc_id, data)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Restore failed: {e}")
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Restore failed")
    return {"status": "restored", "doc_id": doc_id, "snapshot_id": body.snapshot_id}


# ===== ACL Management Endpoints =====

class ACLEntry(BaseModel):
    user_id: str
    role: str  # owner, edit, view


class ACLUpsertRequest(BaseModel):
    user_id: str
    role: str


@router.get("/docs/{doc_id}/acl")
async def get_doc_acl(doc_id: str):
    """
    Get ACL entries for a document

    Returns:
        List of {user_id, role} entries
    """
    if not SAFE_ID.match(doc_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doc_id")

    try:
        acl_entries = list_acl(doc_id)
        return {
            "doc_id": doc_id,
            "acl": [{"user_id": user_id, "role": role} for user_id, role in acl_entries]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ACL: {str(e)}"
        )


@router.post("/docs/{doc_id}/acl")
async def set_doc_acl(
    doc_id: str,
    body: ACLUpsertRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Set/update ACL entry for a document

    Note: First-cut implementation allows any authenticated user to set ACL.
    In production, restrict to document owner or admin.

    Args:
        doc_id: Document ID
        body: {user_id, role}

    Returns:
        Success status
    """
    if not SAFE_ID.match(doc_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doc_id")

    # Validate role
    if body.role not in ("owner", "edit", "view"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: owner, edit, or view"
        )

    try:
        upsert_acl(doc_id, body.user_id, body.role)
        return {
            "success": True,
            "doc_id": doc_id,
            "user_id": body.user_id,
            "role": body.role,
            "message": "ACL entry updated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ACL: {str(e)}"
        )
