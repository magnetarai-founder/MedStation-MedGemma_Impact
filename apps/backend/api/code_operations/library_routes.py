"""
Code Operations - Library Routes

CRUD endpoints for project library documents.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import logging

from api.auth_middleware import get_current_user
from api.errors import http_500
from api.utils import get_user_id
from api.code_operations.models import ProjectLibraryDocument, UpdateDocumentRequest
from api.code_operations import library_db

try:
    from api.audit_logger import log_action
except ImportError:
    async def log_action(**kwargs: Any) -> None:
        pass

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library")
async def get_library_documents(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get all project library documents"""
    try:
        user_id = get_user_id(current_user)
        return library_db.get_documents(user_id)

    except Exception as e:
        logger.error(f"Error getting library documents: {e}")
        raise http_500("Failed to get library documents")


@router.post("/library")
async def create_library_document(
    doc: ProjectLibraryDocument,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create new project library document"""
    try:
        user_id = get_user_id(current_user)

        doc_id = library_db.create_document(
            user_id=user_id,
            name=doc.name,
            content=doc.content,
            tags=doc.tags,
            file_type=doc.file_type
        )

        await log_action(
            user_id=user_id,
            action="code.library.create",
            resource=doc.name,
            details={'id': doc_id, 'tags': doc.tags}
        )

        return {'id': doc_id, 'success': True}

    except Exception as e:
        logger.error(f"Error creating library document: {e}")
        raise http_500("Failed to create library document")


@router.patch("/library/{doc_id}")
async def update_library_document(
    doc_id: int,
    update: UpdateDocumentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, bool]:
    """Update project library document"""
    try:
        user_id = get_user_id(current_user)

        library_db.update_document(
            user_id=user_id,
            doc_id=doc_id,
            name=update.name,
            content=update.content,
            tags=update.tags
        )

        await log_action(
            user_id=user_id,
            action="code.library.update",
            resource=str(doc_id),
            details=update.model_dump(exclude_none=True)
        )

        return {'success': True}

    except Exception as e:
        logger.error(f"Error updating library document: {e}")
        raise http_500("Failed to update library document")


@router.delete("/library/{doc_id}")
async def delete_library_document(
    doc_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, bool]:
    """Delete project library document"""
    try:
        user_id = get_user_id(current_user)

        library_db.delete_document(user_id=user_id, doc_id=doc_id)

        await log_action(
            user_id=user_id,
            action="code.library.delete",
            resource=str(doc_id)
        )

        return {'success': True}

    except Exception as e:
        logger.error(f"Error deleting library document: {e}")
        raise http_500("Failed to delete library document")
