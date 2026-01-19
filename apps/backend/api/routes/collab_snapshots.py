"""
Collaboration Snapshots Routes

Provides list/restore operations for Y.Doc snapshots and ACL management.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user, User
from api.config_paths import PATHS
from api.services.collab_state import apply_snapshot
from api.services.collab_acl import upsert_acl, list_acl
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collab", tags=["collab-snapshots"])


SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _snap_dir(doc_id: str) -> Path:
    base = PATHS.cache_dir / "collab_docs" / doc_id
    base.mkdir(parents=True, exist_ok=True)
    return base


class SnapshotItem(BaseModel):
    id: str
    size_bytes: int
    modified_ts: float


@router.get(
    "/docs/{doc_id}/snapshots",
    response_model=SuccessResponse[List[SnapshotItem]],
    status_code=status.HTTP_200_OK,
    name="list_document_snapshots",
    summary="List snapshots",
    description="List all snapshots for a collaboration document"
)
async def list_snapshots(
    doc_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[List[SnapshotItem]]:
    """List all snapshots for a document"""
    try:
        if not SAFE_ID.match(doc_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid doc_id format"
                ).model_dump()
            )

        d = _snap_dir(doc_id)
        items: List[SnapshotItem] = []
        for p in sorted(d.glob("*.json")):
            try:
                stat = p.stat()
                items.append(SnapshotItem(id=p.name, size_bytes=stat.st_size, modified_ts=stat.st_mtime))
            except Exception:
                continue

        return SuccessResponse(
            data=items,
            message=f"Retrieved {len(items)} snapshot(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list snapshots for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve snapshots"
            ).model_dump()
        )


class RestoreRequest(BaseModel):
    snapshot_id: str


@router.post(
    "/docs/{doc_id}/restore",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="restore_document_snapshot",
    summary="Restore snapshot",
    description="Restore a collaboration document from a snapshot"
)
async def restore_snapshot(
    doc_id: str,
    body: RestoreRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Restore a document from a snapshot"""
    try:
        if not SAFE_ID.match(doc_id) or not SAFE_ID.match(body.snapshot_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid doc_id or snapshot_id format"
                ).model_dump()
            )

        snap_path = _snap_dir(doc_id) / body.snapshot_id
        if not snap_path.exists() or not snap_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Snapshot not found"
                ).model_dump()
            )

        data = snap_path.read_bytes()
        ok = apply_snapshot(doc_id, data)

        if not ok:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Restore failed"
                ).model_dump()
            )

        return SuccessResponse(
            data={"doc_id": doc_id, "snapshot_id": body.snapshot_id, "status": "restored"},
            message=f"Snapshot '{body.snapshot_id}' restored successfully"
        )

    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=str(e)
            ).model_dump()
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to restore snapshot {body.snapshot_id} for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to restore snapshot"
            ).model_dump()
        )


# ===== ACL Management Endpoints =====

class ACLEntry(BaseModel):
    user_id: str
    role: str  # owner, edit, view


class ACLUpsertRequest(BaseModel):
    user_id: str
    role: str


@router.get(
    "/docs/{doc_id}/acl",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_document_acl_entries",
    summary="Get ACL entries",
    description="Get access control entries for a collaboration document"
)
async def get_doc_acl(
    doc_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get ACL entries for a document"""
    try:
        if not SAFE_ID.match(doc_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid doc_id format"
                ).model_dump()
            )

        acl_entries = list_acl(doc_id)
        acl_list = [{"user_id": user_id, "role": role} for user_id, role in acl_entries]

        return SuccessResponse(
            data={"doc_id": doc_id, "acl": acl_list},
            message=f"Retrieved {len(acl_list)} ACL entr{'y' if len(acl_list) == 1 else 'ies'}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve ACL for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve ACL"
            ).model_dump()
        )


@router.post(
    "/docs/{doc_id}/acl",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    name="set_document_acl_entry",
    summary="Set ACL entry",
    description="Set or update an access control entry for a collaboration document"
)
async def set_doc_acl(
    doc_id: str,
    body: ACLUpsertRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Set/update ACL entry for a document

    Note: First-cut implementation allows any authenticated user to set ACL.
    In production, restrict to document owner or admin.
    """
    try:
        if not SAFE_ID.match(doc_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid doc_id format"
                ).model_dump()
            )

        # Validate role
        if body.role not in ("owner", "edit", "view"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid role. Must be: owner, edit, or view"
                ).model_dump()
            )

        upsert_acl(doc_id, body.user_id, body.role)

        return SuccessResponse(
            data={
                "doc_id": doc_id,
                "user_id": body.user_id,
                "role": body.role
            },
            message=f"ACL entry for user '{body.user_id}' set to '{body.role}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update ACL for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update ACL"
            ).model_dump()
        )
