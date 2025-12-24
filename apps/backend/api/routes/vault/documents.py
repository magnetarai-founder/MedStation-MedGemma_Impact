"""
Vault Documents Routes

Document CRUD operations with E2E encryption and team support.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.permission_engine import require_perm_team, require_perm
from api.services.team import is_team_member
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
)
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vault", tags=["vault-documents"])


@router.post(
    "/documents",
    response_model=SuccessResponse[VaultDocument],
    status_code=status.HTTP_201_CREATED,
    name="create_vault_document",
    summary="Create vault document",
    description="Store encrypted vault document (personal, decoy, or team vault with E2E encryption)"
)
@require_perm_team("vault.documents.create", level="write")
async def create_vault_document(
    vault_type: str,
    document: VaultDocumentCreate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultDocument]:
    """
    Store encrypted vault document (Phase 3: team-aware)

    Security: All encryption happens client-side
    Server only stores encrypted blobs

    vault_type options:
    - "personal": Personal vault (E2E encrypted, Founder Rights cannot decrypt)
    - "decoy": Decoy vault (plausible deniability)
    - "team": Team vault (requires team_id, Founder Rights can decrypt metadata)
    """
    try:
        user_id = current_user["user_id"]

        # Phase 3: Support team vault type
        if vault_type not in ('personal', 'decoy', 'team'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'personal', 'decoy', or 'team'"
                ).model_dump()
            )

        # Phase 3: Team vault requires team_id and membership
        if vault_type == 'team':
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="team_id required for team vault"
                    ).model_dump()
                )
            if not is_team_member(team_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message="Not a member of this team"
                    ).model_dump()
                )

        # Map API vault_type to DB vault_type for payload validation
        db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'
        if document.vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="document.vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )
        if document.vault_type != db_vault_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Vault type mismatch between route and payload"
                ).model_dump()
            )

        service = get_vault_service()
        doc = service.store_document(user_id, document, team_id=team_id)

        return SuccessResponse(
            data=doc,
            message=f"Document created successfully in {vault_type} vault"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create vault document", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create document"
            ).model_dump()
        )


@router.get(
    "/documents",
    response_model=SuccessResponse[VaultListResponse],
    status_code=status.HTTP_200_OK,
    name="list_vault_documents",
    summary="List vault documents",
    description="List all encrypted vault documents (personal, decoy, or team vault)"
)
@require_perm_team("vault.documents.read", level="read")
async def list_vault_documents(
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultListResponse]:
    """
    List all vault documents (Phase 3: team-aware)

    Returns encrypted blobs that must be decrypted client-side

    vault_type options:
    - "personal": Personal vault documents
    - "decoy": Decoy vault documents
    - "team": Team vault documents (requires team_id and membership)
    """
    try:
        user_id = current_user["user_id"]

        # Phase 3: Support team vault type
        if vault_type not in ('personal', 'decoy', 'team'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'personal', 'decoy', or 'team'"
                ).model_dump()
            )

        # Phase 3: Team vault requires team_id and membership
        if vault_type == 'team':
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="team_id required for team vault"
                    ).model_dump()
                )
            if not is_team_member(team_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message="Not a member of this team"
                    ).model_dump()
                )

        # Legacy compatibility: 'real' -> 'personal'
        if vault_type == 'real':
            vault_type = 'personal'

        service = get_vault_service()
        docs = service.list_documents(user_id, vault_type, team_id=team_id)

        return SuccessResponse(
            data=docs,
            message=f"Retrieved documents from {vault_type} vault"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list vault documents", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve documents"
            ).model_dump()
        )


@router.get(
    "/documents/{doc_id}",
    response_model=SuccessResponse[VaultDocument],
    status_code=status.HTTP_200_OK,
    name="get_vault_document",
    summary="Get vault document",
    description="Get single encrypted vault document by ID"
)
@require_perm_team("vault.documents.read", level="read")
async def get_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultDocument]:
    """
    Get single vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    try:
        user_id = current_user["user_id"]

        # Phase 3: Support team vault type
        if vault_type not in ('personal', 'decoy', 'team'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'personal', 'decoy', or 'team'"
                ).model_dump()
            )

        # Phase 3: Team vault requires team_id and membership
        if vault_type == 'team':
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="team_id required for team vault"
                    ).model_dump()
                )
            if not is_team_member(team_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message="Not a member of this team"
                    ).model_dump()
                )

        # Legacy compatibility: 'real' -> 'personal'
        db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

        service = get_vault_service()
        doc = service.get_document(user_id, doc_id, db_vault_type, team_id=team_id)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Document not found"
                ).model_dump()
            )

        return SuccessResponse(
            data=doc,
            message="Document retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get vault document {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve document"
            ).model_dump()
        )


