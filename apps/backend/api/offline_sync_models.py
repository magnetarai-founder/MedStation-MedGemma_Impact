"""
Compatibility Shim for Offline Sync Models

The implementation now lives in the `api.offline` package:
- api.offline.models: Sync dataclasses and constants

This shim maintains backward compatibility.
"""

from api.offline.models import (
    SYNCABLE_TABLES,
    SyncOperation,
    SyncState,
    SYNC_OPERATIONS_SCHEMA,
    PEER_SYNC_STATE_SCHEMA,
    VERSION_TRACKING_SCHEMA,
)

__all__ = [
    "SYNCABLE_TABLES",
    "SyncOperation",
    "SyncState",
    "SYNC_OPERATIONS_SCHEMA",
    "PEER_SYNC_STATE_SCHEMA",
    "VERSION_TRACKING_SCHEMA",
]
