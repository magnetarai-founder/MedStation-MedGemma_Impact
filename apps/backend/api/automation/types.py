"""
Automation Types - Request/response models for workflow automation

Extracted from automation_router.py during P2 decomposition.
Contains:
- WorkflowNode, WorkflowEdge (graph structure)
- WorkflowRunRequest, WorkflowSaveRequest (input models)
- WorkflowRunResponse, WorkflowSaveResponse (output models)
- Semantic search models
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


# ===== Graph Structure Models =====

class WorkflowNode(BaseModel):
    """Node in a workflow graph"""
    id: str
    type: str
    position: Dict[str, float]
    label: str


class WorkflowEdge(BaseModel):
    """Edge connecting workflow nodes"""
    source: str
    target: str


# ===== Request Models =====

class WorkflowRunRequest(BaseModel):
    """Request to run a workflow"""
    workflow_id: str
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowSaveRequest(BaseModel):
    """Request to save a workflow"""
    workflow_id: str
    name: str
    nodes: List[Any]
    edges: List[Any]


# ===== Response Models =====

class WorkflowRunResponse(BaseModel):
    """Response from workflow execution"""
    status: str
    workflow_id: str
    workflow_name: str
    steps_executed: int
    execution_time_ms: int
    results: Dict[str, Any]


class WorkflowSaveResponse(BaseModel):
    """Response from workflow save"""
    status: str
    workflow_id: str
    saved_at: str


# ===== Semantic Search Models =====

class WorkflowSemanticSearchRequest(BaseModel):
    """Request for semantic workflow search"""
    query: str
    limit: int = 10
    min_similarity: float = 0.4


class WorkflowSearchResult(BaseModel):
    """Single result from workflow search"""
    workflow_id: str
    workflow_name: str
    description: Optional[str]
    created_at: str
    similarity_score: float


class WorkflowSemanticSearchResponse(BaseModel):
    """Response with workflow search results"""
    results: List[WorkflowSearchResult]
    query: str
    total_results: int


__all__ = [
    # Graph structure
    "WorkflowNode",
    "WorkflowEdge",
    # Request models
    "WorkflowRunRequest",
    "WorkflowSaveRequest",
    "WorkflowSemanticSearchRequest",
    # Response models
    "WorkflowRunResponse",
    "WorkflowSaveResponse",
    "WorkflowSearchResult",
    "WorkflowSemanticSearchResponse",
]
