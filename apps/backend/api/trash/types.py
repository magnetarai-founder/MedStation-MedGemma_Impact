"""
Trash Types - Models for the soft-delete trash system

Extracted from trash_service.py during P2 decomposition.
Contains:
- TrashItem model (soft-deleted item data)
- TrashStats model (trash statistics)
"""

from typing import Optional

from pydantic import BaseModel


class TrashItem(BaseModel):
    """Trash item (soft-deleted document or file)

    Attributes:
        id: Unique trash entry ID
        user_id: Owner user ID
        vault_type: 'real' or 'decoy' vault
        item_type: 'document', 'file', or 'folder'
        item_id: Original item ID
        item_name: Display name
        deleted_at: When item was deleted
        permanent_delete_at: Auto-delete date (30 days after deletion)
        original_data: JSON blob with original item data for restoration
    """
    id: str
    user_id: str
    vault_type: str
    item_type: str
    item_id: str
    item_name: str
    deleted_at: str
    permanent_delete_at: str
    original_data: str


class TrashStats(BaseModel):
    """Trash statistics

    Attributes:
        total_items: Total items in trash
        document_count: Number of documents
        file_count: Number of files
        folder_count: Number of folders
        total_size_bytes: Total size of trashed items
        oldest_item_date: Date of oldest trashed item
    """
    total_items: int
    document_count: int
    file_count: int
    folder_count: int
    total_size_bytes: int
    oldest_item_date: Optional[str]


__all__ = [
    "TrashItem",
    "TrashStats",
]
