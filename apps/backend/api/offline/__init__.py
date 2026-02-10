"""
Offline Package

Offline-first data synchronization for MedStation:
- CRDT-based conflict-free sync
- Database sync utilities
- Peer discovery for mesh networks
- File sharing for offline environments
"""

from api.offline.models import (
    SYNCABLE_TABLES,
    SyncOperation,
    SyncState,
    SYNC_OPERATIONS_SCHEMA,
    PEER_SYNC_STATE_SCHEMA,
    VERSION_TRACKING_SCHEMA,
)
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
)
from api.offline.file_share import (
    SharedFile,
    FileTransferProgress,
    OfflineFileShare,
    get_file_share,
)
from api.offline.mesh_discovery import (
    LocalPeer,
    OfflineMeshDiscovery,
    get_mesh_discovery,
)

__all__ = [
    # Models
    "SYNCABLE_TABLES",
    "SyncOperation",
    "SyncState",
    "SYNC_OPERATIONS_SCHEMA",
    "PEER_SYNC_STATE_SCHEMA",
    "VERSION_TRACKING_SCHEMA",
    # Database utilities
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
    # File sharing
    "SharedFile",
    "FileTransferProgress",
    "OfflineFileShare",
    "get_file_share",
    # Mesh discovery
    "LocalPeer",
    "OfflineMeshDiscovery",
    "get_mesh_discovery",
]
