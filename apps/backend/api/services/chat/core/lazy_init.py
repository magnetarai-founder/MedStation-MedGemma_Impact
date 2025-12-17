"""
Chat service - Lazy initialization helpers.

All heavy dependencies are imported and initialized inside function bodies
to avoid circular dependencies and reduce startup time.
"""

import logging
from pathlib import Path

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
        from ..streaming import OllamaClient
        _ollama_client = OllamaClient()
    return _ollama_client


def _get_chat_uploads_dir():
    """Get chat uploads directory"""
    from config_paths import get_config_paths
    uploads_dir = get_config_paths().uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir
