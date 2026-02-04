"""
Context API for MagnetarCode

Provides endpoints for intelligent context indexing and retrieval.

Endpoints:
  POST /api/v1/context/index/workspace    - Index workspace files
  POST /api/v1/context/index/terminal     - Index terminal output
  GET  /api/v1/context/search              - Search for context
  GET  /api/v1/context/stats               - Get indexing statistics
  DELETE /api/v1/context/clear             - Clear index
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .services.context_engine import get_context_engine

router = APIRouter(prefix="/api/v1/context", tags=["Context"])

# ===== Models =====


class IndexWorkspaceRequest(BaseModel):
    """Request to index a workspace"""

    workspace_path: str = Field(..., description="Path to workspace root")
    force_reindex: bool = Field(False, description="Force re-indexing")


class IndexWorkspaceResponse(BaseModel):
    """Response from workspace indexing"""

    success: bool
    workspace_path: str
    files_indexed: int
    message: str


class SearchRequest(BaseModel):
    """Request to search context"""

    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    source_filter: str | None = Field(None, description="Source filter (file:, terminal:)")
    use_hybrid: bool = Field(True, description="Use hybrid search (semantic + keyword)")


class SearchResult(BaseModel):
    """Search result"""

    id: str
    source: str
    content: str
    score: float
    search_method: str | None = None
    metadata: dict[str, Any] | None = None


# ===== Endpoints =====


@router.post("/index/workspace", response_model=IndexWorkspaceResponse)
async def index_workspace(request: IndexWorkspaceRequest) -> IndexWorkspaceResponse:
    """
    Index all files in a workspace for context retrieval.

    Indexes files using:
    - Vector embeddings for semantic search
    - Full-text search for keyword matching

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/context/index/workspace \
      -H "Content-Type: application/json" \
      -d '{"workspace_path": "/path/to/project"}'
    ```
    """
    try:
        engine = get_context_engine()

        # Index workspace
        result = await engine.index_workspace(
            workspace_path=request.workspace_path, show_progress=True
        )

        return IndexWorkspaceResponse(
            success=True,
            workspace_path=result["workspace_path"],
            files_indexed=result["files_indexed"],
            message=f"Indexed {result['files_indexed']} files",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e!s}")


@router.post("/index/terminal")
async def index_terminal(
    session_id: str = Query(default="main", description="Terminal session ID"),
    lines: int = Query(default=100, ge=1, le=500, description="Number of lines to index"),
) -> dict[str, bool | str | int]:
    """
    Index terminal output for context retrieval.

    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/v1/context/index/terminal?session_id=main&lines=100"
    ```
    """
    try:
        engine = get_context_engine()

        doc_id = await engine.index_terminal(session_id=session_id, lines=lines)

        if doc_id:
            return {
                "success": True,
                "session_id": session_id,
                "document_id": doc_id,
                "message": f"Indexed {lines} lines from terminal session",
            }
        else:
            return {
                "success": False,
                "session_id": session_id,
                "message": "No terminal output to index",
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e!s}")


@router.post("/search", response_model=list[SearchResult])
async def search_context(request: SearchRequest) -> list[SearchResult]:
    """
    Search for relevant context using hybrid retrieval.

    Combines:
    - Semantic search (vector embeddings)
    - Keyword search (full-text)

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/context/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "How do I handle authentication?",
        "top_k": 5,
        "use_hybrid": true
      }'
    ```
    """
    try:
        engine = get_context_engine()

        results = engine.search(
            query=request.query,
            top_k=request.top_k,
            source_filter=request.source_filter,
            use_hybrid=request.use_hybrid,
        )

        return [SearchResult(**r) for r in results]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """
    Get context indexing statistics.

    Returns counts of indexed documents by source type.
    """
    try:
        engine = get_context_engine()
        stats = engine.get_stats()

        return {"status": "healthy", **stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e!s}")


@router.delete("/clear")
async def clear_index(
    source_type: str | None = Query(
        None, description="Source type to clear (file, terminal, or all)"
    ),
) -> dict[str, bool | str | int]:
    """
    Clear context index.

    **Example:**
    ```bash
    # Clear workspace index
    curl -X DELETE "http://localhost:8001/api/v1/context/clear?source_type=file"

    # Clear terminal index
    curl -X DELETE "http://localhost:8001/api/v1/context/clear?source_type=terminal"

    # Clear all
    curl -X DELETE "http://localhost:8001/api/v1/context/clear"
    ```
    """
    try:
        engine = get_context_engine()

        if source_type == "file":
            engine.clear_workspace()
            message = "Cleared workspace index"
        elif source_type == "terminal":
            engine.clear_terminal()
            message = "Cleared terminal index"
        else:
            engine.clear_workspace()
            engine.clear_terminal()
            message = "Cleared all indexes"

        return {"success": True, "message": message}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear failed: {e!s}")


@router.get("/health")
async def context_health() -> dict[str, str | bool | int]:
    """Health check for context engine"""
    try:
        engine = get_context_engine()
        stats = engine.get_stats()

        return {
            "status": "healthy",
            "indexed_documents": stats["total_documents"],
            "db_path": stats["db_path"],
        }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
