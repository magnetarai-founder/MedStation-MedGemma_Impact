"""
Automation Workflow Router
Handles workflow execution and management
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from fastapi import Depends
from auth_middleware import get_current_user
from utils import sanitize_for_log

router = APIRouter(
    prefix="/api/v1/automation",
    tags=["automation"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


class WorkflowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    label: str


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowSaveRequest(BaseModel):
    workflow_id: str
    name: str
    nodes: List[Any]
    edges: List[Any]


class WorkflowRunResponse(BaseModel):
    status: str
    workflow_id: str
    workflow_name: str
    steps_executed: int
    execution_time_ms: int
    results: Dict[str, Any]


class WorkflowSaveResponse(BaseModel):
    status: str
    workflow_id: str
    saved_at: str


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(request: Request, body: WorkflowRunRequest):
    """
    Execute a workflow

    This is a simulation endpoint. In production, this would:
    1. Connect to n8n API to trigger workflow
    2. Or execute workflow steps internally
    3. Return execution results
    """
    start_time = datetime.now()

    # Sanitize workflow name for logging
    safe_name = sanitize_for_log(body.name)
    safe_id = sanitize_for_log(body.workflow_id)
    logger.info(f"🚀 Running workflow: {safe_name} (ID: {safe_id})")
    logger.info(f"   Nodes: {len(body.nodes)}, Edges: {len(body.edges)}")

    # Simulate workflow execution
    steps_executed = 0
    results = {}

    # Build execution graph
    node_map = {node.id: node for node in body.nodes}

    # Find trigger nodes (nodes with no incoming edges)
    incoming = {edge.target for edge in body.edges}
    trigger_nodes = [node for node in body.nodes if node.id not in incoming]

    if not trigger_nodes:
        raise HTTPException(status_code=400, detail="No trigger node found in workflow")

    # Execute nodes in order (simplified BFS)
    executed = set()
    queue = [n.id for n in trigger_nodes]

    while queue:
        node_id = queue.pop(0)
        if node_id in executed:
            continue

        node = node_map.get(node_id)
        if not node:
            continue

        # Simulate node execution
        await asyncio.sleep(0.1)  # Simulate processing time
        steps_executed += 1

        logger.info(f"   ✓ Executed: {node.label}")
        results[node_id] = {
            "node_label": node.label,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }

        executed.add(node_id)

        # Add dependent nodes to queue
        for edge in body.edges:
            if edge.source == node_id and edge.target not in executed:
                queue.append(edge.target)

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    logger.info(f"✅ Workflow completed: {steps_executed} steps in {execution_time}ms")

    return WorkflowRunResponse(
        status="success",
        workflow_id=body.workflow_id,
        workflow_name=body.name,
        steps_executed=steps_executed,
        execution_time_ms=execution_time,
        results=results
    )


@router.post("/save", response_model=WorkflowSaveResponse)
async def save_workflow(request: Request, body: WorkflowSaveRequest):
    """
    Save workflow configuration

    In production, this would save to database or n8n
    """
    safe_name = sanitize_for_log(body.name)
    safe_id = sanitize_for_log(body.workflow_id)
    logger.info(f"💾 Saving workflow: {safe_name} (ID: {safe_id})")

    # TODO: Save to database
    # For now, just simulate success

    return WorkflowSaveResponse(
        status="saved",
        workflow_id=body.workflow_id,
        saved_at=datetime.now().isoformat()
    )


@router.get("/workflows")
async def list_workflows():
    """
    List all saved workflows
    """
    # TODO: Fetch from database
    return {
        "workflows": [],
        "count": 0
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Get workflow by ID
    """
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(request: Request, workflow_id: str):
    """
    Delete workflow
    """
    # TODO: Delete from database
    return {"status": "deleted", "workflow_id": workflow_id}


# MARK: - Semantic Search


class WorkflowSemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    min_similarity: float = 0.4


class WorkflowSearchResult(BaseModel):
    workflow_id: str
    workflow_name: str
    description: Optional[str]
    created_at: str
    similarity_score: float


class WorkflowSemanticSearchResponse(BaseModel):
    results: List[WorkflowSearchResult]
    query: str
    total_results: int


@router.post("/workflows/semantic-search")
async def semantic_search_workflows(
    request: WorkflowSemanticSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic search for similar workflows using AI embeddings.
    Helps users find relevant workflow templates.
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"🔍 Workflow semantic search: user={user_id}, query='{request.query[:50]}...'")

        # Get embedding for query
        query_embedding = await _embed_query_workflow(request.query)

        if not query_embedding:
            logger.warning("⚠️ Embeddings unavailable")
            return WorkflowSemanticSearchResponse(
                results=[],
                query=request.query,
                total_results=0
            )

        # Get workflows from WorkflowService
        workflows = await _get_user_workflows(user_id)

        # Compute similarity for each workflow
        results = []
        for workflow in workflows:
            # Create searchable text from workflow metadata
            searchable_text = f"{workflow.get('name', '')} {workflow.get('description', '')}"

            # Get workflow embedding
            workflow_embedding = await _embed_query_workflow(searchable_text)

            if workflow_embedding:
                # Compute cosine similarity
                similarity = _compute_cosine_similarity(query_embedding, workflow_embedding)

                if similarity >= request.min_similarity:
                    results.append(WorkflowSearchResult(
                        workflow_id=workflow.get("id", ""),
                        workflow_name=workflow.get("name", "Unnamed Workflow"),
                        description=workflow.get("description"),
                        created_at=workflow.get("created_at", ""),
                        similarity_score=round(similarity, 4)
                    ))

        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit results
        results = results[:request.limit]

        logger.info(f"✅ Found {len(results)} similar workflows")

        return WorkflowSemanticSearchResponse(
            results=results,
            query=request.query,
            total_results=len(results)
        )

    except Exception as e:
        logger.error(f"❌ Workflow semantic search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow semantic search failed: {str(e)}")


# MARK: - Helper Functions for Semantic Search

async def _embed_query_workflow(text: str) -> Optional[List[float]]:
    """Generate embedding for workflow text using ANE Context Engine"""
    try:
        from api.ane_context_engine import _embed_with_ane
        embedding = _embed_with_ane(text)
        return embedding
    except Exception as e:
        logger.warning(f"⚠️ Embedding failed: {e}")
        return None


async def _get_user_workflows(user_id: str) -> List[Dict[str, Any]]:
    """Get workflows for user"""
    try:
        from api.workflow_service import WorkflowService
        workflow_service = WorkflowService()

        # Get workflows from service
        workflows = workflow_service.list_workflows(user_id=user_id)
        return workflows

    except Exception as e:
        logger.warning(f"⚠️ Failed to get workflows: {e}")
        return []


def _compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)
