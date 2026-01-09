"""
Code Operations Package

File browsing and operations for Code Tab.
Delegates to services/code_editor for business logic.

Components:
- models.py: Pydantic request/response models
- library_db.py: Project library SQLite operations
- file_routes.py: File tree, read, write, delete, diff operations
- library_routes.py: Project library CRUD endpoints
- git_routes.py: Git log and workspace operations
"""

from fastapi import APIRouter

from api.code_operations.models import (
    ProjectLibraryDocument,
    UpdateDocumentRequest,
    WorkspaceRootRequest,
)
from api.code_operations.library_db import (
    get_library_db_path,
    init_library_db,
    get_documents,
    create_document,
    update_document,
    delete_document,
)
from api.code_operations.file_routes import (
    router as file_router,
    health_check,
    get_file_tree,
    read_file,
    get_workspace_info,
    preview_diff,
    write_file,
    delete_file,
)
from api.code_operations.library_routes import (
    router as library_router,
    get_library_documents,
    create_library_document,
    update_library_document,
    delete_library_document,
)
from api.code_operations.git_routes import (
    router as git_router,
    set_workspace_root,
    get_git_log,
)

# Create main router that includes all sub-routers
router = APIRouter(prefix="/api/v1/code", tags=["code"])
router.include_router(file_router)
router.include_router(library_router)
router.include_router(git_router)


__all__ = [
    # Main router
    "router",
    # Models
    "ProjectLibraryDocument",
    "UpdateDocumentRequest",
    "WorkspaceRootRequest",
    # Library DB functions
    "get_library_db_path",
    "init_library_db",
    "get_documents",
    "create_document",
    "update_document",
    "delete_document",
    # File endpoints
    "health_check",
    "get_file_tree",
    "read_file",
    "get_workspace_info",
    "preview_diff",
    "write_file",
    "delete_file",
    # Library endpoints
    "get_library_documents",
    "create_library_document",
    "update_library_document",
    "delete_library_document",
    # Git endpoints
    "set_workspace_root",
    "get_git_log",
]
