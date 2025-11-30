"""
Chat-related Pydantic models for ElohimOS API.

Extracted from chat_service.py for service layer pattern migration.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ===== Core Chat Models =====

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: str
    files: List[Dict[str, Any]] = Field(default_factory=list)
    model: Optional[str] = None
    tokens: Optional[int] = None


class ChatSession(BaseModel):
    """Chat session model"""
    id: str
    title: str
    created_at: str
    updated_at: str
    model: str = "qwen2.5-coder:7b-instruct"
    message_count: int = 0


class CreateChatRequest(BaseModel):
    """Request to create a new chat session"""
    title: Optional[str] = "New Chat"
    model: Optional[str] = "qwen2.5-coder:7b-instruct"


class SendMessageRequest(BaseModel):
    """Request to send a message in chat"""
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


# ===== Model Management =====

class OllamaModel(BaseModel):
    """Ollama model information"""
    name: str
    size: int
    modified_at: str


# ===== Data Export =====

class ExportToChatRequest(BaseModel):
    """Request to export data to chat"""
    session_id: str
    query_id: str
    query: str
    results: List[Dict[str, Any]]


# ===== System Management =====

class RestartServerRequest(BaseModel):
    """Request body for server restart"""
    models_to_load: Optional[List[str]] = None


# ===== Adaptive Router =====

class RouterFeedback(BaseModel):
    """Feedback for adaptive router learning"""
    command: str
    tool_used: str
    success: bool
    execution_time: float
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating")


# ===== Recursive Prompting =====

class RecursiveQueryRequest(BaseModel):
    """Request for recursive prompt processing"""
    query: str
    model: Optional[str] = "qwen2.5-coder:7b-instruct"


# ===== Ollama Configuration =====

class SetModeRequest(BaseModel):
    """Request to set performance mode"""
    mode: str  # performance, balanced, silent


# ===== Panic Mode =====

class PanicTriggerRequest(BaseModel):
    """Request to trigger panic mode"""
    reason: Optional[str] = "Manual activation"
    confirmation: str  # Must be "CONFIRM" to prevent accidental triggers
