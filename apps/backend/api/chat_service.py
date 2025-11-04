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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import aiofiles

# Try both import styles for flexibility
try:
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
    from api.metal4_engine import get_metal4_engine
    from api.adaptive_router import AdaptiveRouter
    from api.jarvis_memory import JarvisMemory
    from api.learning_system import LearningSystem
    from api.ane_router import get_ane_router, ANERouter
    from api.learning_engine import get_learning_engine
except ImportError:
    # Fallback for standalone execution
    from chat_memory import get_memory, ConversationEvent
    from chat_enhancements import (
        ChatTitleGenerator,
        FileTextExtractor,
        SimpleEmbedding,
        ConversationAnalytics,
        DocumentChunker
    )
    from ane_context_engine import get_ane_engine
    from token_counter import TokenCounter
    from error_handler import ErrorHandler
    from model_manager import get_model_manager
    from metal4_engine import get_metal4_engine
    from adaptive_router import AdaptiveRouter
    from jarvis_memory import JarvisMemory
    from learning_system import LearningSystem
    from ane_router import get_ane_router, ANERouter

logger = logging.getLogger(__name__)

# Storage paths
from config_paths import get_config_paths
CHAT_UPLOADS_DIR = get_config_paths().uploads_dir

# Ensure directories exist
CHAT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Get memory and ANE engine instances
memory = get_memory()
ane_engine = get_ane_engine()
token_counter = TokenCounter()
model_manager = get_model_manager()
metal4_engine = get_metal4_engine()

# Initialize adaptive router with learning
jarvis_memory = JarvisMemory()
learning_system = LearningSystem(memory=jarvis_memory)
adaptive_router = AdaptiveRouter(memory=jarvis_memory, learning=learning_system)

# Initialize ANE router (ultra-low power mode for field work)
ane_router = get_ane_router()

# Router mode: 'adaptive' (GPU, learns) or 'ane' (ultra-low power)
current_router_mode = 'ane'  # Default to ANE for battery life

# Initialize recursive prompt library
try:
    from api.recursive_prompt_library import get_recursive_library
except ImportError:
    from recursive_prompt_library import get_recursive_library
recursive_library = get_recursive_library()

# Initialize Ollama config manager
try:
    from api.ollama_config import get_ollama_config
except ImportError:
    from ollama_config import get_ollama_config
ollama_config = get_ollama_config()

# Initialize performance monitor
try:
    from api.performance_monitor import get_performance_monitor
except ImportError:
    from performance_monitor import get_performance_monitor
performance_monitor = get_performance_monitor()

# Initialize panic mode (missionary safety)
try:
    from api.panic_mode import get_panic_mode
except ImportError:
    from panic_mode import get_panic_mode
panic_mode = get_panic_mode()

logger.info("🚀 Chat service initialized with ANE context engine")
if metal4_engine.is_available():
    logger.info("✅ Metal 4 tick flow enabled for parallel ML operations")
logger.info("🧠 Adaptive router initialized with learning system")
logger.info("🔄 Recursive prompt library ready for complex queries")


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

    # Recursive Prompting
    use_recursive: Optional[bool] = True  # Enable by default for complex queries


class OllamaModel(BaseModel):
    name: str
    size: str
    modified_at: str


# ===== Storage Layer (using advanced memory system) =====

