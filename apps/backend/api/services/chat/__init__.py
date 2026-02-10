"""
Chat Service Package

Modular chat service for MedStation with session management,
message handling, file uploads, model management, and analytics.

Public API for routes:
    from api.services.chat import create_session, get_session, send_message_stream, etc.
    from api.services.chat import get_ollama_client (legacy compatibility)
"""

# Re-export OllamaClient from streaming for backwards compatibility
from .streaming import OllamaClient

# Re-export all core functions (session, message, file, model, etc.)
from .core import (
    # Session Management
    create_session,
    get_session,
    list_sessions,
    delete_session,
    update_session_model,
    update_session_title,
    set_session_archived,

    # Message Management
    append_message,
    get_messages,
    send_message_stream,

    # File Management
    upload_file_to_chat,

    # Model Management
    list_ollama_models,
    preload_model,
    unload_model,
    get_models_status,
    get_orchestrator_suitable_models,

    # Search & Analytics
    semantic_search,
    get_analytics,
    get_session_analytics,

    # ANE Context
    get_ane_stats,
    search_ane_context,

    # Embedding Info
    get_embedding_info,

    # Token Counting
    get_token_count,

    # Health & Status
    check_health,
    get_ollama_server_status,

    # System Management
    get_system_memory,
    shutdown_ollama_server,
    start_ollama_server,
    restart_ollama_server,

    # Data Export
    export_data_to_chat,

    # Model Hot Slots
    get_hot_slots,
    assign_to_hot_slot,
    remove_from_hot_slot,
    load_hot_slot_models,

    # Adaptive Router
    submit_router_feedback,
    get_router_stats,
    explain_routing,

    # Router Mode
    get_router_mode,
    set_router_mode,
    get_combined_router_stats,

    # Recursive Prompting
    execute_recursive_prompt,
    get_recursive_stats,

    # Ollama Configuration
    get_ollama_configuration,
    set_ollama_mode,
    auto_detect_ollama_config,

    # Performance Monitoring
    get_current_performance,
    get_performance_statistics,
    get_performance_history,
    check_thermal_throttling,
    reset_performance_metrics,

    # Panic Mode
    trigger_panic_mode,
    get_panic_status,
    reset_panic_mode,

    # Learning System
    get_learning_patterns,
    get_recommendations,
    accept_recommendation,
    reject_recommendation,
    get_optimal_model_for_task,
    track_usage_manually,
)

# Legacy compatibility: provide get_ollama_client function
def get_ollama_client() -> "OllamaClient":
    """
    Get OllamaClient instance (LEGACY)

    For backwards compatibility with existing code that uses:
        from api.services.chat import get_ollama_client

    Returns singleton OllamaClient instance.
    """
    from .core import _get_ollama_client
    return _get_ollama_client()


__all__ = [
    # Classes
    "OllamaClient",

    # Legacy function
    "get_ollama_client",

    # Session Management
    "create_session",
    "get_session",
    "list_sessions",
    "delete_session",
    "update_session_model",
    "update_session_title",
    "set_session_archived",

    # Message Management
    "append_message",
    "get_messages",
    "send_message_stream",

    # File Management
    "upload_file_to_chat",

    # Model Management
    "list_ollama_models",
    "preload_model",
    "unload_model",
    "get_models_status",
    "get_orchestrator_suitable_models",

    # Search & Analytics
    "semantic_search",
    "get_analytics",
    "get_session_analytics",

    # ANE Context
    "get_ane_stats",
    "search_ane_context",

    # Embedding Info
    "get_embedding_info",

    # Token Counting
    "get_token_count",

    # Health & Status
    "check_health",
    "get_ollama_server_status",

    # System Management
    "get_system_memory",
    "shutdown_ollama_server",
    "start_ollama_server",
    "restart_ollama_server",

    # Data Export
    "export_data_to_chat",

    # Model Hot Slots
    "get_hot_slots",
    "assign_to_hot_slot",
    "remove_from_hot_slot",
    "load_hot_slot_models",

    # Adaptive Router
    "submit_router_feedback",
    "get_router_stats",
    "explain_routing",

    # Router Mode
    "get_router_mode",
    "set_router_mode",
    "get_combined_router_stats",

    # Recursive Prompting
    "execute_recursive_prompt",
    "get_recursive_stats",

    # Ollama Configuration
    "get_ollama_configuration",
    "set_ollama_mode",
    "auto_detect_ollama_config",

    # Performance Monitoring
    "get_current_performance",
    "get_performance_statistics",
    "get_performance_history",
    "check_thermal_throttling",
    "reset_performance_metrics",

    # Panic Mode
    "trigger_panic_mode",
    "get_panic_status",
    "reset_panic_mode",

    # Learning System
    "get_learning_patterns",
    "get_recommendations",
    "accept_recommendation",
    "reject_recommendation",
    "get_optimal_model_for_task",
    "track_usage_manually",
]
