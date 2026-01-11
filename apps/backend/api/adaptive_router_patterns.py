"""
Adaptive Router Patterns - Static definitions for task routing

Extracted from adaptive_router.py during P2 decomposition.
Contains:
- TaskType and ToolType enums
- RoutePattern and RouteResult dataclasses
- DEFAULT_ROUTE_PATTERNS for ElohimOS routing
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ===== Task and Tool Types =====

class TaskType(str, Enum):
    """Types of tasks the agent can handle"""
    CODE_WRITE = "code_write"
    CODE_EDIT = "code_edit"
    BUG_FIX = "bug_fix"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    EXPLANATION = "explanation"
    SYSTEM_COMMAND = "system_command"
    GIT_OPERATION = "git_operation"
    FILE_OPERATION = "file_operation"
    CHAT = "chat"  # ElohimOS-specific: general chat


class ToolType(str, Enum):
    """Available tools in ElohimOS"""
    OLLAMA = "ollama"  # Local LLM via Ollama
    SYSTEM = "system"  # System commands
    P2P = "p2p"  # P2P messaging (for missionaries)
    DATA = "data"  # Data analysis tools


# ===== Route Patterns =====

@dataclass
class RoutePattern:
    """Enhanced pattern for routing with confidence scoring"""
    pattern_type: str  # 'keyword', 'regex'
    patterns: List[str]
    task_type: TaskType
    tool_type: ToolType
    weight: float = 1.0
    min_confidence: float = 0.5
    context_hints: List[str] = None
    negative_patterns: List[str] = None

    def __post_init__(self) -> None:
        if self.context_hints is None:
            self.context_hints = []
        if self.negative_patterns is None:
            self.negative_patterns = []


@dataclass
class RouteResult:
    """Result of routing analysis with confidence"""
    task_type: TaskType
    tool_type: ToolType
    confidence: float
    matched_patterns: List[str]
    reasoning: str
    fallback_options: List[Tuple[TaskType, ToolType, float]]
    suggested_model: str = "qwen2.5-coder:1.5b-instruct"
    context: Dict = None


# ===== Default Route Patterns for ElohimOS =====

DEFAULT_ROUTE_PATTERNS: List[RoutePattern] = [
    # ===== Data Analysis =====
    RoutePattern(
        pattern_type='regex',
        patterns=[
            r'(analyze|query|search)\s+.*\s+(data|database|table|excel|csv)',
            r'sql\s+(query|select|insert|update|delete)',
            r'(show|list|find)\s+.*\s+(from|in)\s+.*\s+(table|database)',
        ],
        task_type=TaskType.RESEARCH,
        tool_type=ToolType.DATA,
        weight=1.8
    ),

    # ===== P2P Messaging (Missionaries) =====
    RoutePattern(
        pattern_type='keyword',
        patterns=['send message', 'p2p', 'peer to peer', 'offline message', 'missionary'],
        task_type=TaskType.CHAT,
        tool_type=ToolType.P2P,
        weight=2.0
    ),

    # ===== Code & Documentation =====
    RoutePattern(
        pattern_type='regex',
        patterns=[
            r'(write|create|generate)\s+.*code',
            r'(implement|build|develop)\s+.*\s+(function|feature)',
        ],
        task_type=TaskType.CODE_WRITE,
        tool_type=ToolType.OLLAMA,
        weight=1.5
    ),

    RoutePattern(
        pattern_type='keyword',
        patterns=['document', 'documentation', 'readme', 'docs'],
        task_type=TaskType.DOCUMENTATION,
        tool_type=ToolType.OLLAMA,
        weight=1.3
    ),

    # ===== General Chat (Default) =====
    RoutePattern(
        pattern_type='regex',
        patterns=[
            r'^(what|why|how|when|where)\s+',
            r'explain\s+',
            r'tell\s+me\s+(about|how)',
        ],
        task_type=TaskType.EXPLANATION,
        tool_type=ToolType.OLLAMA,
        weight=0.8,
        min_confidence=0.4
    ),
]


__all__ = [
    # Enums
    "TaskType",
    "ToolType",
    # Dataclasses
    "RoutePattern",
    "RouteResult",
    # Constants
    "DEFAULT_ROUTE_PATTERNS",
]
