"""Backward Compatibility Shim - use api.workflows.p2p_sync instead."""

from api.workflows.p2p_sync import (
    WorkflowP2PSync,
    get_workflow_sync,
    init_workflow_sync,
    logger,
    WORKFLOW_SYNC_PROTOCOL,
    _workflow_sync_instance,
)

__all__ = [
    "WorkflowP2PSync",
    "get_workflow_sync",
    "init_workflow_sync",
    "logger",
    "WORKFLOW_SYNC_PROTOCOL",
    "_workflow_sync_instance",
]