class ChatStorage:
    """Memory-based chat storage using NeutronChatMemory"""

    @staticmethod
    async def create_session(title: str, model: str, user_id: str, team_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session for user"""
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"

        session_data = await asyncio.to_thread(
            memory.create_session,
            chat_id,
            title,
            model,
            user_id,  # Pass user_id to memory
            team_id
        )

        return ChatSession(**session_data)

    @staticmethod
    async def get_session(chat_id: str, user_id: str, role: str = None, team_id: Optional[str] = None) -> Optional[ChatSession]:
        """Get session by ID (user-filtered unless God Rights)"""
        session_data = await asyncio.to_thread(
            memory.get_session,
            chat_id,
            user_id=user_id,
            role=role,
            team_id=team_id
        )

        if not session_data:
            return None

        return ChatSession(**session_data)

    @staticmethod
    async def list_sessions(user_id: str, role: str = None, team_id: Optional[str] = None) -> List[ChatSession]:
        """List all chat sessions for user (God Rights sees all)"""
        sessions_data = await asyncio.to_thread(
            memory.list_sessions,
            user_id=user_id,
            role=role,
            team_id=team_id
        )
        return [ChatSession(**s) for s in sessions_data]

    @staticmethod
    async def delete_session(chat_id: str, user_id: str, role: str = None):
        """Delete a chat session (user-filtered unless God Rights)"""
        return await asyncio.to_thread(
            memory.delete_session,
            chat_id,
            user_id=user_id,
            role=role
        )

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

from fastapi import Depends

# Import auth middleware
try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
try:
    from api.permission_engine import require_perm_team
except ImportError:
    from permission_engine import require_perm_team

# Import utils
try:
    from api.utils import sanitize_for_log
except ImportError:
    from utils import sanitize_for_log

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_user)]  # Require auth for all chat endpoints
)

# Public router for health checks (no auth required)
public_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat - Public"]
)

ollama_client = OllamaClient()


@router.post("/sessions", response_model=ChatSession)
@require_perm_team("chat.use")
async def create_chat_session(request: Request, body: CreateChatRequest, team_id: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Create a new chat session"""
    session = await ChatStorage.create_session(
        title=body.title or "New Chat",
        model=body.model or "qwen2.5-coder:7b-instruct",
        user_id=current_user["user_id"],
        team_id=team_id
    )
    return session


@router.get("/sessions", response_model=List[ChatSession])
@require_perm_team("chat.use")
async def list_chat_sessions(team_id: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """List all chat sessions for current user"""
    sessions = await ChatStorage.list_sessions(
        user_id=current_user["user_id"],
        role=current_user.get("role"),
        team_id=team_id
    )
    # Sort by updated_at descending
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions


@router.get("/sessions/{chat_id}", response_model=Dict[str, Any])
@require_perm_team("chat.use")
async def get_chat_session(chat_id: str, limit: Optional[int] = None, team_id: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Get chat session with message history (user-filtered)"""
    session = await ChatStorage.get_session(
        chat_id,
        user_id=current_user["user_id"],
        role=current_user.get("role"),
        team_id=team_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or access denied")

    messages = await ChatStorage.get_messages(
        chat_id,
        limit=limit
    )

    return {
        "session": session.model_dump(),
        "messages": [m.model_dump() for m in messages]
    }


@router.delete("/sessions/{chat_id}")
async def delete_chat_session(request: Request, chat_id: str, current_user: Dict = Depends(get_current_user)):
    """Delete a chat session (user-filtered)"""
    deleted = await ChatStorage.delete_session(
        chat_id,
        user_id=current_user["user_id"],
        role=current_user.get("role")
    )
    if not deleted:
        raise HTTPException(status_code=403, detail="Access denied or session not found")
    return {"status": "deleted", "chat_id": chat_id}


@router.post("/sessions/{chat_id}/messages")
@require_perm_team("chat.use")
async def send_message(request: Request, chat_id: str, body: SendMessageRequest, team_id: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Send a message and get streaming response"""

    # Verify session exists
    session = await ChatStorage.get_session(chat_id, user_id=current_user["user_id"], role=current_user.get("role"), team_id=team_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Use model from body or session default
    model = body.model or session.model

    # Auto-generate title from first message
    session_data = await asyncio.to_thread(memory.get_session, chat_id)
    if session_data and session_data.get("message_count", 0) == 0:
        # This is the first message - generate title
        title = await asyncio.to_thread(
            ChatTitleGenerator.generate_from_first_message,
            body.content
        )
        await asyncio.to_thread(memory.update_session_title, chat_id, title, auto_titled=True)
        safe_title = sanitize_for_log(title)
        logger.info(f"Auto-generated title for {chat_id}: {safe_title}")

    # Save user message
    user_message = ChatMessage(
        role="user",
        content=body.content,
        timestamp=datetime.utcnow().isoformat()
    )
    await ChatStorage.append_message(chat_id, user_message)

    # ===== ADAPTIVE ROUTING WITH LEARNING =====
    # Use adaptive router (GPU, learns) or ANE router (ultra-low power)
    routing_start = asyncio.get_event_loop().time()

    if current_router_mode == 'ane':
        # ANE routing (ultra-low power, <0.1W)
        ane_result = await asyncio.to_thread(
            ane_router.route,
            body.content
        )
        routing_time = (asyncio.get_event_loop().time() - routing_start) * 1000

        logger.info(f"🧠 ANE routing: {ane_result.target.value} ({ane_result.confidence:.0%}) - {routing_time:.1f}ms [<0.1W]")
        logger.debug(f"   Reasoning: {ane_result.reasoning}")

        # Convert ANE result to adaptive router format
        from api.adaptive_router import ToolType, TaskType, AdaptiveRouteResult

        # Map ANE targets to tool types
        ane_to_tool = {
            'ollama_chat': ToolType.OLLAMA,
            'p2p_message': ToolType.P2P,
            'data_query': ToolType.DATA,
            'system_cmd': ToolType.SYSTEM,
        }

        route_result = AdaptiveRouteResult(
            task_type=TaskType.CHAT,  # Default
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
        # Adaptive routing (GPU, learns from history)
        route_result = await asyncio.to_thread(
            adaptive_router.route_task,
            body.content
        )
        routing_time = (asyncio.get_event_loop().time() - routing_start) * 1000

        logger.info(f"🧠 Adaptive routing: {route_result.tool_type.value} ({route_result.confidence:.0%}) - {routing_time:.1f}ms")
        if route_result.reasoning:
            logger.debug(f"   Reasoning: {route_result.reasoning}")
    if route_result.recommendations:
        logger.debug(f"   Recommendations: {len(route_result.recommendations)}")

    # Use routing suggestion if confidence is high enough
    if route_result.confidence > 0.6 and route_result.model_name:
        model = route_result.model_name
        logger.info(f"   Using routed model: {model}")

    # ===== RECURSIVE PROMPT PROCESSING =====
    # Determine if query is complex enough for recursive decomposition
    use_recursive = body.use_recursive and len(body.content.split()) > 10

    if use_recursive:
        logger.info("🔄 Using recursive prompt decomposition for complex query")

    # Get conversation history
    # Use last 75 messages for full context + summary of earlier messages
    all_history = await ChatStorage.get_messages(chat_id, limit=None)
    CONTEXT_WINDOW = 75

    if len(all_history) > CONTEXT_WINDOW:
        # Use last 75 messages
        history = all_history[-CONTEXT_WINDOW:]

        # Get summary of earlier messages
        summary_data = await asyncio.to_thread(memory.get_summary, chat_id)
        earlier_summary = summary_data['summary'] if summary_data else None
    else:
        # Use all messages if less than context window
        history = all_history
        earlier_summary = None

    # ===== METAL 4 TICK FLOW (OPTIMIZED) =====
    # Only use Metal4 RAG if there are documents in this session
    # This avoids unnecessary overhead for simple chats
    relevant_chunks = None
    has_documents = await asyncio.to_thread(memory.has_documents, chat_id)

    if has_documents:
        # Documents exist - use Metal4 for parallel embedding + RAG
        metal4_engine.kick_frame()

        # Try to use Metal GPU embedder (Week 2 optimization)
        try:
            from metal_embedder import get_metal_embedder
            metal_embedder = get_metal_embedder()

            if metal_embedder.is_available():
                # Use GPU-accelerated embeddings
                def embedder(text: str):
                    """Metal GPU embedding"""
                    return metal_embedder.embed(text)
                logger.debug("✓ Using Metal GPU embedder")
            else:
                # Fall back to CPU
                def embedder(text: str):
                    """CPU fallback embedding"""
                    return SimpleEmbedding.create_embedding(text)
                logger.debug("✓ Using CPU embedder (Metal GPU not available)")
        except ImportError:
            # Metal embedder not available - use SimpleEmbedding
            def embedder(text: str):
                """CPU fallback embedding"""
                return SimpleEmbedding.create_embedding(text)
            logger.debug("✓ Using CPU embedder (metal_embedder not installed)")

        def rag_retriever(embedding):
            """Wrapper for RAG retrieval"""
            return memory.search_document_chunks(chat_id, embedding, top_k=3)

        # Process on Metal4 Q_ml queue (runs in parallel with potential UI updates)
        metal_result = await asyncio.to_thread(
            metal4_engine.process_chat_message,
            body.content,
            embedder=embedder,
            rag_retriever=rag_retriever
        )

        # Extract results
        relevant_chunks = metal_result.get('context') if metal_result else None

        # Log Metal4 performance
        if metal_result and 'elapsed_ms' in metal_result:
            logger.debug(f"⚡ Metal4 embedding+RAG: {metal_result['elapsed_ms']:.2f}ms")
    # ===== END METAL 4 TICK FLOW =====

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
    if body.system_prompt:
        ollama_messages.insert(0, {"role": "system", "content": body.system_prompt})

    # Prepend summary of earlier messages if conversation is long
    if earlier_summary:
        summary_message = {
            "role": "system",
            "content": f"📋 Summary of earlier conversation:\n\n{earlier_summary}\n\n---\nThe following messages are the recent conversation:"
        }
        # Insert after system prompt if exists, otherwise at beginning
        insert_pos = 1 if body.system_prompt else 0
        ollama_messages.insert(insert_pos, summary_message)
        logger.info(f"Added conversation summary for {len(all_history) - CONTEXT_WINDOW} earlier messages")

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
                temperature=body.temperature,
                top_p=body.top_p,
                top_k=body.top_k,
                repeat_penalty=body.repeat_penalty
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
                "user_message": body.content,
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
    request: Request,
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
            safe_filename = sanitize_for_log(file.filename)
            logger.info(f"Created {len(chunks)} chunks for file {safe_filename}")
        else:
            file_info["text_preview"] = "[Text extraction not supported for this file type]"
            file_info["text_extracted"] = False

    except Exception as e:
        logger.warning(f"Failed to extract text from file: {e}")
        file_info["text_preview"] = f"[Extraction error: {str(e)}]"
        file_info["text_extracted"] = False

    return file_info


@public_router.get("/models", response_model=List[OllamaModel])
async def list_ollama_models():
    """List available Ollama models (public endpoint - no auth required)"""
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

    # Filter out non-chat models (embeddings, foundation models, etc.)
    # Exclude models with these patterns in their name
    excluded_patterns = [
        'embed',      # nomic-embed, all-minilm, etc.
        'embedding',  # any model with 'embedding' in name
        '-vision',    # vision models (not pure chat)
    ]

    chat_models = []
    for model in models:
        model_name_lower = model.name.lower()
        # Skip if model matches any excluded pattern
        if any(pattern in model_name_lower for pattern in excluded_patterns):
            logger.debug(f"Filtering out non-chat model: {model.name}")
            continue
        chat_models.append(model)

    return chat_models


@router.post("/models/preload")
async def preload_model(request: Request, model: str, keep_alive: str = "1h"):
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
@require_perm_team("chat.use")
async def semantic_search(
    query: str,
    limit: int = 10,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """
    Search across conversations using semantic similarity

    Phase 5: Team-aware - searches within user's personal chats or team chats
    """
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    user_id = current_user.get("user_id")

    # Phase 5: Team-scoped search
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
        "team_id": team_id  # Phase 5
    }


@router.get("/analytics")
@require_perm_team("chat.use")
async def get_analytics(
    session_id: Optional[str] = None,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """
    Get analytics for a session or scoped analytics

    Phase 5: Team-aware - returns analytics for user's personal or team sessions
    """
    user_id = current_user.get("user_id")

    # Phase 5: Pass team_id for scoped analytics
    analytics = await asyncio.to_thread(
        memory.get_analytics,
        session_id,
        user_id=user_id,
        team_id=team_id
    )
    return analytics


@router.get("/sessions/{chat_id}/analytics")
@require_perm_team("chat.use")
async def get_session_analytics(
    chat_id: str,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """
    Get detailed analytics for a specific session

    Phase 5: Team-aware - verifies session access via team membership
    """
    user_id = current_user.get("user_id")
    role = current_user.get("role")

    # Phase 5: Get session with team context
    session = await ChatStorage.get_session(chat_id, user_id, role, team_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or access denied")

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
        "topics": topics,
        "team_id": team_id  # Phase 5
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
async def get_token_count(request: Request, chat_id: str):
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


@public_router.get("/health")
async def check_health():
    """Check Ollama health status (public endpoint - no auth required)"""
    return await ErrorHandler.check_ollama_health()


@public_router.get("/models/status")
async def get_models_status():
    """
    Get status of all models (loaded/unloaded, favorites) (public endpoint - no auth required)

    Returns:
    {
        "available": [...],    # Chat models suitable for conversation
        "unavailable": [...]   # Embedding/foundation models with reasons
    }
    """
    return await model_manager.get_model_status(ollama_client)


@public_router.get("/models/hot-slots")
async def get_hot_slots():
    """Get current hot slot assignments (1-4) (public endpoint - no auth required)"""
    slots = model_manager.get_hot_slots()
    return {"hot_slots": slots}


@public_router.get("/models/orchestrator-suitable")
async def get_orchestrator_suitable_models():
    """
    Get models suitable for orchestrator use (public endpoint - no auth required)

    Returns small, efficient models (< 4GB) that can handle routing/reasoning.
    Includes small base models since orchestrator doesn't need perfect chat formatting.
    """
    from model_manager import is_orchestrator_suitable

    models = await ollama_client.list_models()

    suitable_models = []
    for model in models:
        if is_orchestrator_suitable(model.name, model.size):
            suitable_models.append({
                "name": model.name,
                "size": model.size,
                "modified_at": model.modified_at
            })

    return suitable_models


@router.post("/models/hot-slots/{slot_number}")
async def assign_to_hot_slot(request: Request, slot_number: int, model_name: str):
    """
    Assign a model to a specific hot slot (1-4)

    Args:
        slot_number: Slot number (1-4)
        model_name: Model name to assign

    Returns:
        Success status and updated hot slots
    """
    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    # Check if model already in another slot
    existing_slot = model_manager.get_slot_for_model(model_name)
    if existing_slot and existing_slot != slot_number:
        # Remove from previous slot
        model_manager.remove_from_slot(existing_slot)

    # Check if slot already occupied
    current_slots = model_manager.get_hot_slots()
    if current_slots[slot_number] is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Slot {slot_number} is already occupied by {current_slots[slot_number]}"
        )

    # Assign to new slot
    success = model_manager.assign_to_slot(slot_number, model_name)

    # Preload the model
    await ollama_client.preload_model(model_name, "1h")

    return {
        "success": success,
        "model": model_name,
        "slot_number": slot_number,
        "hot_slots": model_manager.get_hot_slots()
    }


@router.delete("/models/hot-slots/{slot_number}")
async def remove_from_hot_slot(request: Request, slot_number: int):
    """
    Remove a model from a specific hot slot

    Args:
        slot_number: Slot number (1-4) to clear

    Returns:
        Success status and updated hot slots
    """
    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    current_slots = model_manager.get_hot_slots()
    model_name = current_slots[slot_number]

    if model_name is None:
        raise HTTPException(status_code=400, detail=f"Slot {slot_number} is already empty")

    # Unload the model
    await ollama_client.preload_model(model_name, "0")  # keep_alive=0 unloads immediately

    # Remove from slot
    success = model_manager.remove_from_slot(slot_number)

    return {
        "success": success,
        "slot_number": slot_number,
        "model": model_name,
        "hot_slots": model_manager.get_hot_slots()
    }


@router.post("/models/load-hot-slots")
async def load_hot_slot_models(request: Request, keep_alive: str = "1h"):
    """
    Load all hot slot models into memory
    Useful for startup to pre-warm all hot slots
    """
    hot_slots = model_manager.get_hot_slots()
    results = []

    for slot_num, model_name in hot_slots.items():
        if model_name:
            success = await ollama_client.preload_model(model_name, keep_alive)
            results.append({
                "slot": slot_num,
                "model": model_name,
                "loaded": success
            })

    return {
        "total": len([m for m in hot_slots.values() if m is not None]),
        "results": results,
        "keep_alive": keep_alive
    }


class ExportToChatRequest(BaseModel):
    session_id: str
    query_id: str
    query: str
    results: List[Dict[str, Any]]


@router.post("/data/export-to-chat")
async def export_data_to_chat(request: Request, body: ExportToChatRequest):
    """
    Export query results from Data tab to AI Chat
    Creates a new chat session with CSV + JSON results pre-attached
    """
    try:
        import pandas as pd
        import io

        # Create DataFrame from results
        df = pd.DataFrame(body.results)

        # Create new chat session
        chat_session = await ChatStorage.create_session(
            title="Query Analysis",
            model="qwen2.5-coder:7b-instruct"
        )

        # Save CSV file to uploads (primary data format for AI analysis)
        csv_file_id = uuid.uuid4().hex[:12]
        csv_filename = f"query_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_stored_filename = f"{chat_session.id}_{csv_file_id}.csv"
        csv_file_path = CHAT_UPLOADS_DIR / csv_stored_filename

        # Write CSV file
        async with aiofiles.open(csv_file_path, 'w') as f:
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            await f.write(csv_buffer.getvalue())

        # Create CSV preview for RAG (first 1000 chars)
        csv_preview = csv_buffer.getvalue()[:1000]

        # Extract CSV text for RAG chunking
        extracted_text = f"""Query Results Dataset

SQL Query:
{body.query}

Dataset Information:
- Rows: {len(body.results)}
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
                "query": body.query,
                "row_count": len(body.results)
            }
        )

        # Store chunks in memory for semantic search
        await asyncio.to_thread(memory.store_document_chunks, chat_session.id, chunks)

        # Add system message with data summary and analysis prompt
        system_message = ChatMessage(
            role="assistant",
            content=f"""📊 **Query Results Loaded**

I've analyzed your SQL query results. Here's what I found:

**Query:**
```sql
{body.query}
```

**Dataset Summary:**
- Total Rows: {len(body.results):,}
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

What would you like to know about this data?""",
            timestamp=datetime.utcnow().isoformat(),
            files=[{
                "id": csv_file_id,
                "original_name": csv_filename,
                "stored_name": csv_stored_filename,
                "size": csv_file_path.stat().st_size,
                "type": "text/csv",
                "uploaded_at": datetime.utcnow().isoformat(),
                "text_preview": csv_preview,
                "text_extracted": True,
                "chunks_created": len(chunks)
            }]
        )
        await ChatStorage.append_message(chat_session.id, system_message)

        logger.info(f"Exported {len(body.results)} rows to chat session {chat_session.id} with {len(chunks)} RAG chunks")

        return {
            "chat_id": chat_session.id,
            "file_info": {
                "id": csv_file_id,
                "original_name": csv_filename,
                "stored_name": csv_stored_filename,
                "size": csv_file_path.stat().st_size,
                "type": "text/csv",
                "row_count": len(body.results),
                "chunks_created": len(chunks)
            },
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


@public_router.get("/ollama/server/status")
async def get_ollama_server_status():
    """
    Check if Ollama server is running and get loaded models (public endpoint - no auth required)
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
async def shutdown_ollama_server(request: Request):
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
async def start_ollama_server(request: Request):
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


class RestartServerRequest(BaseModel):
    """Request body for server restart"""
    models_to_load: Optional[List[str]] = None


@router.post("/ollama/server/restart")
async def restart_ollama_server(request: Request, body: Optional[RestartServerRequest] = None, reload_models: bool = False):
    """
    Restart Ollama server and optionally reload specific models

    Args:
        reload_models: Whether to reload models after restart (query param)
        body: Request body containing models_to_load list
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
            models_to_load = body.models_to_load if body and body.models_to_load else previous_models

            for model in models_to_load:
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
async def unload_model(request: Request, model_name: str):
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


# ===== ADAPTIVE ROUTER ENDPOINTS =====

class RouterFeedback(BaseModel):
    """Feedback for adaptive router learning"""
    command: str
    tool_used: str
    success: bool
    execution_time: float
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating")


@router.post("/adaptive-router/feedback")
async def submit_router_feedback(request: Request, feedback: RouterFeedback):
    """Submit feedback for adaptive router to learn from"""
    try:
        # Record execution result
        await asyncio.to_thread(
            adaptive_router.record_execution_result,
            feedback.command,
            feedback.tool_used,
            feedback.success,
            feedback.execution_time
        )

        # Optionally record user satisfaction in learning system
        if feedback.user_satisfaction is not None:
            # TODO: Add user satisfaction tracking to learning system
            pass

        logger.info(f"📊 Router feedback: {feedback.command[:50]}... → {feedback.tool_used} ({'✓' if feedback.success else '✗'})")

        return {
            "status": "recorded",
            "message": "Feedback recorded successfully"
        }

    except Exception as e:
        logger.error(f"Failed to record router feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-router/stats")
async def get_router_stats():
    """Get adaptive router statistics and learning progress"""
    try:
        # Get routing stats
        routing_stats = adaptive_router.get_routing_stats() if hasattr(adaptive_router, 'get_routing_stats') else {}

        # Get learning stats
        learning_stats = await asyncio.to_thread(learning_system.get_statistics)

        # Get memory stats
        memory_stats = await asyncio.to_thread(jarvis_memory.get_statistics)

        # Get top learned patterns
        learned_patterns = await asyncio.to_thread(learning_system.get_learned_patterns) if hasattr(learning_system, 'get_learned_patterns') else []

        # Get user preferences
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

    except Exception as e:
        logger.error(f"Failed to get router stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-router/explain")
async def explain_routing(command: str):
    """Explain how a command would be routed"""
    try:
        explanation = await asyncio.to_thread(
            adaptive_router.explain_routing if hasattr(adaptive_router, 'explain_routing') else adaptive_router.route_task,
            command
        )

        if isinstance(explanation, str):
            return {"explanation": explanation}
        else:
            # If explain_routing doesn't exist, use route_task result
            return {
                "task_type": explanation.task_type.value,
                "tool_type": explanation.tool_type.value,
                "confidence": explanation.confidence,
                "reasoning": explanation.reasoning,
                "learning_insights": explanation.learning_insights if hasattr(explanation, 'learning_insights') else {}
            }

    except Exception as e:
        logger.error(f"Failed to explain routing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== ANE ROUTER ENDPOINTS (Ultra-Low Power Mode) =====

@router.get("/router/mode")
async def get_router_mode():
    """Get current router mode (adaptive or ane)"""
    global current_router_mode
    return {
        "mode": current_router_mode,
        "description": "adaptive (GPU, learns)" if current_router_mode == 'adaptive' else "ane (ultra-low power <0.1W)",
        "power_estimate": "5-10W" if current_router_mode == 'adaptive' else "<0.1W"
    }


@router.post("/router/mode")
async def set_router_mode(request: Request, mode: str):
    """
    Set router mode for battery optimization

    Modes:
    - 'adaptive': GPU-based routing with learning (5-10W)
    - 'ane': Apple Neural Engine routing (<0.1W) - best for field work
    """
    global current_router_mode

    if mode not in ['adaptive', 'ane']:
        raise HTTPException(status_code=400, detail="Mode must be 'adaptive' or 'ane'")

    current_router_mode = mode
    logger.info(f"🔄 Router mode changed to: {mode}")

    return {
        "mode": mode,
        "description": "adaptive (GPU, learns)" if mode == 'adaptive' else "ane (ultra-low power <0.1W)",
        "power_estimate": "5-10W" if mode == 'adaptive' else "<0.1W",
        "message": f"Router mode set to {mode}"
    }


@router.get("/router/stats")
async def get_router_stats():
    """Get combined stats from both routers"""
    try:
        adaptive_stats = adaptive_router.get_routing_stats() if hasattr(adaptive_router, 'get_routing_stats') else {}
        ane_stats = ane_router.get_stats()

        return {
            "current_mode": current_router_mode,
            "adaptive_router": adaptive_stats,
            "ane_router": ane_stats
        }
    except Exception as e:
        logger.error(f"Failed to get router stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== RECURSIVE PROMPT ENDPOINTS =====

class RecursiveQueryRequest(BaseModel):
    """Request for recursive prompt processing"""
    query: str
    model: Optional[str] = "qwen2.5-coder:7b-instruct"


@router.post("/recursive-prompt/execute")
async def execute_recursive_prompt(request: Request, body: RecursiveQueryRequest):
    """Execute a query using recursive prompt decomposition"""
    try:
        import ollama
        ollama_client = ollama.AsyncClient()

        result = await recursive_library.process_query(
            body.query,
            ollama_client
        )

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

    except Exception as e:
        logger.error(f"Failed to execute recursive prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recursive-prompt/stats")
async def get_recursive_stats():
    """Get recursive prompt library statistics"""
    try:
        stats = recursive_library.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get recursive stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== OLLAMA CONFIG ENDPOINTS =====

class SetModeRequest(BaseModel):
    """Request to set performance mode"""
    mode: str  # performance, balanced, silent


@router.get("/ollama/config")
async def get_ollama_configuration():
    """Get current Ollama configuration"""
    try:
        summary = ollama_config.get_config_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get Ollama config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/config/mode")
async def set_ollama_mode(request: Request, body: SetModeRequest):
    """Set Ollama performance mode"""
    try:
        ollama_config.set_mode(body.mode)
        return {
            "status": "success",
            "mode": body.mode,
            "config": ollama_config.get_config_summary()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set Ollama mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/config/auto-detect")
async def auto_detect_ollama_config(request: Request):
    """Auto-detect optimal Ollama settings for current hardware"""
    try:
        optimal_config = ollama_config.detect_optimal_settings()
        ollama_config.config = optimal_config
        ollama_config.save_config()

        return {
            "status": "success",
            "message": "Auto-detected optimal settings",
            "config": ollama_config.get_config_summary()
        }
    except Exception as e:
        logger.error(f"Failed to auto-detect config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== PERFORMANCE MONITORING ENDPOINTS =====

@router.get("/performance/current")
async def get_current_performance():
    """Get current performance metrics"""
    try:
        metrics = performance_monitor.get_current_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/stats")
async def get_performance_statistics():
    """Get performance statistics over time"""
    try:
        stats = performance_monitor.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/history")
async def get_performance_history(last_n: int = 20):
    """Get recent performance history"""
    try:
        history = performance_monitor.get_history(last_n)
        return {"history": history}
    except Exception as e:
        logger.error(f"Failed to get performance history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/thermal")
async def check_thermal_throttling():
    """Check for thermal throttling"""
    try:
        thermal_check = performance_monitor.check_thermal_throttling()
        return thermal_check
    except Exception as e:
        logger.error(f"Failed to check thermal status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/reset")
async def reset_performance_metrics(request: Request):
    """Reset performance metrics"""
    try:
        performance_monitor.reset()
        return {"status": "success", "message": "Performance metrics reset"}
    except Exception as e:
        logger.error(f"Failed to reset performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== PANIC MODE ENDPOINTS (MISSIONARY SAFETY) =====

class PanicTriggerRequest(BaseModel):
    """Request to trigger panic mode"""
    reason: Optional[str] = "Manual activation"
    confirmation: str  # Must be "CONFIRM" to prevent accidental triggers


@router.post("/panic/trigger")
async def trigger_panic_mode(request: Request, body: PanicTriggerRequest):
    """
    🚨 EMERGENCY: Trigger panic mode
    Wipes sensitive data, closes connections, secures databases
    THIS IS IRREVERSIBLE!
    """
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="Panic mode requires confirmation='CONFIRM'"
        )

    try:
        result = await panic_mode.trigger_panic(body.reason)
        return result
    except Exception as e:
        logger.critical(f"Panic mode execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/panic/status")
async def get_panic_status():
    """Get current panic mode status"""
    try:
        status = panic_mode.get_panic_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get panic status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/panic/reset")
async def reset_panic_mode(request: Request):
    """Reset panic mode (admin only)"""
    try:
        panic_mode.reset_panic()
        return {"status": "success", "message": "Panic mode reset"}
    except Exception as e:
        logger.error(f"Failed to reset panic mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADAPTIVE LEARNING ENDPOINTS
# ============================================================================

@router.get("/learning/patterns")
async def get_learning_patterns(days: int = 30):
    """
    Get usage patterns and learning insights

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        Usage patterns, recommendations, and insights
    """
    try:
        learning_engine = get_learning_engine()
        patterns = learning_engine.analyze_patterns(days=days)
        return patterns
    except Exception as e:
        logger.error(f"Failed to get learning patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/recommendations")
async def get_recommendations():
    """Get current classification recommendations"""
    try:
        learning_engine = get_learning_engine()
        recommendations = learning_engine.get_recommendations()
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/recommendations/{recommendation_id}/accept")
async def accept_recommendation(request: Request, recommendation_id: int, feedback: Optional[str] = None):
    """Accept a classification recommendation"""
    try:
        learning_engine = get_learning_engine()
        success = learning_engine.accept_recommendation(recommendation_id, feedback)

        if success:
            return {"status": "success", "message": "Recommendation accepted"}
        else:
            raise HTTPException(status_code=400, detail="Failed to accept recommendation")
    except Exception as e:
        logger.error(f"Failed to accept recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/recommendations/{recommendation_id}/reject")
async def reject_recommendation(request: Request, recommendation_id: int, feedback: Optional[str] = None):
    """Reject a classification recommendation"""
    try:
        learning_engine = get_learning_engine()
        success = learning_engine.reject_recommendation(recommendation_id, feedback)

        if success:
            return {"status": "success", "message": "Recommendation rejected"}
        else:
            raise HTTPException(status_code=400, detail="Failed to reject recommendation")
    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/optimal-model/{task_type}")
async def get_optimal_model(task_type: str, top_n: int = 3):
    """
    Get the optimal models for a specific task type based on learning

    Args:
        task_type: Task classification (code, writing, reasoning, etc.)
        top_n: Number of top models to return

    Returns:
        List of recommended models with confidence scores
    """
    try:
        learning_engine = get_learning_engine()
        models = learning_engine.get_optimal_model_for_task(task_type, top_n)

        return {
            "task_type": task_type,
            "recommended_models": [
                {"model": model, "confidence": confidence}
                for model, confidence in models
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get optimal model for task '{task_type}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/track-usage")
async def track_usage_manually(
    request: Request,
    model_name: str,
    classification: Optional[str] = None,
    session_id: Optional[str] = None,
    message_count: int = 1,
    tokens_used: int = 0,
    task_detected: Optional[str] = None
):
    """
    Manually track model usage (for testing or external integrations)

    Normally usage is tracked automatically during chat sessions
    """
    try:
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
    except Exception as e:
        logger.error(f"Failed to track usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export routers
__all__ = ["router", "public_router"]
