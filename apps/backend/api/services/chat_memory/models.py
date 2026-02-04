"""
Data models for chat memory system
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class ConversationEvent:
    """Single conversation event (message)"""

    timestamp: str
    role: str  # user|assistant
    content: str
    model: str | None = None
    tokens: int | None = None
    files: list[dict[str, Any]] | None = None
