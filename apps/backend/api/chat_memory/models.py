"""
Chat Memory Models

Data classes for chat memory system.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ConversationEvent:
    """Single conversation event (message)"""
    timestamp: str
    role: str  # user|assistant
    content: str
    model: Optional[str] = None
    tokens: Optional[int] = None
    files: Optional[List[Dict[str, Any]]] = None


__all__ = ["ConversationEvent"]
