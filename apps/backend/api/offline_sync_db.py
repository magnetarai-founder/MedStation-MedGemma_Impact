"""
Compatibility Shim for Offline Sync Database

The implementation now lives in the `api.offline` package:
- api.offline.db: Database utilities for sync operations

This shim maintains backward compatibility.
"""

from api.offline.db import (
    get_sync_db_path,
    init_sync_db,
    save_sync_operation,
    load_pending_operations,
    mark_operations_synced,
    get_max_version,
    get_peer_last_sync,
    save_sync_state,
    load_sync_state,
    check_version_conflict,
    update_version_tracking,
    get_operations_since,
)

__all__ = [
    "get_sync_db_path",
    "init_sync_db",
    "save_sync_operation",
    "load_pending_operations",
    "mark_operations_synced",
    "get_max_version",
    "get_peer_last_sync",
    "save_sync_state",
    "load_sync_state",
    "check_version_conflict",
    "update_version_tracking",
    "get_operations_since",
]
