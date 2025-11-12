import json
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

router = APIRouter()

# Import shared elohimos_memory instance from main.py
def get_elohimos_memory():
    from api import main
    return main.elohimos_memory

# Models
class SavedQueryRequest(BaseModel):
    name: str
    query: str
    query_type: str
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

class SavedQueryUpdateRequest(BaseModel):
    name: str | None = None
    query: str | None = None
    query_type: str | None = None
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

@router.post("")
async def save_query(request: Request, body: SavedQueryRequest):
    """Save a query for later use"""
    elohimos_memory = get_elohimos_memory()
    try:
        query_id = elohimos_memory.save_query(
            name=body.name,
            query=body.query,
            query_type=body.query_type,
            folder=body.folder,
            description=body.description,
            tags=body.tags
        )
        return {"id": query_id, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_saved_queries(
    folder: str | None = Query(None),
    query_type: str | None = Query(None)
):
    """Get all saved queries"""
    elohimos_memory = get_elohimos_memory()
    try:
        queries = elohimos_memory.get_saved_queries(
            folder=folder,
            query_type=query_type
        )
        return {"queries": queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{query_id}")
async def update_saved_query(request: Request, query_id: int, body: SavedQueryUpdateRequest):
    """Update a saved query (partial updates supported)"""
    elohimos_memory = get_elohimos_memory()
    try:
        # Get existing query
        all_queries = elohimos_memory.get_saved_queries()
        existing = next((q for q in all_queries if q['id'] == query_id), None)

        if not existing:
            raise HTTPException(status_code=404, detail="Query not found")

        # Merge updates with existing data
        elohimos_memory.update_saved_query(
            query_id=query_id,
            name=body.name if body.name is not None else existing['name'],
            query=body.query if body.query is not None else existing['query'],
            query_type=body.query_type if body.query_type is not None else existing['query_type'],
            folder=body.folder if body.folder is not None else existing.get('folder'),
            description=body.description if body.description is not None else existing.get('description'),
            tags=body.tags if body.tags is not None else (json.loads(existing.get('tags', '[]')) if existing.get('tags') else None)
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{query_id}")
async def delete_saved_query(request: Request, query_id: int):
    """Delete a saved query"""
    elohimos_memory = get_elohimos_memory()
    try:
        elohimos_memory.delete_saved_query(query_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
