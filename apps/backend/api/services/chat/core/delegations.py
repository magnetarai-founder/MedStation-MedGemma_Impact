"""
Chat service - Delegation wrappers.

Functions that delegate to other chat service modules:
- Sessions (sessions.py)
- Models (models.py)
- Hot slots (hot_slots.py)
- Analytics (analytics.py)
- System (system.py)
- Ollama operations (ollama_ops.py)
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ===== Session Management (delegated to sessions.py) =====

async def create_session(title: str, model: str, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new chat session"""
    from .. import sessions as sessions_mod
    return await sessions_mod.create_new_session(title, model, user_id, team_id)


async def get_session(chat_id: str, user_id: str, role: str = None, team_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get session by ID (user-filtered unless Founder Rights)"""
    from .. import sessions as sessions_mod
    return await sessions_mod.get_session_by_id(chat_id, user_id, role, team_id)


async def list_sessions(user_id: str, role: str = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all chat sessions for user (Founder Rights sees all)"""
    from .. import sessions as sessions_mod
    return await sessions_mod.list_user_sessions(user_id, role, team_id)


async def delete_session(chat_id: str, user_id: str, role: str = None) -> bool:
    """Delete a chat session (user-filtered unless Founder Rights)"""
    from .. import sessions as sessions_mod
    return await sessions_mod.delete_session_by_id(chat_id, user_id, role)


# ===== Model Management (delegated to models.py) =====

async def list_ollama_models() -> List[Dict[str, Any]]:
    """List available Ollama models"""
    from .. import models as models_mod
    return await models_mod.list_ollama_models()


async def preload_model(model: str, keep_alive: str = "1h", source: str = "unknown") -> bool:
    """Pre-load a model into memory"""
    from .. import models as models_mod
    return await models_mod.preload_model(model, keep_alive, source)


async def unload_model(model_name: str) -> bool:
    """Unload a specific model from memory"""
    from .. import models as models_mod
    return await models_mod.unload_model(model_name)


async def get_models_status() -> Dict[str, Any]:
    """Get status of all models"""
    from .. import models as models_mod
    return await models_mod.get_models_status()


async def get_orchestrator_suitable_models() -> List[Dict[str, Any]]:
    """Get models suitable for orchestrator use"""
    from .. import models as models_mod
    return await models_mod.get_orchestrator_suitable_models()


# ===== Hot Slots (delegated to hot_slots.py) =====

async def get_hot_slots() -> Dict[int, Optional[str]]:
    """Get current hot slot assignments"""
    from .. import hot_slots as hot_slots_mod
    return await hot_slots_mod.get_hot_slots()


async def assign_to_hot_slot(slot_number: int, model_name: str) -> Dict[str, Any]:
    """Assign a model to a specific hot slot"""
    from .. import hot_slots as hot_slots_mod
    return await hot_slots_mod.assign_to_hot_slot(slot_number, model_name)


async def remove_from_hot_slot(slot_number: int) -> Dict[str, Any]:
    """Remove a model from a specific hot slot"""
    from .. import hot_slots as hot_slots_mod
    return await hot_slots_mod.remove_from_hot_slot(slot_number)


async def load_hot_slot_models(keep_alive: str = "1h") -> Dict[str, Any]:
    """Load all hot slot models into memory"""
    from .. import hot_slots as hot_slots_mod
    return await hot_slots_mod.load_hot_slot_models(keep_alive)


# ===== Search & Analytics (delegated to analytics.py) =====

async def semantic_search(query: str, limit: int, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Search across conversations using semantic similarity"""
    from .. import analytics as analytics_mod
    return await analytics_mod.semantic_search(query, limit, user_id, team_id)


async def get_analytics(session_id: Optional[str], user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Get analytics for a session or scoped analytics"""
    from .. import analytics as analytics_mod
    return await analytics_mod.get_analytics(session_id, user_id, team_id)


async def get_session_analytics(chat_id: str) -> Dict[str, Any]:
    """Get detailed analytics for a specific session"""
    from .. import analytics as analytics_mod
    return await analytics_mod.get_session_analytics(chat_id)


# ===== System operations (delegated to system.py) =====

async def get_ane_stats() -> Dict[str, Any]:
    """Get Apple Neural Engine context stats"""
    from .. import system as system_mod
    return await system_mod.get_ane_stats()


async def search_ane_context(query: str, top_k: int = 5, threshold: float = 0.5) -> Dict[str, Any]:
    """Search for similar chat contexts using ANE-accelerated embeddings"""
    from .. import system as system_mod
    return await system_mod.search_ane_context(query, top_k, threshold)


async def get_embedding_info() -> Dict[str, Any]:
    """Get information about the embedding backend"""
    from .. import system as system_mod
    return await system_mod.get_embedding_info()


async def get_token_count(chat_id: str) -> Dict[str, Any]:
    """Get token count for a chat session"""
    from .. import system as system_mod
    return await system_mod.get_token_count(chat_id)


# ===== Ollama server operations (delegated to ollama_ops.py) =====

async def get_ollama_server_status() -> Dict[str, Any]:
    """Check if Ollama server is running"""
    from .. import ollama_ops as ollama_ops_mod
    return await ollama_ops_mod.get_ollama_server_status()


async def shutdown_ollama_server() -> Dict[str, Any]:
    """Shutdown Ollama server"""
    from .. import ollama_ops as ollama_ops_mod
    return await ollama_ops_mod.shutdown_ollama_server()


async def start_ollama_server() -> Dict[str, Any]:
    """Start Ollama server in background"""
    from .. import ollama_ops as ollama_ops_mod
    return await ollama_ops_mod.start_ollama_server()


async def restart_ollama_server(reload_models: bool = False, models_to_load: Optional[List[str]] = None) -> Dict[str, Any]:
    """Restart Ollama server and optionally reload specific models"""
    from .. import ollama_ops as ollama_ops_mod
    return await ollama_ops_mod.restart_ollama_server(reload_models, models_to_load)


def get_ollama_configuration() -> Dict[str, Any]:
    """Get current Ollama configuration"""
    from .. import ollama_ops as ollama_ops_mod
    return ollama_ops_mod.get_ollama_configuration()


def set_ollama_mode(mode: str) -> Dict[str, Any]:
    """Set Ollama performance mode"""
    from .. import ollama_ops as ollama_ops_mod
    return ollama_ops_mod.set_ollama_mode(mode)


def auto_detect_ollama_config() -> Dict[str, Any]:
    """Auto-detect optimal Ollama settings"""
    from .. import ollama_ops as ollama_ops_mod
    return ollama_ops_mod.auto_detect_ollama_config()
