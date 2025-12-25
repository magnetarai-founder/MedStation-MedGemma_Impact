"""
Workflow Storage - Service Module Re-export

Re-exports workflow storage from the main api module for consistency
with other service imports.
"""

# Re-export from parent api directory
try:
    from api.workflow_storage import WorkflowStorage, get_workflow_storage
except ImportError:
    from workflow_storage import WorkflowStorage, get_workflow_storage

__all__ = ["WorkflowStorage", "get_workflow_storage"]
