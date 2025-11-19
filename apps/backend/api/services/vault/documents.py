"""
Vault Documents Operations

Handles all document-related operations for vault service.
Documents are encrypted client-side; server stores encrypted blobs.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException

from .schemas import VaultDocument, VaultDocumentCreate, VaultDocumentUpdate, VaultListResponse
from . import storage

logger = logging.getLogger(__name__)


def store_document(
    service,
    user_id: str,
    doc: VaultDocumentCreate,
    team_id: Optional[str] = None
) -> VaultDocument:
    """
    Store encrypted vault document

    Args:
        service: VaultService instance (for db_path/files_path access)
        user_id: User ID from auth
        doc: Encrypted document data
        team_id: Optional team ID for team-scoped documents

    Returns:
        Stored vault document
    """
    return storage.store_document_record(user_id, doc, team_id)


def get_document(
    service,
    user_id: str,
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> Optional[VaultDocument]:
    """
    Get encrypted vault document by ID (Phase 3: optional team scope)

    Args:
        service: VaultService instance
        user_id: User ID
        doc_id: Document ID
        vault_type: Vault type ('real' or 'decoy')
        team_id: Optional team ID

    Returns:
        VaultDocument if found, None otherwise
    """
    return storage.get_document_record(user_id, doc_id, vault_type, team_id)


def list_documents(
    service,
    user_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> VaultListResponse:
    """
    List all vault documents for a user and vault type

    Phase 3: if team_id is provided, return team-scoped documents.

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: Vault type
        team_id: Optional team ID

    Returns:
        VaultListResponse with documents and count
    """
    documents = storage.list_documents_records(user_id, vault_type, team_id)
    return VaultListResponse(
        documents=documents,
        total_count=len(documents)
    )


def update_document(
    service,
    user_id: str,
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate,
    team_id: Optional[str] = None
) -> VaultDocument:
    """
    Update encrypted vault document (Phase 3: optional team scope)

    Args:
        service: VaultService instance
        user_id: User ID
        doc_id: Document ID
        vault_type: Vault type
        update: Document update data
        team_id: Optional team ID

    Returns:
        Updated VaultDocument

    Raises:
        HTTPException: If document not found or update fails
    """
    success, rowcount = storage.update_document_record(user_id, doc_id, vault_type, update, team_id)

    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    # Fetch updated document
    updated_doc = get_document(service, user_id, doc_id, vault_type, team_id=team_id)
    if not updated_doc:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated document")

    return updated_doc


def delete_document(
    service,
    user_id: str,
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> bool:
    """
    Soft-delete vault document (Phase 3: optional team scope)

    Args:
        service: VaultService instance
        user_id: User ID
        doc_id: Document ID
        vault_type: Vault type
        team_id: Optional team ID

    Returns:
        True if document was deleted, False otherwise
    """
    return storage.delete_document_record(user_id, doc_id, vault_type, team_id)


def get_vault_stats(service, user_id: str, vault_type: str) -> Dict[str, Any]:
    """
    Get vault statistics

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: Vault type

    Returns:
        Dictionary with document_count, total_size_bytes, vault_type
    """
    return storage.get_vault_stats_record(user_id, vault_type)
