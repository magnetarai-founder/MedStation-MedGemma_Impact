"""
Chat Analytics Operations

Handles analytics, semantic search, and session statistics.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def semantic_search(query: str, limit: int, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Search across conversations using semantic similarity

    Args:
        query: Search query text
        limit: Maximum number of results
        user_id: User ID for scoping
        team_id: Optional team ID for team-scoped search

    Returns:
        Dictionary with query, results, count, and team_id
    """
    # Import here to avoid circular dependency
    from .core import _get_memory

    memory = _get_memory()

    results = await asyncio.to_thread(
        memory.search_messages_semantic,
        query,
        limit,
        user_id=user_id,
        team_id=team_id
    )

    return {
        "query": query,
        "results": results,
        "count": len(results),
        "team_id": team_id
    }


async def get_analytics(session_id: Optional[str], user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get analytics for a session or scoped analytics

    Args:
        session_id: Optional specific session ID
        user_id: User ID for scoping
        team_id: Optional team ID for team-scoped analytics

    Returns:
        Analytics dictionary from memory system
    """
    # Import here to avoid circular dependency
    from .core import _get_memory

    memory = _get_memory()

    analytics = await asyncio.to_thread(
        memory.get_analytics,
        session_id,
        user_id=user_id,
        team_id=team_id
    )

    return analytics


async def get_session_analytics(chat_id: str) -> Dict[str, Any]:
    """
    Get detailed analytics for a specific session

    Args:
        chat_id: Session/chat ID

    Returns:
        Dictionary with stats and topics for the session
    """
    from api.chat_enhancements import ConversationAnalytics
    from .core import get_messages

    messages = await get_messages(chat_id)

    stats = await asyncio.to_thread(
        ConversationAnalytics.calculate_session_stats,
        messages
    )

    topics = await asyncio.to_thread(
        ConversationAnalytics.get_conversation_topics,
        messages
    )

    return {
        "stats": stats,
        "topics": topics
    }
