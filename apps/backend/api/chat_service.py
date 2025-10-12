"""
Chat Service for Neutron Star
Local AI chat with Ollama integration, file attachments, and session management
Uses advanced memory system extracted from Jarvis Agent
"""

import os
import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import aiofiles

from api.chat_memory import get_memory, ConversationEvent
from api.chat_enhancements import (
    ChatTitleGenerator,
    FileTextExtractor,
    SimpleEmbedding,
    ConversationAnalytics,
    DocumentChunker
)
from api.ane_context_engine import get_ane_engine
from api.token_counter import TokenCounter
from api.error_handler import ErrorHandler
from api.model_manager import get_model_manager

logger = logging.getLogger(__name__)

# Storage paths
CHAT_UPLOADS_DIR = Path(".neutron_data/uploads")

# Ensure directories exist
CHAT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Get memory and ANE engine instances
memory = get_memory()
ane_engine = get_ane_engine()
token_counter = TokenCounter()
model_manager = get_model_manager()

logger.info("🚀 Chat service initialized with ANE context engine")


# ===== Models =====

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: str
    files: List[Dict[str, Any]] = Field(default_factory=list)
    model: Optional[str] = None
    tokens: Optional[int] = None


class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    model: str = "qwen2.5-coder:7b-instruct"
    message_count: int = 0


class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = "qwen2.5-coder:7b-instruct"


class SendMessageRequest(BaseModel):
    content: str
    model: Optional[str] = None

    # LLM Parameters
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1
    system_prompt: Optional[str] = None


class OllamaModel(BaseModel):
    name: str
    size: str
    modified_at: str


# ===== Storage Layer (using advanced memory system) =====

