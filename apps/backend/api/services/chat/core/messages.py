"""
Chat service - Message operations.

Handles message appending, retrieval, and streaming chat responses with:
- Adaptive routing (ANE/GPU)
- Metal4 acceleration
- RAG with document context
- Conversation summarization
- Analytics tracking
- Search indexing
"""

import json
import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, UTC

from .lazy_init import (
    _get_memory,
    _get_ane_engine,
    _get_metal4_engine,
    _get_ollama_client,
    _get_adaptive_router,
    _get_ane_router
)

logger = logging.getLogger(__name__)

# Router mode: 'adaptive' (GPU, learns) or 'ane' (ultra-low power)
current_router_mode = 'ane'  # Default to ANE for battery life


async def append_message(chat_id: str, role: str, content: str, timestamp: str, model: Optional[str] = None, tokens: Optional[int] = None, files: Optional[List[Dict]] = None) -> None:
    """Append a message to chat history"""
    # Import sessions module for delegation
    from .. import sessions as sessions_mod

    # Save message via sessions module
    await sessions_mod.save_message_to_session(
        chat_id=chat_id,
        role=role,
        content=content,
        model=model,
        tokens=tokens,
        files=files
    )

    # Index message for search (Sprint 6 Theme B)
    try:
        from api.services.search_indexer import get_search_indexer

        # Get session to find user_id
        session_data = await sessions_mod.get_session_by_id(chat_id, user_id=None)
        if session_data:
            user_id = session_data.get('user_id', 'unknown')

            indexer = get_search_indexer()
            await asyncio.to_thread(
                indexer.add_message_to_index,
                session_id=chat_id,
                role=role,
                content=content,
                timestamp=timestamp,
                user_id=user_id
            )
    except Exception as index_error:
        # Don't fail message append if indexing fails
        logger.warning(f"Failed to index message for search: {index_error}")


