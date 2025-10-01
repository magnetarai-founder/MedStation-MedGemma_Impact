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

logger = logging.getLogger(__name__)

# Storage paths
CHAT_UPLOADS_DIR = Path(".neutron_data/uploads")

# Ensure directories exist
CHAT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Get memory and ANE engine instances
memory = get_memory()
ane_engine = get_ane_engine()

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

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Send chat request to Ollama with streaming"""
        try:
            import httpx

            payload = {
                "model": model,
                "messages": messages,
                "stream": stream
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

    # Get conversation history (last 50 messages for context)
    history = await ChatStorage.get_messages(chat_id, limit=50)

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

            async for chunk in ollama_client.chat(model, ollama_messages):
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


# Export router
__all__ = ["router"]
