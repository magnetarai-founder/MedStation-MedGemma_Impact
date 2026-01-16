"""
Compatibility Shim for Offline File Share

The implementation now lives in the `api.offline` package:
- api.offline.file_share: OfflineFileShare class

This shim maintains backward compatibility.
"""

from api.offline.file_share import (
    SharedFile,
    FileTransferProgress,
    OfflineFileShare,
    get_file_share,
)

__all__ = [
    "SharedFile",
    "FileTransferProgress",
    "OfflineFileShare",
    "get_file_share",
]