class ChatStorage:
    """Memory-based chat storage using NeutronChatMemory"""

    @staticmethod
    async def create_session(title: str, model: str) -> ChatSession:
        """Create a new chat session"""
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"

        session_data = await asyncio.to_thread(
            memory.create_session,
            chat_id,
            title,
            model
        )

        return ChatSession(**session_data)

    @staticmethod
    async def get_session(chat_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        session_data = await asyncio.to_thread(memory.get_session, chat_id)

        if not session_data:
            return None

        return ChatSession(**session_data)

    @staticmethod
    async def list_sessions() -> List[ChatSession]:
        """List all chat sessions"""
        sessions_data = await asyncio.to_thread(memory.list_sessions)
        return [ChatSession(**s) for s in sessions_data]

    @staticmethod
    async def delete_session(chat_id: str):
        """Delete a chat session"""
        await asyncio.to_thread(memory.delete_session, chat_id)

    @staticmethod
    async def append_message(chat_id: str, message: ChatMessage):
        """Append a message to chat history"""
        event = ConversationEvent(
            timestamp=message.timestamp,
            role=message.role,
            content=message.content,
            model=message.model,
            tokens=message.tokens,
            files=message.files
        )

        await asyncio.to_thread(memory.add_message, chat_id, event)

        # Update rolling summary every message
        await asyncio.to_thread(memory.update_summary, chat_id)

    @staticmethod
    async def get_messages(chat_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get chat messages"""
        if limit:
            events = await asyncio.to_thread(memory.get_recent_messages, chat_id, limit)
        else:
            events = await asyncio.to_thread(memory.get_messages, chat_id)

        messages = []
        for event in events:
            messages.append(ChatMessage(
                role=event.role,
                content=event.content,
                timestamp=event.timestamp,
                files=event.files or [],
                model=event.model,
                tokens=event.tokens
            ))

        return messages


# ===== Ollama Integration =====

class OllamaClient:
    """Client for Ollama API"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def list_models(self) -> List[OllamaModel]:
        """List available models"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    models.append(OllamaModel(
                        name=model_data["name"],
                        size=self._format_size(model_data.get("size", 0)),
                        modified_at=model_data.get("modified_at", "")
                    ))

                return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def preload_model(self, model: str, keep_alive: str = "1h") -> bool:
        """
        Pre-load a model into memory for instant responses

        Args:
            model: Model name to load
            keep_alive: How long to keep model in memory (e.g., "1h", "30m", "5m")

        Returns:
            True if successful, False otherwise
        """
        try:
            import httpx

            payload = {
                "model": model,
                "prompt": "",  # Empty prompt to just load the model
                "stream": False,
                "keep_alive": keep_alive
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                logger.info(f"✓ Pre-loaded model '{model}' (keep_alive: {keep_alive})")
                return True

        except Exception as e:
            logger.error(f"Failed to pre-load model '{model}': {e}")
            return False

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1
    ) -> AsyncGenerator[str, None]:
        """Send chat request to Ollama with streaming and custom parameters"""
        try:
            import httpx

            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k,
                    "repeat_penalty": repeat_penalty
                }
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.strip():
                            chunk = json.loads(line)

                            # Yield content if present
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    yield content

                            # Check if done
                            if chunk.get("done"):
                                break

        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format size in bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"


# ===== Router =====

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
ollama_client = OllamaClient()


@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(request: CreateChatRequest):
    """Create a new chat session"""
    session = await ChatStorage.create_session(
        title=request.title or "New Chat",
        model=request.model or "qwen2.5-coder:7b-instruct"
    )
    return session


@router.get("/sessions", response_model=List[ChatSession])
async def list_chat_sessions():
    """List all chat sessions"""
    sessions = await ChatStorage.list_sessions()
    # Sort by updated_at descending
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions


@router.get("/sessions/{chat_id}", response_model=Dict[str, Any])
async def get_chat_session(chat_id: str, limit: Optional[int] = None):
    """Get chat session with message history"""
    session = await ChatStorage.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = await ChatStorage.get_messages(chat_id, limit=limit)

    return {
        "session": session.model_dump(),
        "messages": [m.model_dump() for m in messages]
    }


@router.delete("/sessions/{chat_id}")
async def delete_chat_session(chat_id: str):
    """Delete a chat session"""
    await ChatStorage.delete_session(chat_id)
    return {"status": "deleted", "chat_id": chat_id}


@router.post("/sessions/{chat_id}/messages")
async def send_message(chat_id: str, request: SendMessageRequest):
    """Send a message and get streaming response"""

    # Verify session exists
    session = await ChatStorage.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Use model from request or session default
    model = request.model or session.model

    # Auto-generate title from first message
    session_data = await asyncio.to_thread(memory.get_session, chat_id)
    if session_data and session_data.get("message_count", 0) == 0:
        # This is the first message - generate title
        title = await asyncio.to_thread(
            ChatTitleGenerator.generate_from_first_message,
            request.content
        )
        await asyncio.to_thread(memory.update_session_title, chat_id, title, auto_titled=True)
        logger.info(f"Auto-generated title for {chat_id}: {title}")

    # Save user message
    user_message = ChatMessage(
        role="user",
        content=request.content,
        timestamp=datetime.utcnow().isoformat()
    )
    await ChatStorage.append_message(chat_id, user_message)

    # Get conversation history (full 200k token context)
    history = await ChatStorage.get_messages(chat_id, limit=None)

    # Check if there are uploaded documents to use for RAG
    query_embedding = await asyncio.to_thread(SimpleEmbedding.create_embedding, request.content)
    relevant_chunks = await asyncio.to_thread(memory.search_document_chunks, chat_id, query_embedding, top_k=3)

    # Add relevant document context to the prompt if found
    rag_context = ""
    if relevant_chunks:
        rag_context = "\n\n📎 Relevant document context:\n"
        for i, chunk in enumerate(relevant_chunks, 1):
            rag_context += f"\n[{chunk['filename']}, chunk {chunk['chunk_index'] + 1}]:\n{chunk['content'][:300]}...\n"
        logger.info(f"Added {len(relevant_chunks)} document chunks to context")

    # Format for Ollama
    ollama_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]

    # Add system prompt at the beginning if provided
    if request.system_prompt:
        ollama_messages.insert(0, {"role": "system", "content": request.system_prompt})

    # Inject RAG context into the last user message if available
    if rag_context and ollama_messages:
        # Find the last user message and add context
        for i in range(len(ollama_messages) - 1, -1, -1):
            if ollama_messages[i]["role"] == "user":
                ollama_messages[i]["content"] = ollama_messages[i]["content"] + rag_context
                break

    # Stream response
    async def generate():
        full_response = ""

        try:
            # Send SSE header
            yield "data: [START]\n\n"

            async for chunk in ollama_client.chat(
                model,
                ollama_messages,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                repeat_penalty=request.repeat_penalty
            ):
                full_response += chunk
                # Send as SSE event
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Save assistant message
            assistant_message = ChatMessage(
                role="assistant",
                content=full_response,
                timestamp=datetime.utcnow().isoformat(),
                model=model,
                tokens=len(full_response.split())  # Rough estimate
            )
            await ChatStorage.append_message(chat_id, assistant_message)

            # Preserve context with ANE (background vectorization)
            context_data = {
                "user_message": request.content,
                "assistant_response": full_response,
                "model": model,
                "timestamp": datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                ane_engine.preserve_context,
                chat_id,
                context_data,
                {"model": model, "tokens": len(full_response.split())}
            )

            # Send done event
            yield f"data: {json.dumps({'done': True, 'message_id': str(uuid.uuid4())})}\n\n"

        except Exception as e:
            logger.error(f"Error in message streaming: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/sessions/{chat_id}/upload")
async def upload_file_to_chat(
    chat_id: str,
    file: UploadFile = File(...)
):
    """Upload a file to a chat session"""

    # Verify session exists
    session = await ChatStorage.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    file_ext = Path(file.filename).suffix
    stored_filename = f"{chat_id}_{file_id}{file_ext}"
    file_path = CHAT_UPLOADS_DIR / stored_filename

    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Extract text if possible (PDF, txt, etc.)
    file_info = {
        "id": file_id,
        "original_name": file.filename,
        "stored_name": stored_filename,
        "size": len(content),
        "type": file.content_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }

    # Try to extract text for RAG
    extracted_text = None
    try:
        extracted_text = await asyncio.to_thread(
            FileTextExtractor.extract,
            file_path,
            file.content_type
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
            logger.info(f"Created {len(chunks)} chunks for file {file.filename}")
        else:
            file_info["text_preview"] = "[Text extraction not supported for this file type]"
            file_info["text_extracted"] = False

    except Exception as e:
        logger.warning(f"Failed to extract text from file: {e}")
        file_info["text_preview"] = f"[Extraction error: {str(e)}]"
        file_info["text_extracted"] = False

    return file_info


@router.get("/models", response_model=List[OllamaModel])
async def list_ollama_models():
    """List available Ollama models"""
    models = await ollama_client.list_models()

    if not models:
        # Return some default models if Ollama is not running
        return [
            OllamaModel(
                name="qwen2.5-coder:7b-instruct",
                size="4.7GB",
                modified_at=datetime.utcnow().isoformat()
            )
        ]

    return models


@router.post("/models/preload")
async def preload_model(model: str, keep_alive: str = "1h"):
    """
    Pre-load a model into memory for instant responses

    Args:
        model: Name of the model to pre-load
        keep_alive: How long to keep model in memory (default: "1h")

    Returns:
        Status of pre-loading operation
    """
    success = await ollama_client.preload_model(model, keep_alive)

    if success:
        return {
            "status": "success",
            "model": model,
            "keep_alive": keep_alive,
            "message": f"Model '{model}' pre-loaded successfully"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pre-load model '{model}'. Check if Ollama is running and model is available."
        )


@router.get("/search")
async def semantic_search(query: str, limit: int = 10):
    """Search across all conversations using semantic similarity"""
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    results = await asyncio.to_thread(memory.search_messages_semantic, query, limit)

    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


@router.get("/analytics")
async def get_analytics(session_id: Optional[str] = None):
    """Get analytics for a session or global analytics"""
    analytics = await asyncio.to_thread(memory.get_analytics, session_id)
    return analytics


@router.get("/sessions/{chat_id}/analytics")
async def get_session_analytics(chat_id: str):
    """Get detailed analytics for a specific session"""
    session = await ChatStorage.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get messages for analysis
    messages = await ChatStorage.get_messages(chat_id)

    # Calculate stats
    stats = await asyncio.to_thread(
        ConversationAnalytics.calculate_session_stats,
        [msg.model_dump() for msg in messages]
    )

    topics = await asyncio.to_thread(
        ConversationAnalytics.get_conversation_topics,
        [msg.model_dump() for msg in messages]
    )

    return {
        "session_id": chat_id,
        "title": session.title,
        "stats": stats,
        "topics": topics
    }


@router.get("/ane/stats")
async def get_ane_stats():
    """Get Apple Neural Engine context stats"""
    stats = await asyncio.to_thread(ane_engine.stats)
    return stats


@router.get("/ane/search")
async def search_ane_context(query: str, top_k: int = 5, threshold: float = 0.5):
    """
    Search for similar chat contexts using ANE-accelerated embeddings

    Args:
        query: Search query text
        top_k: Number of results to return
        threshold: Minimum similarity score (0-1)
    """
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

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


@router.get("/embedding/info")
async def get_embedding_info():
    """Get information about the embedding backend (MLX/Metal/ANE status)"""
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


@router.post("/sessions/{chat_id}/token-count")
async def get_token_count(chat_id: str):
    """Get token count for a chat session"""
    session = await ChatStorage.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = await ChatStorage.get_messages(chat_id, limit=None)

    # Format messages for token counting
    message_list = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    # Count tokens
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


@router.get("/health")
async def check_health():
    """Check Ollama health status"""
    return await ErrorHandler.check_ollama_health()


@router.get("/models/status")
async def get_models_status():
    """Get status of all models (loaded/unloaded, favorites)"""
    status = await model_manager.get_model_status(ollama_client)
    return {"models": status}


@router.get("/models/favorites")
async def get_favorite_models():
    """Get list of favorite models"""
    favorites = model_manager.get_favorites()
    return {"favorites": favorites}


@router.post("/models/favorites/{model_name}")
async def add_favorite_model(model_name: str):
    """Add a model to favorites"""
    success = model_manager.add_favorite(model_name)
    return {
        "success": success,
        "model": model_name,
        "favorites": model_manager.get_favorites()
    }


@router.delete("/models/favorites/{model_name}")
async def remove_favorite_model(model_name: str):
    """Remove a model from favorites"""
    success = model_manager.remove_favorite(model_name)
    return {
        "success": success,
        "model": model_name,
        "favorites": model_manager.get_favorites()
    }


@router.post("/models/load-favorites")
async def load_favorite_models(keep_alive: str = "1h"):
    """
    Load all favorite models into memory
    Useful for startup to pre-warm all favorites
    """
    favorites = model_manager.get_favorites()
    results = []

    for model in favorites:
        success = await ollama_client.preload_model(model, keep_alive)
        results.append({
            "model": model,
            "loaded": success
        })

    return {
        "total": len(favorites),
        "results": results,
        "keep_alive": keep_alive
    }


class ExportToChatRequest(BaseModel):
    session_id: str
    query_id: str
    query: str
    results: List[Dict[str, Any]]


@router.post("/data/export-to-chat")
async def export_data_to_chat(request: ExportToChatRequest):
    """
    Export query results from Data tab to AI Chat
    Creates a new chat session with JSON results pre-attached
    """
    try:
        # Create JSON export data
        export_data = {
            "export_type": "query_results",
            "query": request.query,
            "results": request.results,
            "metadata": {
                "source_session": request.session_id,
                "query_id": request.query_id,
                "row_count": len(request.results),
                "exported_at": datetime.utcnow().isoformat()
            }
        }

        # Create new chat session
        chat_session = await ChatStorage.create_session(
            title="Data Analysis Export",
            model="qwen2.5-coder:7b-instruct"
        )

        # Save JSON file to uploads
        file_id = uuid.uuid4().hex[:12]
        filename = f"query_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        stored_filename = f"{chat_session.id}_{file_id}.json"
        file_path = CHAT_UPLOADS_DIR / stored_filename

        # Write JSON file
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(export_data, indent=2))

        # Create file info and attach to chat
        file_info = {
            "id": file_id,
            "original_name": filename,
            "stored_name": stored_filename,
            "size": file_path.stat().st_size,
            "type": "application/json",
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_preview": f"Query results: {len(request.results)} rows",
            "text_extracted": True,
            "export_metadata": export_data["metadata"]
        }

        # Add system message about the attached file
        system_message = ChatMessage(
            role="assistant",
            content=f"📊 Data exported from query:\n\n```sql\n{request.query}\n```\n\n**Results**: {len(request.results)} rows\n**File**: {filename}\n\nWhat would you like to know about this data?",
            timestamp=datetime.utcnow().isoformat()
        )
        await ChatStorage.append_message(chat_session.id, system_message)

        logger.info(f"Exported {len(request.results)} rows to chat session {chat_session.id}")

        return {
            "chat_id": chat_session.id,
            "file_info": file_info,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to export to chat: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/system/memory")
async def get_system_memory():
    """
    Get actual system memory stats for Mac
    Used by model management to calculate available memory for models
    """
    try:
        import psutil

        # Get system memory
        virtual_mem = psutil.virtual_memory()

        # Convert to GB
        total_gb = virtual_mem.total / (1024 ** 3)
        available_gb = virtual_mem.available / (1024 ** 3)
        used_gb = virtual_mem.used / (1024 ** 3)

        # Calculate usable percentage for models (80% of total)
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
        # psutil not available - return error
        raise HTTPException(
            status_code=503,
            detail="psutil library not available for memory detection"
        )
    except Exception as e:
        logger.error(f"Failed to get system memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama/server/status")
async def get_ollama_server_status():
    """
    Check if Ollama server is running and get loaded models
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Check if server is responding
            response = await client.get(f"{ollama_client.base_url}/api/ps")

            if response.status_code == 200:
                data = response.json()
                loaded_models = [model.get("name") for model in data.get("models", [])]

                return {
                    "running": True,
                    "loaded_models": loaded_models,
                    "model_count": len(loaded_models)
                }
            else:
                return {"running": False, "loaded_models": [], "model_count": 0}

    except Exception as e:
        logger.debug(f"Ollama server check failed: {e}")
        return {"running": False, "loaded_models": [], "model_count": 0}


@router.post("/ollama/server/shutdown")
async def shutdown_ollama_server():
    """
    Shutdown Ollama server (unloads all models and stops server)
    WARNING: This will terminate all active model sessions
    """
    try:
        import subprocess
        import httpx

        # First, get list of currently loaded models to return to user
        loaded_models = []
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{ollama_client.base_url}/api/ps")
                if response.status_code == 200:
                    data = response.json()
                    loaded_models = [model.get("name") for model in data.get("models", [])]
        except:
            pass

        # Kill ollama process
        try:
            # Use killall on macOS to terminate ollama
            subprocess.run(["killall", "-9", "ollama"], check=False, capture_output=True)
            logger.info("🔴 Ollama server shutdown requested - all models unloaded")

            return {
                "status": "shutdown",
                "message": "Ollama server stopped successfully",
                "previously_loaded_models": loaded_models,
                "model_count": len(loaded_models)
            }
        except Exception as e:
            logger.error(f"Failed to shutdown Ollama: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to shutdown Ollama server: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Ollama shutdown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/server/start")
async def start_ollama_server():
    """
    Start Ollama server in background
    """
    try:
        import subprocess

        # Start ollama serve in background
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent process
        )

        # Wait a moment for startup
        await asyncio.sleep(2)

        # Check if it started successfully
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{ollama_client.base_url}/api/tags")
                if response.status_code == 200:
                    logger.info("🟢 Ollama server started successfully")
                    return {
                        "status": "started",
                        "message": "Ollama server started successfully",
                        "pid": process.pid
                    }
        except:
            pass

        raise HTTPException(
            status_code=500,
            detail="Ollama server started but not responding. Check logs."
        )

    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start Ollama server: {str(e)}"
        )


