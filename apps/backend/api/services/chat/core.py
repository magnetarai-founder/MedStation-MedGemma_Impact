"""
Chat service for ElohimOS - Business logic for chat management.

Thin service layer with lazy imports to avoid circular dependencies.
All heavy dependencies are imported inside function bodies.
"""

import os
import json
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime

# Phase 2.3a - Session/storage delegation
from . import sessions as sessions_mod
# Phase 2.3b - Model/hot-slot delegation
from . import models as models_mod
from . import hot_slots as hot_slots_mod
# Phase 2.3b+ - Analytics and system monitoring delegation
from . import analytics as analytics_mod
from . import system as system_mod
# Phase 2.3c - Ollama server operations delegation
from . import ollama_ops as ollama_ops_mod

logger = logging.getLogger(__name__)


# ===== Global instances (lazy initialization) =====

_memory = None
_ane_engine = None
_token_counter = None
_model_manager = None
_metal4_engine = None
_adaptive_router = None
_ane_router = None
_recursive_library = None
_ollama_config = None
_performance_monitor = None
_panic_mode = None
_ollama_client = None

# Router mode: 'adaptive' (GPU, learns) or 'ane' (ultra-low power)
current_router_mode = 'ane'  # Default to ANE for battery life


def _get_memory():
    """Lazy init for memory"""
    global _memory
    if _memory is None:
        try:
            from api.chat_memory import get_memory
        except ImportError:
            from chat_memory import get_memory
        _memory = get_memory()
    return _memory


def _get_ane_engine():
    """Lazy init for ANE engine"""
    global _ane_engine
    if _ane_engine is None:
        try:
            from api.ane_context_engine import get_ane_engine
        except ImportError:
            from ane_context_engine import get_ane_engine
        _ane_engine = get_ane_engine()
    return _ane_engine


def _get_token_counter():
    """Lazy init for token counter"""
    global _token_counter
    if _token_counter is None:
        try:
            from api.token_counter import TokenCounter
        except ImportError:
            from token_counter import TokenCounter
        _token_counter = TokenCounter()
    return _token_counter


def _get_model_manager():
    """Lazy init for model manager"""
    global _model_manager
    if _model_manager is None:
        try:
            from api.model_manager import get_model_manager
        except ImportError:
            from model_manager import get_model_manager
        _model_manager = get_model_manager()
    return _model_manager


def _get_metal4_engine():
    """Lazy init for Metal4 engine"""
    global _metal4_engine
    if _metal4_engine is None:
        try:
            from api.metal4_engine import get_metal4_engine
        except ImportError:
            from metal4_engine import get_metal4_engine
        _metal4_engine = get_metal4_engine()
    return _metal4_engine


def _get_adaptive_router():
    """Lazy init for adaptive router"""
    global _adaptive_router
    if _adaptive_router is None:
        try:
            from api.adaptive_router import AdaptiveRouter
            from api.jarvis_memory import JarvisMemory
            from api.learning_system import LearningSystem
        except ImportError:
            from adaptive_router import AdaptiveRouter
            from jarvis_memory import JarvisMemory
            from learning_system import LearningSystem

        jarvis_memory = JarvisMemory()
        learning_system = LearningSystem(memory=jarvis_memory)
        _adaptive_router = AdaptiveRouter(memory=jarvis_memory, learning=learning_system)
    return _adaptive_router


def _get_ane_router():
    """Lazy init for ANE router"""
    global _ane_router
    if _ane_router is None:
        try:
            from api.ane_router import get_ane_router
        except ImportError:
            from ane_router import get_ane_router
        _ane_router = get_ane_router()
    return _ane_router


def _get_recursive_library():
    """Lazy init for recursive library"""
    global _recursive_library
    if _recursive_library is None:
        try:
            from api.recursive_prompt_library import get_recursive_library
        except ImportError:
            from recursive_prompt_library import get_recursive_library
        _recursive_library = get_recursive_library()
    return _recursive_library


def _get_ollama_config():
    """Lazy init for Ollama config"""
    global _ollama_config
    if _ollama_config is None:
        try:
            from api.ollama_config import get_ollama_config
        except ImportError:
            from ollama_config import get_ollama_config
        _ollama_config = get_ollama_config()
    return _ollama_config


