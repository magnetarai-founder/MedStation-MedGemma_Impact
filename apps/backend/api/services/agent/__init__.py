"""
Agent Execution System for MagnetarCode

Autonomous agents that can:
- Plan multi-step tasks
- Execute code changes
- Run commands
- Verify results
- Iterate until task is complete

Agent Types:
- CodeAgent: Code implementation and refactoring
- TestAgent: Testing and validation
- DebugAgent: Bug finding and fixing
- ReviewAgent: Code review and quality checks
- ResearchAgent: Documentation and research
- SecurityAgent: Security analysis and hardening
- PerformanceAgent: Performance optimization and profiling
- ArchitectureAgent: System design and structural analysis
"""

from .agent_types import (
    AGENT_PROFILES,
    ARCHITECTURE_AGENT_PROFILE,
    CODE_AGENT_PROFILE,
    DEBUG_AGENT_PROFILE,
    PERFORMANCE_AGENT_PROFILE,
    RESEARCH_AGENT_PROFILE,
    REVIEW_AGENT_PROFILE,
    SECURITY_AGENT_PROFILE,
    TEST_AGENT_PROFILE,
    AgentCapability,
    AgentProfile,
    AgentRole,
    get_agent_for_capability,
    get_agent_profile,
    get_collaborative_agents,
    select_best_agent,
)
from .async_tools import (
    AsyncToolExecutor,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolPipeline,
    get_async_tool_executor,
)
from .executor import AgentExecutor
from .planner import TaskPlanner
from .tools import Tool, ToolRegistry

__all__ = [
    # Executor and Planner
    "AgentExecutor",
    "TaskPlanner",
    # Sync Tools
    "Tool",
    "ToolRegistry",
    # Async Tools
    "AsyncToolExecutor",
    "ToolExecutionContext",
    "ToolExecutionResult",
    "ToolPipeline",
    "get_async_tool_executor",
    # Agent Types
    "AgentRole",
    "AgentCapability",
    "AgentProfile",
    "AGENT_PROFILES",
    "CODE_AGENT_PROFILE",
    "TEST_AGENT_PROFILE",
    "DEBUG_AGENT_PROFILE",
    "REVIEW_AGENT_PROFILE",
    "RESEARCH_AGENT_PROFILE",
    "SECURITY_AGENT_PROFILE",
    "PERFORMANCE_AGENT_PROFILE",
    "ARCHITECTURE_AGENT_PROFILE",
    # Agent Selection
    "get_agent_profile",
    "select_best_agent",
    "get_collaborative_agents",
    "get_agent_for_capability",
]