@router.post("/ollama/server/restart")
async def restart_ollama_server(reload_models: bool = False, models_to_load: List[str] = []):
    """
    Restart Ollama server and optionally reload specific models

    Args:
        reload_models: Whether to reload models after restart
        models_to_load: List of model names to load (if empty and reload_models=True, loads previous models)
    """
    try:
        # Get currently loaded models before shutdown
        previous_models = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{ollama_client.base_url}/api/ps")
                if response.status_code == 200:
                    data = response.json()
                    previous_models = [model.get("name") for model in data.get("models", [])]
        except:
            pass

        # Shutdown first
        import subprocess
        subprocess.run(["killall", "-9", "ollama"], check=False, capture_output=True)
        logger.info("🔄 Restarting Ollama server...")

        # Wait a moment
        await asyncio.sleep(1)

        # Start server
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait for startup
        await asyncio.sleep(3)

        # Reload models if requested
        loaded_results = []
        if reload_models:
            models_to_reload = models_to_load if models_to_load else previous_models

            for model in models_to_reload:
                try:
                    success = await ollama_client.preload_model(model, "1h")
                    loaded_results.append({
                        "model": model,
                        "loaded": success
                    })
                except Exception as e:
                    logger.error(f"Failed to reload model {model}: {e}")
                    loaded_results.append({
                        "model": model,
                        "loaded": False,
                        "error": str(e)
                    })

        return {
            "status": "restarted",
            "message": "Ollama server restarted successfully",
            "pid": process.pid,
            "models_reloaded": reload_models,
            "reload_results": loaded_results,
            "previously_loaded": previous_models
        }

    except Exception as e:
        logger.error(f"Failed to restart Ollama: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart Ollama server: {str(e)}"
        )


@router.post("/models/unload/{model_name}")
async def unload_model(model_name: str):
    """
    Unload a specific model from memory
    Uses keep_alive=0 to immediately unload
    """
    try:
        import httpx

        payload = {
            "model": model_name,
            "prompt": "",
            "stream": False,
            "keep_alive": 0  # Immediate unload
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ollama_client.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

        logger.info(f"✓ Unloaded model '{model_name}'")
        return {
            "status": "unloaded",
            "model": model_name,
            "message": f"Model '{model_name}' unloaded successfully"
        }

    except Exception as e:
        logger.error(f"Failed to unload model '{model_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unload model: {str(e)}"
        )


# Export router
__all__ = ["router"]
