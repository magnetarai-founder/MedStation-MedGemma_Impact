"""
Chat System & Monitoring Operations

Handles system health, ANE stats, embeddings, token counting,
Ollama server status, and router management.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ========================================================================
# ANE CONTEXT
# ========================================================================

async def get_ane_stats() -> Dict[str, Any]:
    """
    Get Apple Neural Engine context stats

    Returns:
        Dictionary with ANE statistics
    """
    from .core import _get_ane_engine

    ane_engine = _get_ane_engine()
    stats = await asyncio.to_thread(ane_engine.stats)
    return stats


async def search_ane_context(query: str, top_k: int = 5, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Search for similar chat contexts using ANE-accelerated embeddings

    Args:
        query: Search query text
        top_k: Number of top results to return
        threshold: Similarity threshold (0-1)

    Returns:
        Dictionary with query, results, and count
    """
    from .core import _get_ane_engine

    ane_engine = _get_ane_engine()

    results = await asyncio.to_thread(
        ane_engine.search_similar,
        query,
        top_k,
        threshold
    )

    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


# ========================================================================
# EMBEDDING INFO
# ========================================================================

async def get_embedding_info() -> Dict[str, Any]:
    """
    Get information about the embedding backend

    Returns:
        Dictionary with backend information or error details
    """
    try:
        from api.unified_embedder import get_backend_info
        info = await asyncio.to_thread(get_backend_info)
        return info
    except Exception as e:
        logger.error(f"Failed to get embedding info: {e}")
        return {
            "error": str(e),
            "backend": "unknown"
        }


# ========================================================================
# TOKEN COUNTING
# ========================================================================

async def get_token_count(chat_id: str) -> Dict[str, Any]:
    """
    Get token count for a chat session

    Args:
        chat_id: Session/chat ID

    Returns:
        Dictionary with total_tokens, max_tokens, and percentage
    """
    from .core import _get_token_counter, get_messages

    token_counter = _get_token_counter()
    messages = await get_messages(chat_id, limit=None)

    message_list = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]

    total_tokens = await asyncio.to_thread(
        token_counter.count_message_tokens,
        message_list
    )

    return {
        "chat_id": chat_id,
        "total_tokens": total_tokens,
        "max_tokens": 200000,
        "percentage": round((total_tokens / 200000) * 100, 2)
    }


# ========================================================================
# HEALTH & STATUS
# ========================================================================

async def check_health() -> Dict[str, Any]:
    """
    Check Ollama health status

    Returns:
        Health check dictionary from ErrorHandler
    """
    try:
        from api.error_handler import ErrorHandler
    except ImportError:
        from error_handler import ErrorHandler
    return await ErrorHandler.check_ollama_health()


async def get_ollama_server_status() -> Dict[str, Any]:
    """
    Check if Ollama server is running

    Returns:
        Dictionary with running status, loaded_models list, and model_count
    """
    # Delegate to ollama_ops module (Phase 2.3c)
    from . import ollama_ops
    return await ollama_ops.get_ollama_server_status()


# ========================================================================
# ROUTER FEEDBACK & STATS
# ========================================================================

async def submit_router_feedback(
    command: str,
    tool_used: str,
    success: bool,
    execution_time: float,
    user_satisfaction: Optional[int] = None
):
    """
    Submit feedback for adaptive router to learn from

    Args:
        command: User command that was routed
        tool_used: Tool that was selected
        success: Whether execution was successful
        execution_time: Execution time in seconds
        user_satisfaction: Optional user satisfaction rating

    Returns:
        Status dictionary
    """
    from .core import _get_adaptive_router

    adaptive_router = _get_adaptive_router()

    await asyncio.to_thread(
        adaptive_router.record_execution_result,
        command,
        tool_used,
        success,
        execution_time
    )

    logger.info(f"📊 Router feedback: {command[:50]}... → {tool_used} ({'✓' if success else '✗'})")

    return {
        "status": "recorded",
        "message": "Feedback recorded successfully"
    }


