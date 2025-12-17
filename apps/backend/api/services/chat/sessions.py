"""
Chat Service Session Management

Handles session lifecycle and context assembly for chat requests.
Orchestrates session creation, retrieval, and context preparation.

Phase 2.3a - Session orchestration following Team service pattern.
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC

from . import storage
from .types import SessionDict, MessageDict

logger = logging.getLogger(__name__)


# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

async def create_new_session(
    title: str,
    model: str,
    user_id: str,
    team_id: Optional[str] = None
) -> SessionDict:
    """
    Create a new chat session

    Args:
        title: Session title
        model: Default model for session
        user_id: User ID
        team_id: Optional team ID for team sessions

    Returns:
        Created session dict
    """
    # Generate unique session ID
    chat_id = f"chat_{uuid.uuid4().hex[:16]}"

    # Create session in DB
    session = await storage.create_session(
        chat_id=chat_id,
        title=title,
        model=model,
        user_id=user_id,
        team_id=team_id
    )

    logger.info(f"Created new session {chat_id} for user {user_id}" +
                (f" in team {team_id}" if team_id else ""))

    return session


async def get_session_by_id(
    chat_id: str,
    user_id: str,
    role: Optional[str] = None,
    team_id: Optional[str] = None
) -> Optional[SessionDict]:
    """
    Get session by ID with access control

    Args:
        chat_id: Session ID
        user_id: User ID requesting access
        role: User role (for god_rights bypass)
        team_id: Team ID (for team session access)

    Returns:
        Session dict or None if not found/no access
    """
    session = await storage.get_session(
        chat_id=chat_id,
        user_id=user_id,
        role=role,
        team_id=team_id
    )

    return session


async def list_user_sessions(
    user_id: str,
    role: Optional[str] = None,
    team_id: Optional[str] = None
) -> List[SessionDict]:
    """
    List sessions for a user

    Args:
        user_id: User ID
        role: User role
        team_id: Optional team ID filter

    Returns:
        List of session dicts
    """
    sessions = await storage.list_sessions(
        user_id=user_id,
        role=role,
        team_id=team_id
    )

    return sessions


async def delete_session_by_id(
    chat_id: str,
    user_id: str,
    role: Optional[str] = None
) -> bool:
    """
    Delete a session (with access control)

    Args:
        chat_id: Session ID
        user_id: User ID requesting deletion
        role: User role (for god_rights bypass)

    Returns:
        True if deleted successfully
    """
    success = await storage.delete_session(
        chat_id=chat_id,
        user_id=user_id,
        role=role
    )

    if success:
        logger.info(f"Deleted session {chat_id} by user {user_id}")
    else:
        logger.warning(f"Failed to delete session {chat_id} - access denied or not found")

    return success


async def update_session_metadata(
    chat_id: str,
    title: Optional[str] = None,
    model: Optional[str] = None,
    archived: Optional[bool] = None
) -> SessionDict:
    """
    Update session metadata

    Args:
        chat_id: Session ID
        title: New title (optional)
        model: New model (optional)
        archived: Archive status (optional)

    Returns:
        Updated session dict
    """
    if title is not None:
        await storage.update_session_title(chat_id, title, auto_titled=False)

    if model is not None:
        await storage.update_session_model(chat_id, model)

    if archived is not None:
        await storage.set_session_archived(chat_id, archived)

    # Return updated session
    session = await storage.get_session(chat_id)
    return session


# ============================================================================
# CONTEXT ASSEMBLY
# ============================================================================

async def get_conversation_context(
    chat_id: str,
    max_messages: int = 75,
    include_summary: bool = True
) -> Dict[str, Any]:
    """
    Assemble conversation context for a chat request

    This is the key orchestration function that prepares context
    for sending a message. It handles:
    - Retrieving message history
    - Truncating to context window
    - Including conversation summary if needed

    Args:
        chat_id: Session ID
        max_messages: Maximum messages to include
        include_summary: Whether to include summary if history is long

    Returns:
        Dict with 'messages', 'summary', 'total_count'
    """
    # Get all messages (or recent if limit specified)
    messages = await storage.get_messages(chat_id, limit=None)

    total_count = len(messages)

    # Prepare context
    context = {
        'messages': messages,
        'summary': None,
        'total_count': total_count,
        'truncated': False
    }

    # If history exceeds max_messages, truncate and fetch summary
    if total_count > max_messages:
        # Keep only recent messages
        context['messages'] = messages[-max_messages:]
        context['truncated'] = True

        # Get summary for context
        if include_summary:
            summary_data = await storage.get_summary(chat_id)
            if summary_data:
                context['summary'] = summary_data.get('summary')

    return context


async def save_message_to_session(
    chat_id: str,
    role: str,
    content: str,
    model: Optional[str] = None,
    tokens: Optional[int] = None,
    files: Optional[List[Dict]] = None
) -> None:
    """
    Save a message to session and update metadata

    This handles the full message save flow:
    - Add message to DB
    - Update session metadata
    - Update conversation summary

    Args:
        chat_id: Session ID
        role: Message role (user/assistant/system)
        content: Message content
        model: Model used (for assistant messages)
        tokens: Token count (optional)
        files: Attached files (optional)
    """
    # Create ConversationEvent structure (matches chat_memory expectation)
    from api.chat_memory import ConversationEvent

    timestamp = datetime.now(UTC).isoformat()

    event = ConversationEvent(
        timestamp=timestamp,
        role=role,
        content=content,
        model=model,
        tokens=tokens,
        files=files or []
    )

    # Add message to DB
    await storage.add_message(chat_id, event)

    # Update summary (batched, not on every message)
    await storage.update_summary(chat_id)


async def auto_title_session_if_needed(
    chat_id: str,
    first_user_message: str
) -> None:
    """
    Auto-generate session title from first message if not already titled

    Args:
        chat_id: Session ID
        first_user_message: First user message content
    """
    session = await storage.get_session(chat_id)

    if not session:
        logger.warning(f"Session {chat_id} not found for auto-titling")
        return

    # Only auto-title if this is the first message (message_count would be 1 after first user message)
    message_count = session.get('message_count', 0)

    if message_count <= 1:
        # Generate title from first message (simple heuristic: first 50 chars)
        title = first_user_message[:50].strip()
        if len(first_user_message) > 50:
            title += "..."

        # Update session title
        await storage.update_session_title(chat_id, title, auto_titled=True)

        logger.debug(f"Auto-titled session {chat_id}: {title}")


# ============================================================================
# DOCUMENT CONTEXT (RAG)
# ============================================================================

async def check_session_has_documents(chat_id: str) -> bool:
    """
    Check if session has attached documents for RAG

    Args:
        chat_id: Session ID

    Returns:
        True if session has documents
    """
    return await storage.has_documents(chat_id)


def search_session_documents(
    chat_id: str,
    query_embedding: List[float],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Search document chunks for RAG retrieval (synchronous for performance)

    Args:
        chat_id: Session ID
        query_embedding: Query embedding vector
        top_k: Number of chunks to retrieve

    Returns:
        List of matching document chunks
    """
    return storage.search_document_chunks(
        chat_id=chat_id,
        embedding=query_embedding,
        top_k=top_k
    )


async def store_uploaded_documents(
    chat_id: str,
    chunks: List[Dict[str, Any]]
) -> None:
    """
    Store document chunks for RAG

    Args:
        chat_id: Session ID
        chunks: List of document chunk dicts
    """
    await storage.store_document_chunks(chat_id, chunks)

    logger.info(f"Stored {len(chunks)} document chunks for session {chat_id}")
