"""
Automation module for workflow automation.

Provides:
- router: FastAPI router for automation endpoints
- AutomationStorage: Storage layer for automation data
- Types: Pydantic models for automation requests/responses

Submodules:
- n8n: N8N workflow integration
"""

from api.automation.router import router
from api.automation.storage import AutomationStorage, get_automation_storage
from api.automation.types import (
    WorkflowNode,
    WorkflowEdge,
    WorkflowRunRequest,
    WorkflowSaveRequest,
    WorkflowRunResponse,
    WorkflowSaveResponse,
    WorkflowSemanticSearchRequest,
    WorkflowSearchResult,
    WorkflowSemanticSearchResponse,
)

__all__ = [
    "router",
    "AutomationStorage",
    "get_automation_storage",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowRunRequest",
    "WorkflowSaveRequest",
    "WorkflowRunResponse",
    "WorkflowSaveResponse",
    "WorkflowSemanticSearchRequest",
    "WorkflowSearchResult",
    "WorkflowSemanticSearchResponse",
]
