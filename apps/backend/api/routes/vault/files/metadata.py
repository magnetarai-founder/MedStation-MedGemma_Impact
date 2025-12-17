"""
Vault Files Metadata Routes (Compatibility Wrapper)

This module maintains backwards compatibility by re-exporting the combined
router from the refactored metadata submodule.

The original 1,511-line metadata.py has been refactored into focused modules
organized under api/routes/vault/files/metadata/:
- tags.py - Tag management (add/remove/get tags)
- favorites.py - Favorites and pinned files
- activity.py - Access logging, recent files, storage stats, audit logs
- versions.py - File versions (get/restore/delete)
- trash.py - Trash operations and secure deletion
- comments.py - File comments CRUD
- metadata_ops.py - Metadata set/get operations
- export.py - Vault data export

All functionality is preserved exactly as before. This wrapper ensures
that existing imports continue to work without modification.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

# Import all sub-routers and combine them
from fastapi import APIRouter
from api.routes.vault.files.metadata import (
    tags, favorites, activity, versions, trash,
    comments, metadata_ops, export
)

# Create the combined router (replicate the __init__.py logic)
router = APIRouter()

# Include all sub-routers
router.include_router(tags.router, tags=["Vault Files - Tags"])
router.include_router(favorites.router, tags=["Vault Files - Favorites"])
router.include_router(activity.router, tags=["Vault Files - Activity"])
router.include_router(versions.router, tags=["Vault Files - Versions"])
router.include_router(trash.router, tags=["Vault Files - Trash"])
router.include_router(comments.router, tags=["Vault Files - Comments"])
router.include_router(metadata_ops.router, tags=["Vault Files - Metadata"])
router.include_router(export.router, tags=["Vault Files - Export"])

__all__ = ["router"]
