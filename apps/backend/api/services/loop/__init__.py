"""
Agentic Loop System

Implements the Execute → Observe → Reflect → Decide loop for autonomous agents.
Enables self-correction and learning from execution outcomes.

Usage:
    from api.services.loop import AgenticExecutor, LoopState

    executor = AgenticExecutor(tool_registry, llm_client)

    async for event in executor.execute(task_tree):
        if event["type"] == "reflection":
            print(f"Agent reflection: {event['data']['assessment']}")
        elif event["type"] == "decision":
            print(f"Next action: {event['data']['decision_type']}")
        elif event["type"] == "ask_user":
            user_input = input(event["data"]["question"])
            # Resume with user input

    # Check final state
    print(f"Success: {executor.get_state().success}")
"""

from .agentic_executor import AgenticExecutor
from .decision import DecisionEngine
from .memory import WorkingMemory
from .models import (
    Decision,
    DecisionType,
    LoopPhase,
    LoopState,
    Observation,
    Reflection,
    ReflectionAssessment,
)
from .observation import ObservationEngine
from .reflection import ReflectionEngine

__all__ = [
    # Core models
    "LoopPhase",
    "LoopState",
    "Observation",
    "Reflection",
    "Decision",
    # Enums
    "DecisionType",
    "ReflectionAssessment",
    # Engines
    "ObservationEngine",
    "ReflectionEngine",
    "DecisionEngine",
    # Memory
    "WorkingMemory",
    # Executor
    "AgenticExecutor",
]
