"""
Global state management for Agent API

Manages active agent instances. In production, this should use Redis or a database.
"""

from ..services.agent import AgentExecutor

# Global state for active agents
# In production, use Redis or database
_active_agents: dict[str, AgentExecutor] = {}


def get_active_agent(task_id: str) -> AgentExecutor | None:
    """Get an active agent by task ID"""
    return _active_agents.get(task_id)


def store_active_agent(task_id: str, agent: AgentExecutor) -> None:
    """Store an active agent"""
    _active_agents[task_id] = agent


def remove_active_agent(task_id: str) -> None:
    """Remove an active agent"""
    _active_agents.pop(task_id, None)


def get_active_agents_count() -> int:
    """Get count of active agents"""
    return len(_active_agents)
