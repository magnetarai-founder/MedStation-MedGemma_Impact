"""
Collaboration ACL Admin Routes

Provides endpoints for managing document access control lists (ACLs).
Owner-only operations for granting/revoking document access.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import re
import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.services.collab_acl import (
    user_can_access_doc,
    list_acl,
    upsert_acl,
    ROLES,
)
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collab", tags=["collab-acl"])

SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


class AclRow(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern=r"^(owner|edit|view)$")


def _require_owner(current_user: dict, doc_id: str) -> None:
    """Require owner role for document (raises HTTPException if not)"""
    if not SAFE_ID.match(doc_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Invalid doc_id format"
            ).model_dump()
        )
    uid = current_user.get("user_id")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error_code=ErrorCode.UNAUTHORIZED,
                message="User not authenticated"
            ).model_dump()
        )
    if not user_can_access_doc(uid, doc_id, min_role="owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                error_code=ErrorCode.FORBIDDEN,
                message="Owner role required"
            ).model_dump()
        )


@router.get(
    "/docs/{doc_id}/acl",
    response_model=SuccessResponse[List[AclRow]],
    status_code=status.HTTP_200_OK,
    name="get_document_acl",
    summary="Get document ACL",
    description="List access control entries for a document (owner-only)"
)
async def get_acl(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[AclRow]]:
    """
    List ACL rows for a document

    Security:
    - Requires owner role on document
    """
    try:
        _require_owner(current_user, doc_id)
        rows = list_acl(doc_id)
        acl_rows = [AclRow(user_id=u, role=r) for (u, r) in rows]

        return SuccessResponse(
            data=acl_rows,
            message=f"Retrieved {len(acl_rows)} ACL entr{'y' if len(acl_rows) == 1 else 'ies'}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get ACL for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve document ACL"
            ).model_dump()
        )


@router.post(
    "/docs/{doc_id}/acl",
    response_model=SuccessResponse[AclRow],
    status_code=status.HTTP_201_CREATED,
    name="upsert_document_acl",
    summary="Upsert ACL entry",
    description="Create or update a document ACL entry (owner-only)"
)
async def upsert_acl_entry(
    doc_id: str,
    body: AclRow,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[AclRow]:
    """
    Create or update an ACL entry

    Security:
    - Requires owner role on document
    - Role must be one of: owner, edit, view
    """
    try:
        _require_owner(current_user, doc_id)

        if body.role not in ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid role. Must be one of: {', '.join(ROLES)}"
                ).model_dump()
            )

        # Prevent privilege lockout: owner cannot demote the last owner (naive safeguard omitted for brevity)
        upsert_acl(doc_id, body.user_id, body.role)

        return SuccessResponse(
            data=body,
            message=f"ACL entry for user '{body.user_id}' set to '{body.role}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to upsert ACL for doc {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update document ACL"
            ).model_dump()
        )

