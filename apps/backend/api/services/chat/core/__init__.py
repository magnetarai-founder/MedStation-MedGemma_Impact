"""
Chat Service Core Module

This module combines all chat service functionality into focused sub-modules:
- lazy_init: Lazy initialization helpers for all dependencies
- messages: Message operations (append, get, stream)
- files: File upload and RAG integration
- session_ops: Session operations (update model/title, archive, export)
- health: Health checks and system status
- router_ops: Router mode, stats, feedback, recursive prompts
- performance: Performance monitoring and panic mode
- learning: Learning system operations
- delegations: Delegation wrappers for other chat modules

The original 1,255-line core.py has been refactored into focused modules
for better maintainability and code organization.

Follows MedStation API standards (see API_STANDARDS.md).
"""

# Import all functions from sub-modules
from .lazy_init import (
    _get_memory,
    _get_ane_engine,
    _get_token_counter,
    _get_model_manager,
    _get_metal4_engine,
    _get_adaptive_router,
    _get_ane_router,
    _get_recursive_library,
    _get_ollama_config,
    _get_performance_monitor,
    _get_panic_mode,
    _get_ollama_client,
    _get_chat_uploads_dir
)

from .messages import (
    append_message,
    get_messages,
    send_message_stream,
    current_router_mode
)

from .files import (
    upload_file_to_chat
)

from .session_ops import (
    update_session_model,
    update_session_title,
    set_session_archived,
    export_data_to_chat
)

from .health import (
    check_health,
    get_system_memory
)

from .router_ops import (
    submit_router_feedback,
    get_router_stats,
    explain_routing,
    get_router_mode,
    set_router_mode,
    get_combined_router_stats,
    execute_recursive_prompt,
    get_recursive_stats
)

from .performance import (
    get_current_performance,
    get_performance_statistics,
    get_performance_history,
    check_thermal_throttling,
    reset_performance_metrics,
    trigger_panic_mode,
    get_panic_status,
    reset_panic_mode
)

from .learning import (
    get_learning_patterns,
    get_recommendations,
    accept_recommendation,
    reject_recommendation,
    get_optimal_model_for_task,
    track_usage_manually
)

from .delegations import (
    create_session,
    get_session,
    list_sessions,
    delete_session,
    list_ollama_models,
    preload_model,
    unload_model,
    get_models_status,
    get_orchestrator_suitable_models,
    get_hot_slots,
    assign_to_hot_slot,
    remove_from_hot_slot,
    load_hot_slot_models,
    semantic_search,
    get_analytics,
    get_session_analytics,
    get_ane_stats,
    search_ane_context,
    get_embedding_info,
    get_token_count,
    get_ollama_server_status,
    shutdown_ollama_server,
    start_ollama_server,
    restart_ollama_server,
    get_ollama_configuration,
    set_ollama_mode,
    auto_detect_ollama_config
)

__all__ = [
    # Lazy initialization
    "_get_memory",
    "_get_ane_engine",
    "_get_token_counter",
    "_get_model_manager",
    "_get_metal4_engine",
    "_get_adaptive_router",
    "_get_ane_router",
    "_get_recursive_library",
    "_get_ollama_config",
    "_get_performance_monitor",
    "_get_panic_mode",
    "_get_ollama_client",
    "_get_chat_uploads_dir",

    # Messages
    "append_message",
    "get_messages",
    "send_message_stream",
    "current_router_mode",

    # Files
    "upload_file_to_chat",

    # Session operations
    "update_session_model",
    "update_session_title",
    "set_session_archived",
    "export_data_to_chat",

    # Health
    "check_health",
    "get_system_memory",

    # Router operations
    "submit_router_feedback",
    "get_router_stats",
    "explain_routing",
    "get_router_mode",
    "set_router_mode",
    "get_combined_router_stats",
    "execute_recursive_prompt",
    "get_recursive_stats",

    # Performance
    "get_current_performance",
    "get_performance_statistics",
    "get_performance_history",
    "check_thermal_throttling",
    "reset_performance_metrics",
    "trigger_panic_mode",
    "get_panic_status",
    "reset_panic_mode",

    # Learning
    "get_learning_patterns",
    "get_recommendations",
    "accept_recommendation",
    "reject_recommendation",
    "get_optimal_model_for_task",
    "track_usage_manually",

    # Delegations
    "create_session",
    "get_session",
    "list_sessions",
    "delete_session",
    "list_ollama_models",
    "preload_model",
    "unload_model",
    "get_models_status",
    "get_orchestrator_suitable_models",
    "get_hot_slots",
    "assign_to_hot_slot",
    "remove_from_hot_slot",
    "load_hot_slot_models",
    "semantic_search",
    "get_analytics",
    "get_session_analytics",
    "get_ane_stats",
    "search_ane_context",
    "get_embedding_info",
    "get_token_count",
    "get_ollama_server_status",
    "shutdown_ollama_server",
    "start_ollama_server",
    "restart_ollama_server",
    "get_ollama_configuration",
    "set_ollama_mode",
    "auto_detect_ollama_config",
]
