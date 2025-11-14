"""
Vault Documents Routes - Document CRUD operations
"""

import logging
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends

from api.auth_middleware import get_current_user
from api.permission_engine import require_perm_team, require_perm
from api.team_service import is_team_member
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/documents", response_model=VaultDocument)
@require_perm_team("vault.documents.create", level="write")
async def create_vault_document(
    vault_type: str,
    document: VaultDocumentCreate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Store encrypted vault document (Phase 3: team-aware)

    Security: All encryption happens client-side
    Server only stores encrypted blobs

    vault_type options:
    - "personal": Personal vault (E2E encrypted, Founder Rights cannot decrypt)
    - "decoy": Decoy vault (plausible deniability)
    - "team": Team vault (requires team_id, Founder Rights can decrypt metadata)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Map API vault_type to DB vault_type for payload validation
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'
    if document.vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="document.vault_type must be 'real' or 'decoy'")
    if document.vault_type != db_vault_type:
        raise HTTPException(status_code=400, detail="Vault type mismatch between route and payload")

    service = get_vault_service()
    return service.store_document(user_id, document, team_id=team_id)


@router.get("/documents", response_model=VaultListResponse)
@require_perm_team("vault.documents.read", level="read")
async def list_vault_documents(
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all vault documents (Phase 3: team-aware)

    Returns encrypted blobs that must be decrypted client-side

    vault_type options:
    - "personal": Personal vault documents
    - "decoy": Decoy vault documents
    - "team": Team vault documents (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    if vault_type == 'real':
        vault_type = 'personal'

    service = get_vault_service()
    return service.list_documents(user_id, vault_type, team_id=team_id)


@router.get("/documents/{doc_id}", response_model=VaultDocument)
@require_perm_team("vault.documents.read", level="read")
async def get_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get single vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    doc = service.get_document(user_id, doc_id, db_vault_type, team_id=team_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.put("/documents/{doc_id}", response_model=VaultDocument)
@require_perm_team("vault.documents.update", level="write")
async def update_vault_document(
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    return service.update_document(user_id, doc_id, db_vault_type, update, team_id=team_id)


@router.delete("/documents/{doc_id}")
@require_perm_team("vault.documents.delete", level="write")
async def delete_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete vault document (soft delete, Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    success = service.delete_document(user_id, doc_id, db_vault_type, team_id=team_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"success": True, "message": "Document deleted"}


@router.get("/stats")
@require_perm("vault.use")
async def get_vault_stats(
    vault_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get vault statistics (Phase 1: uses authenticated user_id)"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.get_vault_stats(user_id, vault_type)