async def get_messages(
    chat_id: str,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get chat messages with pagination

    Args:
        chat_id: Chat session ID
        limit: Maximum number of messages (None for all)
        offset: Number of messages to skip

    Returns:
        List of message dictionaries in chronological order
    """
    memory = _get_memory()

    if limit:
        events = await asyncio.to_thread(
            memory.get_recent_messages, chat_id, limit, offset
        )
    else:
        events = await asyncio.to_thread(memory.get_messages, chat_id)

    messages = []
    for event in events:
        messages.append({
            "role": event.role,
            "content": event.content,
            "timestamp": event.timestamp,
            "files": event.files or [],
            "model": event.model,
            "tokens": event.tokens
        })

    return messages


async def count_messages(chat_id: str) -> int:
    """Count total messages in a session"""
    memory = _get_memory()
    return await asyncio.to_thread(memory.count_messages, chat_id)


async def send_message_stream(
    chat_id: str,
    content: str,
    user_id: str,
    role: str,
    team_id: Optional[str],
    model: Optional[str] = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 40,
    repeat_penalty: float = 1.1,
    system_prompt: Optional[str] = None,
    use_recursive: bool = True
) -> AsyncGenerator[str, None]:
    """
    Send a message and get streaming response

    This is the core chat logic with Metal4, ANE, adaptive routing, etc.
    """
    from api.chat_enhancements import ChatTitleGenerator, SimpleEmbedding, DocumentChunker
    try:
        from api.utils import sanitize_for_log
    except ImportError:
        from utils import sanitize_for_log

    # Import sessions module for delegation
    from .. import sessions as sessions_mod

    memory = _get_memory()
    ane_engine = _get_ane_engine()
    metal4_engine = _get_metal4_engine()
    ollama_client = _get_ollama_client()

    # Auto-generate title from first message (Phase 2.3a - use sessions module)
    await sessions_mod.auto_title_session_if_needed(chat_id, content)

    # Save user message
    timestamp = datetime.now(UTC).isoformat()
    await append_message(chat_id, "user", content, timestamp)

    # Add to unified context for cross-component persistence
    try:
        try:
            from api.unified_context import get_unified_context
        except ImportError:
            from unified_context import get_unified_context

        try:
            from api.workspace_session import get_workspace_session_manager
        except ImportError:
            from workspace_session import get_workspace_session_manager

        unified_ctx = get_unified_context()
        ws_mgr = get_workspace_session_manager()

        workspace_session_id = await asyncio.to_thread(
            ws_mgr.get_or_create_for_chat,
            user_id=user_id,
            chat_id=chat_id
        )

        await asyncio.to_thread(
            unified_ctx.add_entry,
            user_id=user_id,
            session_id=workspace_session_id,
            source='chat',
            entry_type='message',
            content=content,
            metadata={'role': 'user', 'model': model, 'chat_id': chat_id}
        )
    except Exception as e:
        logger.warning(f"Failed to add message to unified context: {e}")

    # ===== ADAPTIVE ROUTING WITH LEARNING =====
    routing_start = asyncio.get_event_loop().time()

    global current_router_mode
    if current_router_mode == 'ane':
        # ANE routing (ultra-low power)
        ane_router = _get_ane_router()
        ane_result = await asyncio.to_thread(
            ane_router.route,
            content
        )
        routing_time = (asyncio.get_event_loop().time() - routing_start) * 1000

        logger.info(f"🧠 ANE routing: {ane_result.target.value} ({ane_result.confidence:.0%}) - {routing_time:.1f}ms [<0.1W]")
        logger.debug(f"   Reasoning: {ane_result.reasoning}")

        # Convert ANE result to adaptive router format
        from api.adaptive_router import ToolType, TaskType, AdaptiveRouteResult

        ane_to_tool = {
            'ollama_chat': ToolType.OLLAMA,
            'p2p_message': ToolType.P2P,
            'data_query': ToolType.DATA,
            'system_cmd': ToolType.SYSTEM,
        }

        route_result = AdaptiveRouteResult(
            task_type=TaskType.CHAT,
            tool_type=ane_to_tool.get(ane_result.target.value, ToolType.OLLAMA),
            confidence=ane_result.confidence,
            matched_patterns=[],
            reasoning=ane_result.reasoning,
            fallback_options=[],
            recommendations=[],
            adjusted_confidence=ane_result.confidence,
            learning_insights={},
            context=ane_result.metadata
        )
    else:
        # Adaptive routing (GPU, learns)
        adaptive_router = _get_adaptive_router()
        route_result = await asyncio.to_thread(
            adaptive_router.route_task,
            content
        )
        routing_time = (asyncio.get_event_loop().time() - routing_start) * 1000

        logger.info(f"🧠 Adaptive routing: {route_result.tool_type.value} ({route_result.confidence:.0%}) - {routing_time:.1f}ms")
        if route_result.reasoning:
            logger.debug(f"   Reasoning: {route_result.reasoning}")
        if route_result.recommendations:
            logger.debug(f"   Recommendations: {len(route_result.recommendations)}")

    # Use routing suggestion if confidence is high enough
    if route_result.confidence > 0.6 and hasattr(route_result, 'model_name') and route_result.model_name:
        model = route_result.model_name
        logger.info(f"   Using routed model: {model}")

    # ===== RECURSIVE PROMPT PROCESSING =====
    use_recursive = use_recursive and len(content.split()) > 10
    if use_recursive:
        logger.info("🔄 Using recursive prompt decomposition for complex query")

    # Get conversation history
    all_history = await get_messages(chat_id, limit=None)
    CONTEXT_WINDOW = 75

    if len(all_history) > CONTEXT_WINDOW:
        history = all_history[-CONTEXT_WINDOW:]
        summary_data = await asyncio.to_thread(memory.get_summary, chat_id)
        earlier_summary = summary_data['summary'] if summary_data else None
    else:
        history = all_history
        earlier_summary = None

    # ===== METAL 4 TICK FLOW (OPTIMIZED) =====
    relevant_chunks = None
    has_documents = await asyncio.to_thread(memory.has_documents, chat_id)

    if has_documents:
        metal4_engine.kick_frame()

        # Try to use Metal GPU embedder
        try:
            from metal_embedder import get_metal_embedder
            metal_embedder = get_metal_embedder()

            if metal_embedder.is_available():
                embedder = lambda text: metal_embedder.embed(text)
                logger.debug("✓ Using Metal GPU embedder")
            else:
                embedder = lambda text: SimpleEmbedding.create_embedding(text)
                logger.debug("✓ Using CPU embedder (Metal GPU not available)")
        except ImportError:
            embedder = lambda text: SimpleEmbedding.create_embedding(text)
            logger.debug("✓ Using CPU embedder (metal_embedder not installed)")

        rag_retriever = lambda embedding: memory.search_document_chunks(chat_id, embedding, top_k=3)

        metal_result = await asyncio.to_thread(
            metal4_engine.process_chat_message,
            content,
            embedder=embedder,
            rag_retriever=rag_retriever
        )

        relevant_chunks = metal_result.get('context') if metal_result else None

        if metal_result and 'elapsed_ms' in metal_result:
            logger.debug(f"⚡ Metal4 embedding+RAG: {metal_result['elapsed_ms']:.2f}ms")

    # Add relevant document context
    rag_context = ""
    if relevant_chunks:
        rag_context = "\n\n📎 Relevant document context:\n"
        for i, chunk in enumerate(relevant_chunks, 1):
            rag_context += f"\n[{chunk['filename']}, chunk {chunk['chunk_index'] + 1}]:\n{chunk['content'][:300]}...\n"
        logger.info(f"Added {len(relevant_chunks)} document chunks to context")

    # Format for Ollama
    ollama_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
    ]

    if system_prompt:
        ollama_messages.insert(0, {"role": "system", "content": system_prompt})

    if earlier_summary:
        summary_message = {
            "role": "system",
            "content": f"📋 Summary of earlier conversation:\n\n{earlier_summary}\n\n---\nThe following messages are the recent conversation:"
        }
        insert_pos = 1 if system_prompt else 0
        ollama_messages.insert(insert_pos, summary_message)
        logger.info(f"Added conversation summary for {len(all_history) - CONTEXT_WINDOW} earlier messages")

    if rag_context and ollama_messages:
        for i in range(len(ollama_messages) - 1, -1, -1):
            if ollama_messages[i]["role"] == "user":
                ollama_messages[i]["content"] = ollama_messages[i]["content"] + rag_context
                break

    # Stream response
    full_response = ""
    start_time = datetime.now(UTC)  # Track start time for analytics

    try:
        # Send SSE header
        yield "data: [START]\n\n"

        async for chunk in ollama_client.chat(
            model,
            ollama_messages,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty
        ):
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        # Save assistant message
        assistant_timestamp = datetime.now(UTC).isoformat()
        await append_message(
            chat_id,
            "assistant",
            full_response,
            assistant_timestamp,
            model=model,
            tokens=len(full_response.split())
        )

        # Preserve context with ANE
        context_data = {
            "user_message": content,
            "assistant_response": full_response,
            "model": model,
            "timestamp": assistant_timestamp
        }
        await asyncio.to_thread(
            ane_engine.preserve_context,
            chat_id,
            context_data,
            {"model": model, "tokens": len(full_response.split())}
        )

        # Record analytics event (Sprint 6 Theme A)
        try:
            from api.services.analytics import get_analytics_service
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            tokens = len(full_response.split())  # Rough token estimate

            analytics = get_analytics_service()
            await asyncio.to_thread(
                analytics.record_event,
                user_id=user_id,
                event_type="message.sent",
                session_id=chat_id,
                team_id=team_id,
                model_name=model,
                tokens_used=tokens,
                duration_ms=duration_ms,
                metadata={"temperature": temperature, "top_p": top_p}
            )

            # Record latency separately for model performance tracking (Sprint 6 Theme C)
            await asyncio.to_thread(
                analytics.record_event,
                user_id=user_id,
                event_type="assistant_latency",
                session_id=chat_id,
                team_id=team_id,
                model_name=model,
                duration_ms=duration_ms,
                metadata={
                    "latency_ms": duration_ms,
                    "tokens": tokens,
                    "temperature": temperature
                }
            )
        except Exception as analytics_error:
            # Don't fail the request if analytics fails
            logger.warning(f"Failed to record analytics: {analytics_error}")

        # Send done event with message ID for feedback
        message_id = f"{chat_id}:{assistant_timestamp}"
        yield f"data: {json.dumps({'done': True, 'message_id': message_id})}\n\n"

    except Exception as e:
        logger.error(f"Error in message streaming: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
