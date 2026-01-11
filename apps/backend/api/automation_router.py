"""
Automation Workflow Router
Handles workflow execution and management

Module structure (P2 decomposition):
- automation_types.py: Request/response models
- automation_router.py: API endpoints (this file)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from api.auth_middleware import get_current_user
from api.utils import sanitize_for_log

# Import from extracted module (P2 decomposition)
from api.automation_types import (
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

logger = logging.getLogger(__name__)

try:
    from .automation_storage import get_automation_storage
except ImportError:
    from automation_storage import get_automation_storage

router = APIRouter(
    prefix="/api/v1/automation",
    tags=["automation"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: Request,
    body: WorkflowRunRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Execute a workflow and record execution history

    This executes workflow steps and records results to SQLite.
    """
    start_time = datetime.now()
    user_id = current_user.get("user_id", "anonymous")

    # Sanitize workflow name for logging
    safe_name = sanitize_for_log(body.name)
    safe_id = sanitize_for_log(body.workflow_id)
    logger.info(f"🚀 Running workflow: {safe_name} (ID: {safe_id}) for user {user_id}")
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

    # Record execution in storage
    try:
        storage = get_automation_storage()
        storage.record_execution(
            workflow_id=body.workflow_id,
            user_id=user_id,
            status="completed",
            steps_executed=steps_executed,
            execution_time_ms=execution_time,
            results=results
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to record execution: {e}")

    return WorkflowRunResponse(
        status="success",
        workflow_id=body.workflow_id,
        workflow_name=body.name,
        steps_executed=steps_executed,
        execution_time_ms=execution_time,
        results=results
    )


@router.post("/save", response_model=WorkflowSaveResponse)
async def save_workflow(
    request: Request,
    body: WorkflowSaveRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Save workflow configuration to SQLite database
    """
    user_id = current_user.get("user_id", "anonymous")
    safe_name = sanitize_for_log(body.name)
    safe_id = sanitize_for_log(body.workflow_id)
    logger.info(f"💾 Saving workflow: {safe_name} (ID: {safe_id}) for user {user_id}")

    try:
        storage = get_automation_storage()
        # Convert pydantic models to dicts
        nodes = [n.model_dump() if hasattr(n, 'model_dump') else n for n in body.nodes]
        edges = [e.model_dump() if hasattr(e, 'model_dump') else e for e in body.edges]

        result = storage.save_workflow(
            workflow_id=body.workflow_id,
            name=body.name,
            nodes=nodes,
            edges=edges,
            user_id=user_id
        )

        return WorkflowSaveResponse(
            status="saved",
            workflow_id=body.workflow_id,
            saved_at=result["updated_at"]
        )
    except Exception as e:
        logger.error(f"❌ Failed to save workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save workflow: {str(e)}")


@router.get("/workflows")
async def list_workflows(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    active_only: bool = False
) -> Dict[str, Any]:
    """
    List all saved workflows for the current user
    """
    user_id = current_user.get("user_id", "anonymous")

    try:
        storage = get_automation_storage()
        workflows = storage.list_workflows(
            user_id=user_id,
            limit=limit,
            offset=offset,
            active_only=active_only
        )

        return {
            "workflows": workflows,
            "count": len(workflows)
        }
    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get workflow by ID
    """
    user_id = current_user.get("user_id", "anonymous")

    try:
        storage = get_automation_storage()
        workflow = storage.get_workflow(workflow_id=workflow_id, user_id=user_id)

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    request: Request,
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete workflow from database
    """
    user_id = current_user.get("user_id", "anonymous")

    try:
        storage = get_automation_storage()
        deleted = storage.delete_workflow(workflow_id=workflow_id, user_id=user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Workflow not found")

        logger.info(f"🗑️ Deleted workflow {workflow_id} for user {user_id}")
        return {"status": "deleted", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")


@router.get("/workflows/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get execution history for a workflow
    """
    user_id = current_user.get("user_id", "anonymous")

    try:
        storage = get_automation_storage()
        executions = storage.get_execution_history(
            workflow_id=workflow_id,
            user_id=user_id,
            limit=limit
        )

        return {
            "workflow_id": workflow_id,
            "executions": executions,
            "count": len(executions)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get executions: {str(e)}")


# MARK: - Semantic Search


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
    """Get workflows for user from automation storage"""
    try:
        storage = get_automation_storage()
        workflows = storage.list_workflows(user_id=user_id)
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


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Router
    "router",
    # Re-exported from automation_types
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
