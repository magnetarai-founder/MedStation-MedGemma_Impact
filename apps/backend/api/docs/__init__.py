"""
Documents Package

Provides document storage and syncing for ElohimOS:
- Documents, Spreadsheets, and Insights Lab
- Notion-style periodic sync with conflict resolution
- Security level support (public, private, team, sensitive, top-secret)
"""

from api.docs.models import (
    VALID_DOC_TYPES,
    VALID_SECURITY_LEVELS,
    DocumentCreate,
    DocumentUpdate,
    Document,
    SyncRequest,
    SyncResponse,
)
from api.docs.db import (
    DOCS_DB_PATH,
    DOCUMENT_UPDATE_COLUMNS,
    build_safe_update,
    init_db,
    get_db,
    release_db,
)
from api.docs.routes import router

__all__ = [
    # Models
    "VALID_DOC_TYPES",
    "VALID_SECURITY_LEVELS",
    "DocumentCreate",
    "DocumentUpdate",
    "Document",
    "SyncRequest",
    "SyncResponse",
    # Database
    "DOCS_DB_PATH",
    "DOCUMENT_UPDATE_COLUMNS",
    "build_safe_update",
    "init_db",
    "get_db",
    "release_db",
    # Router
    "router",
]
