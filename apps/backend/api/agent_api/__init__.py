"""
Agent API for MagnetarCode

Provides endpoints for autonomous agent execution:
- POST /api/v1/agent/execute - Execute a task with agent
- GET /api/v1/agent/status/{task_id} - Get task status
- POST /api/v1/agent/approve/{task_id} - Approve pending task
- POST /api/v1/agent/cancel/{task_id} - Cancel running task

Advanced Features:
- POST /api/v1/agent/multi/execute - Multi-agent collaborative execution
- GET /api/v1/agent/metrics/{agent_role} - Get agent performance metrics
- POST /api/v1/agent/feedback - Submit feedback on task execution
- GET /api/v1/agent/agents - List available agent types
- POST /api/v1/agent/tools/custom - Register custom tool
- GET /api/v1/agent/tools/custom - List custom tools
- DELETE /api/v1/agent/tools/custom/{tool_name} - Unregister custom tool

This module exports the router for integration with main.py.
"""

from .endpoints import (
    agent_health,
    cancel_agent_task,
    execute_agent_task,
    execute_custom_tool,
    execute_multi_agent,
    get_agent_metrics,
    get_agent_status,
    list_agent_tools,
    list_agents,
    list_custom_tools,
    register_custom_tool,
    router,
    submit_feedback,
    unregister_custom_tool,
)
from .models import (
    AgentStatusResponse,
    AgentTaskRequest,
    CustomToolRequest,
    FeedbackRequest,
    MultiAgentRequest,
)
from .state import (
    get_active_agent,
    get_active_agents_count,
    remove_active_agent,
    store_active_agent,
)

__all__ = [
    # Router (CRITICAL: main.py imports this)
    "router",
    # Core endpoints
    "execute_agent_task",
    "get_agent_status",
    "cancel_agent_task",
    "list_agent_tools",
    "agent_health",
    # Advanced endpoints
    "execute_multi_agent",
    "list_agents",
    "get_agent_metrics",
    "submit_feedback",
    # Custom tools endpoints
    "register_custom_tool",
    "list_custom_tools",
    "unregister_custom_tool",
    "execute_custom_tool",
    # Models
    "AgentTaskRequest",
    "AgentStatusResponse",
    "MultiAgentRequest",
    "FeedbackRequest",
    "CustomToolRequest",
    # State management
    "get_active_agent",
    "store_active_agent",
    "remove_active_agent",
    "get_active_agents_count",
]
