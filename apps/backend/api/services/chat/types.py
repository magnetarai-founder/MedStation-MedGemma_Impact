"""
Chat Service Type Definitions

Centralized type definitions, enums, and type aliases for the chat service.
Phase 2.3a - Foundation module.
"""

from typing import Dict, List, Optional, Any, TypedDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class RouterMode(str, Enum):
    """Router mode for task routing"""
    ADAPTIVE = "adaptive"
    ANE = "ane"
    HYBRID = "hybrid"


class MessageRole(str, Enum):
    """Message roles in chat conversations"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============================================================================
# TYPE ALIASES
# ============================================================================

# Session data structure
SessionDict = Dict[str, Any]

# Message data structure
MessageDict = Dict[str, Any]

# Model information
ModelDict = Dict[str, Any]

# Analytics data
AnalyticsDict = Dict[str, Any]

# Hot slot mapping
HotSlotDict = Dict[int, Optional[str]]


# ============================================================================
# TYPED DICTS (for structured return values)
# ============================================================================

class SessionResponse(TypedDict):
    """Response structure for session operations"""
    chat_id: str
    title: str
    model: str
    user_id: str
    team_id: Optional[str]
    created_at: str
    updated_at: str
    archived: bool


class MessageResponse(TypedDict):
    """Response structure for message operations"""
    role: str
    content: str
    timestamp: str
    model: Optional[str]
    tokens: Optional[int]


class SearchResult(TypedDict):
    """Semantic search result structure"""
    results: List[MessageDict]
    query: str
    limit: int


class FileUploadResult(TypedDict):
    """File upload result structure"""
    success: bool
    filename: str
    size: int
    chunks_stored: int


class HealthStatus(TypedDict):
    """Health check status structure"""
    status: str
    ollama_available: bool
    memory_available: bool
    timestamp: str


# ============================================================================
# CONSTANTS
# ============================================================================

# Default values
DEFAULT_MODEL = "llama3.2:latest"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 40
DEFAULT_REPEAT_PENALTY = 1.1

# Context window management
MAX_CONTEXT_MESSAGES = 75

# Hot slot configuration
HOT_SLOT_COUNT = 3

# File upload limits
MAX_FILE_SIZE_MB = 50
ALLOWED_FILE_TYPES = {
    'text/plain',
    'text/markdown',
    'application/pdf',
    'application/json',
    'text/csv'
}
