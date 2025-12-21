"""
Chat Service Storage Layer

All database operations for chat sessions, messages, and documents.
Wraps NeutronChatMemory for consistent access pattern.

Phase 2.3a - Foundation module following Team service pattern.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Lazy-loaded memory instance
_memory = None


def _get_memory() -> Any:
    """Lazy initialization of chat memory"""
    global _memory
    if _memory is None:
        from api.chat_memory import NeutronChatMemory
        _memory = NeutronChatMemory()
    return _memory


# ============================================================================
# SESSION OPERATIONS
# ============================================================================

async def create_session(
    chat_id: str,
    title: str,
    model: str,
    user_id: str,
    team_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new chat session

    Args:
        chat_id: Unique session identifier
        title: Session title
        model: Model name
        user_id: User ID
        team_id: Optional team ID

    Returns:
        Session data dict
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.create_session,
        chat_id,
        title,
        model,
        user_id,
        team_id
    )


async def get_session(
    chat_id: str,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    team_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get session by ID

    Args:
        chat_id: Session ID
        user_id: Optional user ID for permission check
        role: Optional user role
        team_id: Optional team ID

    Returns:
        Session data dict or None
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.get_session,
        chat_id,
        user_id,
        role,
        team_id
    )


async def list_sessions(
    user_id: str,
    role: Optional[str] = None,
    team_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List sessions for a user

    Args:
        user_id: User ID
        role: Optional user role
        team_id: Optional team ID

    Returns:
        List of session dicts
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.list_sessions,
        user_id,
        role,
        team_id
    )


async def delete_session(
    chat_id: str,
    user_id: str,
    role: Optional[str] = None
) -> bool:
    """
    Delete a session

    Args:
        chat_id: Session ID
        user_id: User ID
        role: Optional user role

    Returns:
        True if deleted successfully
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.delete_session,
        chat_id,
        user_id,
        role
    )


async def update_session_model(
    chat_id: str,
    model: str
) -> None:
    """
    Update session model

    Args:
        chat_id: Session ID
        model: New model name
    """
    memory = _get_memory()
    await asyncio.to_thread(
        memory.update_session_model,
        chat_id,
        model
    )


async def update_session_title(
    chat_id: str,
    title: str,
    auto_titled: bool = False
) -> None:
    """
    Update session title

    Args:
        chat_id: Session ID
        title: New title
        auto_titled: Whether this was auto-generated
    """
    memory = _get_memory()
    await asyncio.to_thread(
        memory.update_session_title,
        chat_id,
        title,
        auto_titled
    )


async def set_session_archived(
    chat_id: str,
    archived: bool
) -> None:
    """
    Archive or unarchive a session

    Args:
        chat_id: Session ID
        archived: Archive status
    """
    memory = _get_memory()
    # Note: This will need to be implemented in chat_memory.py
    # For now, we'll update via get_session + manual update
    session = await get_session(chat_id)
    if session:
        session['archived'] = archived
        # The memory implementation should handle this
        # For now, this is a placeholder


# ============================================================================
# MESSAGE OPERATIONS
# ============================================================================

async def add_message(
    chat_id: str,
    event: Any  # ConversationEvent from chat_memory
) -> None:
    """
    Add a message to session history

    Args:
        chat_id: Session ID
        event: ConversationEvent object
    """
    memory = _get_memory()
    await asyncio.to_thread(
        memory.add_message,
        chat_id,
        event
    )


async def update_summary(
    chat_id: str
) -> None:
    """
    Update session summary

    Args:
        chat_id: Session ID
    """
    memory = _get_memory()
    await asyncio.to_thread(
        memory.update_summary,
        chat_id
    )


async def get_messages(
    chat_id: str,
    limit: Optional[int] = None
) -> List[Any]:
    """
    Get messages for a session

    Args:
        chat_id: Session ID
        limit: Optional limit on number of messages

    Returns:
        List of ConversationEvent objects
    """
    memory = _get_memory()
    if limit:
        return await asyncio.to_thread(
            memory.get_recent_messages,
            chat_id,
            limit
        )
    else:
        return await asyncio.to_thread(
            memory.get_messages,
            chat_id
        )


async def get_summary(
    chat_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get session summary

    Args:
        chat_id: Session ID

    Returns:
        Summary data dict or None
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.get_summary,
        chat_id
    )


# ============================================================================
# DOCUMENT OPERATIONS
# ============================================================================

async def has_documents(
    chat_id: str
) -> bool:
    """
    Check if session has attached documents

    Args:
        chat_id: Session ID

    Returns:
        True if session has documents
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.has_documents,
        chat_id
    )


async def store_document_chunks(
    chat_id: str,
    chunks: List[Dict[str, Any]]
) -> None:
    """
    Store document chunks for RAG

    Args:
        chat_id: Session ID
        chunks: List of document chunk dicts
    """
    memory = _get_memory()
    await asyncio.to_thread(
        memory.store_document_chunks,
        chat_id,
        chunks
    )


def search_document_chunks(
    chat_id: str,
    embedding: List[float],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Search document chunks by embedding (synchronous for RAG)

    Args:
        chat_id: Session ID
        embedding: Query embedding vector
        top_k: Number of results

    Returns:
        List of matching chunk dicts
    """
    memory = _get_memory()
    return memory.search_document_chunks(
        chat_id,
        embedding,
        top_k
    )


# ============================================================================
# SEARCH & ANALYTICS
# ============================================================================

async def search_messages_semantic(
    query: str,
    limit: int,
    user_id: str,
    team_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Semantic search across messages

    Args:
        query: Search query
        limit: Max results
        user_id: User ID for permission filtering
        team_id: Optional team ID

    Returns:
        List of matching message dicts
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.search_messages_semantic,
        query,
        limit,
        user_id,
        team_id
    )


async def get_analytics(
    session_id: Optional[str],
    user_id: str,
    team_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get analytics data

    Args:
        session_id: Optional session ID (None for global analytics)
        user_id: User ID
        team_id: Optional team ID

    Returns:
        Analytics data dict
    """
    memory = _get_memory()
    return await asyncio.to_thread(
        memory.get_analytics,
        session_id,
        user_id,
        team_id
    )
