"""
Chat service - Router operations.

Handles:
- Router mode (ANE vs Adaptive)
- Router statistics
- Router feedback
- Routing explanations
- Recursive prompt execution
"""

import logging
from typing import Dict, Any, Optional

from .lazy_init import (
    _get_adaptive_router,
    _get_ane_router,
    _get_recursive_library
)
from .messages import current_router_mode

logger = logging.getLogger(__name__)


async def submit_router_feedback(command: str, tool_used: str, success: bool, execution_time: float, user_satisfaction: Optional[int] = None):
    """Submit feedback for adaptive router to learn from"""
    from .. import system as system_mod
    return await system_mod.submit_router_feedback(command, tool_used, success, execution_time, user_satisfaction)


async def get_router_stats() -> Dict[str, Any]:
    """Get adaptive router statistics"""
    from .. import system as system_mod
    return await system_mod.get_router_stats()


async def explain_routing(command: str) -> Dict[str, Any]:
    """Explain how a command would be routed"""
    from .. import system as system_mod
    return await system_mod.explain_routing(command)


def get_router_mode() -> Dict[str, Any]:
    """Get current router mode"""
    from .. import system as system_mod
    return system_mod.get_router_mode()


def set_router_mode(mode: str) -> Dict[str, Any]:
    """Set router mode"""
    from .. import system as system_mod
    return system_mod.set_router_mode(mode)


async def get_combined_router_stats() -> Dict[str, Any]:
    """Get combined stats from both routers"""
    adaptive_router = _get_adaptive_router()
    ane_router = _get_ane_router()

    adaptive_stats = adaptive_router.get_routing_stats() if hasattr(adaptive_router, 'get_routing_stats') else {}
    ane_stats = ane_router.get_stats()

    return {
        "current_mode": current_router_mode,
        "adaptive_router": adaptive_stats,
        "ane_router": ane_stats
    }


async def execute_recursive_prompt(query: str, model: Optional[str] = "qwen2.5-coder:7b-instruct") -> Dict[str, Any]:
    """Execute a query using recursive prompt decomposition"""
    import ollama

    recursive_library = _get_recursive_library()
    ollama_client_lib = ollama.AsyncClient()

    result = await recursive_library.process_query(query, ollama_client_lib)

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


async def get_recursive_stats() -> Dict[str, Any]:
    """Get recursive prompt library statistics"""
    recursive_library = _get_recursive_library()
    stats = recursive_library.get_stats()
    return stats