def _get_performance_monitor():
    """Lazy init for performance monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        try:
            from api.performance_monitor import get_performance_monitor
        except ImportError:
            from performance_monitor import get_performance_monitor
        _performance_monitor = get_performance_monitor()
    return _performance_monitor


def _get_panic_mode():
    """Lazy init for panic mode"""
    global _panic_mode
    if _panic_mode is None:
        try:
            from api.panic_mode import get_panic_mode
        except ImportError:
            from panic_mode import get_panic_mode
        _panic_mode = get_panic_mode()
    return _panic_mode


def _get_ollama_client():
    """Lazy init for Ollama client"""
    global _ollama_client
    if _ollama_client is None:
        from .streaming import OllamaClient
        _ollama_client = OllamaClient()
    return _ollama_client


def _get_chat_uploads_dir():
    """Get chat uploads directory"""
    from config_paths import get_config_paths
    uploads_dir = get_config_paths().uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


# ===== Session Management =====

async def create_session(title: str, model: str, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new chat session"""
    return await sessions_mod.create_new_session(title, model, user_id, team_id)


async def get_session(chat_id: str, user_id: str, role: str = None, team_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get session by ID (user-filtered unless Founder Rights)"""
    return await sessions_mod.get_session_by_id(chat_id, user_id, role, team_id)


async def list_sessions(user_id: str, role: str = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all chat sessions for user (Founder Rights sees all)"""
    return await sessions_mod.list_user_sessions(user_id, role, team_id)


async def delete_session(chat_id: str, user_id: str, role: str = None) -> bool:
    """Delete a chat session (user-filtered unless Founder Rights)"""
    return await sessions_mod.delete_session_by_id(chat_id, user_id, role)


# ===== Message Management =====

async def append_message(chat_id: str, role: str, content: str, timestamp: str, model: Optional[str] = None, tokens: Optional[int] = None, files: Optional[List[Dict]] = None):
    """Append a message to chat history"""
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


async def get_messages(chat_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get chat messages"""
    memory = _get_memory()

    if limit:
        events = await asyncio.to_thread(memory.get_recent_messages, chat_id, limit)
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

    memory = _get_memory()
    ane_engine = _get_ane_engine()
    metal4_engine = _get_metal4_engine()
    ollama_client = _get_ollama_client()

    # Auto-generate title from first message (Phase 2.3a - use sessions module)
    await sessions_mod.auto_title_session_if_needed(chat_id, content)

    # Save user message
    timestamp = datetime.utcnow().isoformat()
    await append_message(chat_id, "user", content, timestamp)

    # Add to unified context for cross-component persistence
    try:
        from .unified_context import get_unified_context
        from .workspace_session import get_workspace_session_manager

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
    start_time = datetime.utcnow()  # Track start time for analytics

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
        assistant_timestamp = datetime.utcnow().isoformat()
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
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
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


# ===== File Management =====

async def upload_file_to_chat(chat_id: str, filename: str, content: bytes, content_type: str) -> Dict[str, Any]:
    """Upload a file to a chat session"""
    from api.chat_enhancements import FileTextExtractor, DocumentChunker
    try:
        from api.utils import sanitize_filename, sanitize_for_log
    except ImportError:
        from utils import sanitize_filename, sanitize_for_log
    import aiofiles

    memory = _get_memory()
    uploads_dir = _get_chat_uploads_dir()

    # Sanitize filename
    safe_filename = sanitize_filename(filename)

    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    file_ext = Path(safe_filename).suffix
    stored_filename = f"{chat_id}_{file_id}{file_ext}"
    file_path = uploads_dir / stored_filename

    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # Extract text if possible
    file_info = {
        "id": file_id,
        "original_name": safe_filename,
        "stored_name": stored_filename,
        "size": len(content),
        "type": content_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }

    # Try to extract text for RAG
    extracted_text = None
    try:
        extracted_text = await asyncio.to_thread(
            FileTextExtractor.extract,
            file_path,
            content_type
        )

        if extracted_text:
            file_info["text_preview"] = extracted_text[:1000]
            file_info["text_extracted"] = True

            # Create chunks and embeddings for RAG
            chunks = await asyncio.to_thread(
                DocumentChunker.create_chunks_with_metadata,
                extracted_text,
                file_info
            )

            # Store chunks in memory
            await asyncio.to_thread(memory.store_document_chunks, chat_id, chunks)

            file_info["chunks_created"] = len(chunks)
            safe_name = sanitize_for_log(filename)
            logger.info(f"Created {len(chunks)} chunks for file {safe_name}")
        else:
            file_info["text_preview"] = "[Text extraction not supported for this file type]"
            file_info["text_extracted"] = False

    except Exception as e:
        logger.warning(f"Failed to extract text from file: {e}")
        file_info["text_preview"] = f"[Extraction error: {str(e)}]"
        file_info["text_extracted"] = False

    return file_info


# ===== Model Management (Phase 2.3b - delegated to models.py) =====

async def list_ollama_models() -> List[Dict[str, Any]]:
    """List available Ollama models"""
    return await models_mod.list_ollama_models()


async def preload_model(model: str, keep_alive: str = "1h", source: str = "unknown") -> bool:
    """Pre-load a model into memory"""
    return await models_mod.preload_model(model, keep_alive, source)


async def unload_model(model_name: str) -> bool:
    """Unload a specific model from memory"""
    return await models_mod.unload_model(model_name)


# ===== Search & Analytics =====

async def semantic_search(query: str, limit: int, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Search across conversations using semantic similarity"""
    return await analytics_mod.semantic_search(query, limit, user_id, team_id)


async def get_analytics(session_id: Optional[str], user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Get analytics for a session or scoped analytics"""
    return await analytics_mod.get_analytics(session_id, user_id, team_id)


async def get_session_analytics(chat_id: str) -> Dict[str, Any]:
    """Get detailed analytics for a specific session"""
    return await analytics_mod.get_session_analytics(chat_id)


# ===== ANE Context =====

async def get_ane_stats() -> Dict[str, Any]:
    """Get Apple Neural Engine context stats"""
    return await system_mod.get_ane_stats()


async def search_ane_context(query: str, top_k: int = 5, threshold: float = 0.5) -> Dict[str, Any]:
    """Search for similar chat contexts using ANE-accelerated embeddings"""
    return await system_mod.search_ane_context(query, top_k, threshold)


# ===== Embedding Info =====

async def get_embedding_info() -> Dict[str, Any]:
    """Get information about the embedding backend"""
    return await system_mod.get_embedding_info()


# ===== Token Counting =====

async def get_token_count(chat_id: str) -> Dict[str, Any]:
    """Get token count for a chat session"""
    return await system_mod.get_token_count(chat_id)


async def update_session_model(chat_id: str, model: str) -> Dict[str, Any]:
    """Update the model for a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.update_session_model, chat_id, model)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


async def update_session_title(chat_id: str, title: str) -> Dict[str, Any]:
    """Update the title of a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.update_session_title, chat_id, title, auto_titled=False)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


async def set_session_archived(chat_id: str, archived: bool) -> Dict[str, Any]:
    """Archive or unarchive a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.set_session_archived, chat_id, archived)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


# ===== Health & Status =====

async def check_health() -> Dict[str, Any]:
    """Check Ollama health status"""
    return await system_mod.check_health()


async def get_models_status() -> Dict[str, Any]:
    """Get status of all models"""
    return await models_mod.get_models_status()


async def get_ollama_server_status() -> Dict[str, Any]:
    """Check if Ollama server is running"""
    return await ollama_ops_mod.get_ollama_server_status()


# ===== System Management =====

async def get_system_memory() -> Dict[str, Any]:
    """Get actual system memory stats for Mac"""
    try:
        import psutil

        virtual_mem = psutil.virtual_memory()

        total_gb = virtual_mem.total / (1024 ** 3)
        available_gb = virtual_mem.available / (1024 ** 3)
        used_gb = virtual_mem.used / (1024 ** 3)

        usable_percentage = 0.8
        usable_for_models_gb = total_gb * usable_percentage

        return {
            "total_gb": round(total_gb, 2),
            "available_gb": round(available_gb, 2),
            "used_gb": round(used_gb, 2),
            "percent_used": virtual_mem.percent,
            "usable_for_models_gb": round(usable_for_models_gb, 2),
            "usable_percentage": usable_percentage
        }

    except ImportError:
        raise Exception("psutil library not available for memory detection")
    except Exception as e:
        logger.error(f"Failed to get system memory: {e}")
        raise


async def shutdown_ollama_server() -> Dict[str, Any]:
    """Shutdown Ollama server"""
    return await ollama_ops_mod.shutdown_ollama_server()


async def start_ollama_server() -> Dict[str, Any]:
    """Start Ollama server in background"""
    return await ollama_ops_mod.start_ollama_server()


async def restart_ollama_server(reload_models: bool = False, models_to_load: Optional[List[str]] = None) -> Dict[str, Any]:
    """Restart Ollama server and optionally reload specific models"""
    return await ollama_ops_mod.restart_ollama_server(reload_models, models_to_load)


# ===== Data Export =====

async def export_data_to_chat(session_id: str, query_id: str, query: str, results: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """Export query results from Data tab to AI Chat"""
    import pandas as pd
    import io
    import aiofiles
    from api.chat_enhancements import DocumentChunker

    memory = _get_memory()
    uploads_dir = _get_chat_uploads_dir()

    # Create DataFrame from results
    df = pd.DataFrame(results)

    # Create new chat session
    session = await create_session(
        title="Query Analysis",
        model="qwen2.5-coder:7b-instruct",
        user_id=user_id,
        team_id=None
    )

    chat_id = session["id"]

    # Save CSV file
    csv_file_id = uuid.uuid4().hex[:12]
    csv_filename = f"query_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_stored_filename = f"{chat_id}_{csv_file_id}.csv"
    csv_file_path = uploads_dir / csv_stored_filename

    # Write CSV file
    async with aiofiles.open(csv_file_path, 'w') as f:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        await f.write(csv_buffer.getvalue())

    csv_preview = csv_buffer.getvalue()[:1000]

    # Extract CSV text for RAG
    extracted_text = f"""Query Results Dataset

SQL Query:
{query}

Dataset Information:
- Rows: {len(results)}
- Columns: {', '.join(df.columns.tolist())}

Data Preview (CSV format):
{csv_preview}

Column Statistics:
{df.describe(include='all').to_string() if len(df) > 0 else 'No data'}
"""

    # Create chunks and embeddings for RAG
    chunks = await asyncio.to_thread(
        DocumentChunker.create_chunks_with_metadata,
        extracted_text,
        {
            "original_name": csv_filename,
            "type": "text/csv",
            "query": query,
            "row_count": len(results)
        }
    )

    # Store chunks in memory
    await asyncio.to_thread(memory.store_document_chunks, chat_id, chunks)

    # Add system message
    system_content = f"""📊 **Query Results Loaded**

I've analyzed your SQL query results. Here's what I found:

**Query:**
```sql
{query}
```

**Dataset Summary:**
- Total Rows: {len(results):,}
- Columns: {len(df.columns)}
- Data File: `{csv_filename}`

**Available Columns:**
{', '.join(f'`{col}`' for col in df.columns.tolist())}

**Sample Data:**
```
{df.head(5).to_string(index=False) if len(df) > 0 else 'No data'}
```

---

I can help you:
- 🔍 Analyze patterns and trends
- 📈 Generate insights and summaries
- ⚠️ Identify anomalies or outliers
- 💡 Suggest follow-up queries
- 📊 Explain what the data means

What would you like to know about this data?"""

    timestamp = datetime.utcnow().isoformat()
    await append_message(
        chat_id,
        "assistant",
        system_content,
        timestamp,
        files=[{
            "id": csv_file_id,
            "original_name": csv_filename,
            "stored_name": csv_stored_filename,
            "size": csv_file_path.stat().st_size,
            "type": "text/csv",
            "uploaded_at": timestamp,
            "text_preview": csv_preview,
            "text_extracted": True,
            "chunks_created": len(chunks)
        }]
    )

    logger.info(f"Exported {len(results)} rows to chat session {chat_id} with {len(chunks)} RAG chunks")

    return {
        "chat_id": chat_id,
        "file_info": {
            "id": csv_file_id,
            "original_name": csv_filename,
            "stored_name": csv_stored_filename,
            "size": csv_file_path.stat().st_size,
            "type": "text/csv",
            "row_count": len(results),
            "chunks_created": len(chunks)
        },
        "status": "success"
    }


# ===== Model Hot Slots (Phase 2.3b - delegated to hot_slots.py) =====

async def get_hot_slots() -> Dict[int, Optional[str]]:
    """Get current hot slot assignments"""
    return await hot_slots_mod.get_hot_slots()


async def assign_to_hot_slot(slot_number: int, model_name: str) -> Dict[str, Any]:
    """Assign a model to a specific hot slot"""
    return await hot_slots_mod.assign_to_hot_slot(slot_number, model_name)


async def remove_from_hot_slot(slot_number: int) -> Dict[str, Any]:
    """Remove a model from a specific hot slot"""
    return await hot_slots_mod.remove_from_hot_slot(slot_number)


async def load_hot_slot_models(keep_alive: str = "1h") -> Dict[str, Any]:
    """Load all hot slot models into memory"""
    return await hot_slots_mod.load_hot_slot_models(keep_alive)


async def get_orchestrator_suitable_models() -> List[Dict[str, Any]]:
    """Get models suitable for orchestrator use"""
    return await models_mod.get_orchestrator_suitable_models()


# ===== Adaptive Router =====

async def submit_router_feedback(command: str, tool_used: str, success: bool, execution_time: float, user_satisfaction: Optional[int] = None):
    """Submit feedback for adaptive router to learn from"""
    return await system_mod.submit_router_feedback(command, tool_used, success, execution_time, user_satisfaction)


async def get_router_stats() -> Dict[str, Any]:
    """Get adaptive router statistics"""
    return await system_mod.get_router_stats()


async def explain_routing(command: str) -> Dict[str, Any]:
    """Explain how a command would be routed"""
    return await system_mod.explain_routing(command)


# ===== Router Mode =====

def get_router_mode() -> Dict[str, Any]:
    """Get current router mode"""
    return system_mod.get_router_mode()


def set_router_mode(mode: str) -> Dict[str, Any]:
    """Set router mode"""
    return system_mod.set_router_mode(mode)


async def get_combined_router_stats() -> Dict[str, Any]:
    """Get combined stats from both routers"""
    adaptive_router = _get_adaptive_router()
    ane_router = _get_ane_router()

    adaptive_stats = adaptive_router.get_routing_stats() if hasattr(adaptive_router, 'get_routing_stats') else {}
    ane_stats = ane_router.get_stats()

    return {
        "current_mode": current_router_mode,
        "adaptive_router": adaptive_stats,
        "ane_router": ane_stats
    }


# ===== Recursive Prompting =====

async def execute_recursive_prompt(query: str, model: Optional[str] = "qwen2.5-coder:7b-instruct") -> Dict[str, Any]:
    """Execute a query using recursive prompt decomposition"""
    import ollama

    recursive_library = _get_recursive_library()
    ollama_client_lib = ollama.AsyncClient()

    result = await recursive_library.process_query(query, ollama_client_lib)

    return {
        "final_answer": result['final_answer'],
        "steps_executed": result['steps_executed'],
        "total_time_ms": result['total_time_ms'],
        "time_saved_ms": result['time_saved_ms'],
        "cache_hits": result['cache_hits'],
        "plan": {
            "steps": [
                {
                    "step_number": step.step_number,
                    "description": step.description,
                    "complexity": step.complexity.value,
                    "backend": step.backend.value
                }
                for step in result['plan'].steps
            ],
            "estimated_time_ms": result['plan'].total_estimated_time_ms,
            "estimated_power_w": result['plan'].estimated_power_usage_w
        },
        "step_results": [
            {
                "step_number": r.step_number,
                "execution_time_ms": r.execution_time_ms,
                "backend_used": r.backend_used.value,
                "cached": r.cached,
                "output": r.output[:200] + "..." if len(r.output) > 200 else r.output
            }
            for r in result['results']
        ]
    }


async def get_recursive_stats() -> Dict[str, Any]:
    """Get recursive prompt library statistics"""
    recursive_library = _get_recursive_library()
    stats = recursive_library.get_stats()
    return stats


# ===== Ollama Configuration =====

def get_ollama_configuration() -> Dict[str, Any]:
    """Get current Ollama configuration"""
    return ollama_ops_mod.get_ollama_configuration()


def set_ollama_mode(mode: str) -> Dict[str, Any]:
    """Set Ollama performance mode"""
    return ollama_ops_mod.set_ollama_mode(mode)


def auto_detect_ollama_config() -> Dict[str, Any]:
    """Auto-detect optimal Ollama settings"""
    return ollama_ops_mod.auto_detect_ollama_config()


# ===== Performance Monitoring =====

def get_current_performance() -> Dict[str, Any]:
    """Get current performance metrics"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.get_current_metrics()


def get_performance_statistics() -> Dict[str, Any]:
    """Get performance statistics over time"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.get_statistics()


def get_performance_history(last_n: int = 20) -> Dict[str, Any]:
    """Get recent performance history"""
    performance_monitor = _get_performance_monitor()
    history = performance_monitor.get_history(last_n)
    return {"history": history}


def check_thermal_throttling() -> Dict[str, Any]:
    """Check for thermal throttling"""
    performance_monitor = _get_performance_monitor()
    return performance_monitor.check_thermal_throttling()


def reset_performance_metrics():
    """Reset performance metrics"""
    performance_monitor = _get_performance_monitor()
    performance_monitor.reset()
    return {"status": "success", "message": "Performance metrics reset"}


# ===== Panic Mode =====

async def trigger_panic_mode(reason: Optional[str] = "Manual activation") -> Dict[str, Any]:
    """Trigger panic mode - EMERGENCY"""
    panic_mode = _get_panic_mode()
    result = await panic_mode.trigger_panic(reason)
    return result


def get_panic_status() -> Dict[str, Any]:
    """Get current panic mode status"""
    panic_mode = _get_panic_mode()
    return panic_mode.get_panic_status()


def reset_panic_mode():
    """Reset panic mode"""
    panic_mode = _get_panic_mode()
    panic_mode.reset_panic()
    return {"status": "success", "message": "Panic mode reset"}


# ===== Learning System =====

async def get_learning_patterns(days: int = 30) -> Dict[str, Any]:
    """Get usage patterns and learning insights"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    patterns = learning_engine.analyze_patterns(days=days)
    return patterns


async def get_recommendations() -> Dict[str, Any]:
    """Get current classification recommendations"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    recommendations = learning_engine.get_recommendations()
    return {"recommendations": recommendations}


async def accept_recommendation(recommendation_id: int, feedback: Optional[str] = None) -> bool:
    """Accept a classification recommendation"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    return learning_engine.accept_recommendation(recommendation_id, feedback)


async def reject_recommendation(recommendation_id: int, feedback: Optional[str] = None) -> bool:
    """Reject a classification recommendation"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    return learning_engine.reject_recommendation(recommendation_id, feedback)


async def get_optimal_model_for_task(task_type: str, top_n: int = 3) -> Dict[str, Any]:
    """Get the optimal models for a specific task type"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    models = learning_engine.get_optimal_model_for_task(task_type, top_n)

    return {
        "task_type": task_type,
        "recommended_models": [
            {"model": model, "confidence": confidence}
            for model, confidence in models
        ]
    }


async def track_usage_manually(
    model_name: str,
    classification: Optional[str] = None,
    session_id: Optional[str] = None,
    message_count: int = 1,
    tokens_used: int = 0,
    task_detected: Optional[str] = None
):
    """Manually track model usage"""
    try:
        from api.learning_engine import get_learning_engine
    except ImportError:
        from learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    learning_engine.track_usage(
        model_name=model_name,
        classification=classification,
        session_id=session_id,
        message_count=message_count,
        tokens_used=tokens_used,
        task_detected=task_detected
    )
    return {"status": "success", "message": "Usage tracked"}
