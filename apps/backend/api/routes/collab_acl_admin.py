"""
Collaboration ACL Admin Routes (minimal).

Endpoints:
- GET  /api/v1/collab/docs/{doc_id}/acl        → list ACL rows (owner-only)
- POST /api/v1/collab/docs/{doc_id}/acl        → upsert ACL entry (owner-only)
"""

from __future__ import annotations

import re
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services.collab_acl import (
    user_can_access_doc,
    list_acl,
    upsert_acl,
    ROLES,
)


router = APIRouter(prefix="/api/v1/collab", tags=["collab-acl"], dependencies=[Depends(get_current_user)])

SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


class AclRow(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern=r"^(owner|edit|view)$")


def _require_owner(current_user: dict, doc_id: str) -> None:
    if not SAFE_ID.match(doc_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doc_id")
    uid = current_user.get("user_id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not user_can_access_doc(uid, doc_id, min_role="owner"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")


@router.get("/docs/{doc_id}/acl", response_model=List[AclRow])
async def get_acl(doc_id: str, current_user: dict = Depends(get_current_user)):
    """List ACL rows for a document (owner-only)."""
    _require_owner(current_user, doc_id)
    rows = list_acl(doc_id)
    return [AclRow(user_id=u, role=r) for (u, r) in rows]


@router.post("/docs/{doc_id}/acl", response_model=AclRow)
async def upsert_acl_entry(doc_id: str, body: AclRow, current_user: dict = Depends(get_current_user)):
    """Create or update an ACL entry (owner-only)."""
    _require_owner(current_user, doc_id)
    if body.role not in ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    # Prevent privilege lockout: owner cannot demote the last owner (naive safeguard omitted for brevity)
    upsert_acl(doc_id, body.user_id, body.role)
    return body

