"""Backward Compatibility Shim - use api.db instead."""

from api.db.consolidation_migration import (
    migrate_databases,
    backup_old_databases,
    attach_and_copy,
    PATHS,
)

__all__ = [
    "migrate_databases",
    "backup_old_databases",
    "attach_and_copy",
    "PATHS",
]
