"""Backward Compatibility Shim - use api.docs instead."""

from api.docs.db import (
    PATHS,
    DOCS_DB_PATH,
    DOCUMENT_UPDATE_COLUMNS,
    build_safe_update,
    init_db,
    get_db,
    release_db,
    logger,
)

__all__ = [
    "PATHS",
    "DOCS_DB_PATH",
    "DOCUMENT_UPDATE_COLUMNS",
    "build_safe_update",
    "init_db",
    "get_db",
    "release_db",
    "logger",
]
