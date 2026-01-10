"""
Docs & Sheets Service - Facade Module

Foundation must be solid.
"The Lord is my rock, my firm foundation." - Psalm 18:2

This service provides collaborative document storage and syncing
for Documents, Spreadsheets, and Insights Lab.

Implements Notion-style periodic sync with conflict resolution.

This module serves as a backward-compatible facade that re-exports functions
from extracted modules. Direct imports from extracted modules are preferred
for new code.

Extracted modules (P2 decomposition):
- docs_models.py: Pydantic models for Documents
- docs_db.py: Database utilities and connection pool
- docs_routes.py: FastAPI route endpoints
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Re-export models for backward compatibility
from .docs_models import (
    VALID_DOC_TYPES,
    VALID_SECURITY_LEVELS,
    DocumentCreate,
    DocumentUpdate,
    Document,
    SyncRequest,
    SyncResponse,
)

# Re-export database utilities for backward compatibility
from .docs_db import (
    PATHS,
    DOCS_DB_PATH,
    DOCUMENT_UPDATE_COLUMNS,
    build_safe_update,
    init_db,
    get_db,
    release_db,
)

# Re-export router for backward compatibility
from .docs_routes import router

# Re-export auth dependencies for backward compatibility (used by tests)
try:
    from auth_middleware import get_current_user
    from api.services.team import is_team_member
    from utils import get_user_id
except ImportError:
    from api.auth_middleware import get_current_user
    from api.services.team import is_team_member
    from api.utils import get_user_id


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
    "PATHS",
    "DOCS_DB_PATH",
    "DOCUMENT_UPDATE_COLUMNS",
    "build_safe_update",
    "init_db",
    "get_db",
    "release_db",
    # Router
    "router",
    # Auth dependencies (for backward compatibility)
    "get_current_user",
    "is_team_member",
    "get_user_id",
]
