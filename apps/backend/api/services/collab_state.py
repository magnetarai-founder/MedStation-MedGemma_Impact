"""
Collaboration state bridge (snapshot apply hook).

Purpose
-------
Provide a simple runtime hook so the WebSocket collab server can register
an in-process snapshot applier function. REST handlers (e.g., snapshot
restore) can call this without importing internal WS server state.

Usage (in collab_ws.py):
    from api.services.collab_state import set_snapshot_applier

    def _apply_snapshot_impl(doc_id: str, snapshot_bytes: bytes) -> bool:
        # Locate in-memory Y.Doc for doc_id and apply snapshot, then
        # broadcast update to connected clients. Return True on success.
        ...

    set_snapshot_applier(_apply_snapshot_impl)

Then, REST endpoint can call:
    from api.services.collab_state import apply_snapshot
    apply_snapshot(doc_id, data)

Thread-safety
-------------
The implementer should ensure that applying a snapshot is thread-safe with
the WS server loop (e.g., by scheduling work onto the WS event loop or by
using appropriate locks around the Y.Doc instance).
"""

from __future__ import annotations

from typing import Callable, Optional

SnapshotApplier = Callable[[str, bytes], bool]

_APPLIER: Optional[SnapshotApplier] = None


def set_snapshot_applier(func: SnapshotApplier) -> None:
    """Register the process-wide snapshot applier.

    Args:
        func: callable(doc_id: str, snapshot_bytes: bytes) -> bool
    """
    global _APPLIER
    _APPLIER = func


def apply_snapshot(doc_id: str, snapshot_bytes: bytes) -> bool:
    """Apply a snapshot to the in-memory collab doc via registered applier.

    Returns:
        True on success.

    Raises:
        NotImplementedError: if no applier has been registered yet.
    """
    if _APPLIER is None:
        raise NotImplementedError("Collab snapshot applier not registered")
    return _APPLIER(doc_id, snapshot_bytes)