async def get_router_stats() -> Dict[str, Any]:
    """
    Get adaptive router statistics

    Returns:
        Dictionary with routing, learning, memory stats, top patterns, and preferences
    """
    from .core import _get_adaptive_router

    adaptive_router = _get_adaptive_router()

    try:
        from api.learning_system import LearningSystem
        from api.jarvis_memory import JarvisMemory

        jarvis_memory = JarvisMemory()
        learning_system = LearningSystem(memory=jarvis_memory)
    except ImportError:
        from learning_system import LearningSystem
        from jarvis_memory import JarvisMemory

        jarvis_memory = JarvisMemory()
        learning_system = LearningSystem(memory=jarvis_memory)

    routing_stats = adaptive_router.get_routing_stats() if hasattr(adaptive_router, 'get_routing_stats') else {}
    learning_stats = await asyncio.to_thread(learning_system.get_statistics)
    memory_stats = await asyncio.to_thread(jarvis_memory.get_statistics)
    learned_patterns = await asyncio.to_thread(learning_system.get_learned_patterns) if hasattr(learning_system, 'get_learned_patterns') else []
    preferences = await asyncio.to_thread(learning_system.get_preferences)

    return {
        "routing": routing_stats,
        "learning": learning_stats,
        "memory": memory_stats,
        "top_patterns": learned_patterns[:10],
        "preferences": [
            {
                "category": p.category,
                "preference": p.preference,
                "confidence": p.confidence,
                "evidence_count": p.evidence_count
            }
            for p in preferences[:10]
        ]
    }


async def explain_routing(command: str) -> Dict[str, Any]:
    """
    Explain how a command would be routed

    Args:
        command: User command to analyze

    Returns:
        Explanation dictionary with routing decision details
    """
    from .core import _get_adaptive_router

    adaptive_router = _get_adaptive_router()

    explanation = await asyncio.to_thread(
        adaptive_router.explain_routing if hasattr(adaptive_router, 'explain_routing') else adaptive_router.route_task,
        command
    )

    if isinstance(explanation, str):
        return {"explanation": explanation}
    else:
        return {
            "task_type": explanation.task_type.value,
            "tool_type": explanation.tool_type.value,
            "confidence": explanation.confidence,
            "reasoning": explanation.reasoning,
            "learning_insights": explanation.learning_insights if hasattr(explanation, 'learning_insights') else {}
        }


# ========================================================================
# ROUTER MODE
# ========================================================================

# Module-level variable for router mode (mirroring core.py)
_current_router_mode = 'adaptive'


def get_router_mode() -> Dict[str, Any]:
    """
    Get current router mode

    Returns:
        Dictionary with mode, description, and power_estimate
    """
    # Import to access the global variable from core.py
    from .core import current_router_mode

    return {
        "mode": current_router_mode,
        "description": "adaptive (GPU, learns)" if current_router_mode == 'adaptive' else "ane (ultra-low power <0.1W)",
        "power_estimate": "5-10W" if current_router_mode == 'adaptive' else "<0.1W"
    }


def set_router_mode(mode: str) -> Dict[str, Any]:
    """
    Set router mode

    Args:
        mode: Router mode ('adaptive' or 'ane')

    Returns:
        Dictionary with mode details and confirmation message

    Raises:
        ValueError: If mode is invalid
    """
    # Import to modify the global variable in core.py
    import api.services.chat.core as core_module

    if mode not in ['adaptive', 'ane']:
        raise ValueError("Mode must be 'adaptive' or 'ane'")

    core_module.current_router_mode = mode
    logger.info(f"🔄 Router mode changed to: {mode}")

    return {
        "mode": mode,
        "description": "adaptive (GPU, learns)" if mode == 'adaptive' else "ane (ultra-low power <0.1W)",
        "power_estimate": "5-10W" if mode == 'adaptive' else "<0.1W",
        "message": f"Router mode set to {mode}"
    }