@router.put(
    "/documents/{doc_id}",
    response_model=SuccessResponse[VaultDocument],
    status_code=status.HTTP_200_OK,
    name="update_vault_document",
    summary="Update vault document",
    description="Update encrypted vault document (partial updates supported)"
)
@require_perm_team("vault.documents.update", level="write")
async def update_vault_document(
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultDocument]:
    """
    Update vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    try:
        user_id = current_user["user_id"]

        # Phase 3: Support team vault type
        if vault_type not in ('personal', 'decoy', 'team'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'personal', 'decoy', or 'team'"
                ).model_dump()
            )

        # Phase 3: Team vault requires team_id and membership
        if vault_type == 'team':
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="team_id required for team vault"
                    ).model_dump()
                )
            if not is_team_member(team_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message="Not a member of this team"
                    ).model_dump()
                )

        # Legacy compatibility: 'real' -> 'personal'
        db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

        service = get_vault_service()
        doc = service.update_document(user_id, doc_id, db_vault_type, update, team_id=team_id)

        return SuccessResponse(
            data=doc,
            message="Document updated successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update vault document {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update document"
            ).model_dump()
        )


class DeleteDocumentResponse(BaseModel):
    success: bool
    doc_id: str


@router.delete(
    "/documents/{doc_id}",
    response_model=SuccessResponse[DeleteDocumentResponse],
    status_code=status.HTTP_200_OK,
    name="delete_vault_document",
    summary="Delete vault document",
    description="Delete encrypted vault document (soft delete)"
)
@require_perm_team("vault.documents.delete", level="write")
async def delete_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[DeleteDocumentResponse]:
    """
    Delete vault document (soft delete, Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    try:
        user_id = current_user["user_id"]

        # Phase 3: Support team vault type
        if vault_type not in ('personal', 'decoy', 'team'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'personal', 'decoy', or 'team'"
                ).model_dump()
            )

        # Phase 3: Team vault requires team_id and membership
        if vault_type == 'team':
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="team_id required for team vault"
                    ).model_dump()
                )
            if not is_team_member(team_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message="Not a member of this team"
                    ).model_dump()
                )

        # Legacy compatibility: 'real' -> 'personal'
        db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

        service = get_vault_service()
        success = service.delete_document(user_id, doc_id, db_vault_type, team_id=team_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Document not found"
                ).model_dump()
            )

        return SuccessResponse(
            data=DeleteDocumentResponse(success=True, doc_id=doc_id),
            message="Document deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete vault document {doc_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete document"
            ).model_dump()
        )


@router.get(
    "/stats",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_vault_stats",
    summary="Get vault statistics",
    description="Get vault usage statistics and metrics"
)
@require_perm("vault.use")
async def get_vault_stats(
    vault_type: str,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get vault statistics (Phase 1: uses authenticated user_id)"""
    try:
        user_id = current_user["user_id"]

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        service = get_vault_service()
        stats = service.get_vault_stats(user_id, vault_type)

        return SuccessResponse(
            data=stats,
            message=f"Retrieved {vault_type} vault statistics"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get vault stats", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve vault statistics"
            ).model_dump()
        )
