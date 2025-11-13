"""
Vault Service Schemas

Pydantic models for vault documents, files, and folders.
All encryption happens client-side; server only stores encrypted blobs.
"""

from typing import List
from pydantic import BaseModel, Field


class VaultDocument(BaseModel):
    """Encrypted vault document"""
    id: str
    user_id: str
    vault_type: str = Field(..., description="'real' or 'decoy'")
    encrypted_blob: str = Field(..., description="Client-side encrypted document data")
    encrypted_metadata: str = Field(..., description="Client-side encrypted metadata")
    created_at: str
    updated_at: str
    size_bytes: int


class VaultDocumentCreate(BaseModel):
    """Request to create vault document"""
    id: str
    vault_type: str  # 'real' or 'decoy'
    encrypted_blob: str
    encrypted_metadata: str


class VaultDocumentUpdate(BaseModel):
    """Request to update vault document"""
    encrypted_blob: str
    encrypted_metadata: str


class VaultListResponse(BaseModel):
    """List of vault documents"""
    documents: List[VaultDocument]
    total_count: int


class VaultFile(BaseModel):
    """Encrypted vault file"""
    id: str
    user_id: str
    vault_type: str
    filename: str
    file_size: int
    mime_type: str
    encrypted_path: str
    folder_path: str = "/"  # Default to root folder
    created_at: str
    updated_at: str


class VaultFolder(BaseModel):
    """Vault folder"""
    id: str
    user_id: str
    vault_type: str
    folder_name: str
    folder_path: str  # Full path like "/Documents/Medical"
    parent_path: str  # Parent folder path
    created_at: str
    updated_at: str
