"""
Intent Classification Interface

Defines the abstract interface for intent classification.
All classifiers (keyword, transformer, hybrid) implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(Enum):
    """
    Types of user intents recognized by the system.

    These map to different execution strategies:
    - CODE_EDIT: Route to CodeAgent or Aider for code modifications
    - CODE_EXPLAIN: Route to ResearchAgent for code explanation
    - CODE_REVIEW: Route to ReviewAgent for quality analysis
    - CODE_GENERATE: Route to CodeAgent for new code generation
    - DEBUG: Route to DebugAgent for error analysis
    - TEST: Route to TestAgent for test creation/execution
    - REFACTOR: Route to CodeAgent + ReviewAgent collaboration
    - DOCUMENTATION: Route to DocAgent for documentation generation
    - SEARCH: Route to ContextEngine for codebase search
    - QUESTION: Handle as Q&A about the codebase
    - COMMAND: Execute shell commands or system operations
    - PLANNING: Route to PlanAgent for task planning
    - CHAT: Handle as general conversation (no agent needed)
    - UNKNOWN: Fallback for unrecognized intents
    """

    CODE_EDIT = "code_edit"
    CODE_EXPLAIN = "code_explain"
    CODE_REVIEW = "code_review"
    CODE_GENERATE = "code_generate"
    DEBUG = "debug"
    TEST = "test"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    SEARCH = "search"
    QUESTION = "question"
    COMMAND = "command"
    PLANNING = "planning"
    CHAT = "chat"
    UNKNOWN = "unknown"
    # Legacy alias
    EXPLAIN = "explain"

    @classmethod
    def from_string(cls, value: str) -> "IntentType":
        """Convert string to IntentType, defaulting to CHAT"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.CHAT


@dataclass
class ExtractedEntity:
    """
    An entity extracted from user input.

    Examples:
        - File: ExtractedEntity("file", "src/main.py", 0.95, (10, 21))
        - Symbol: ExtractedEntity("symbol", "authenticate", 0.8, (25, 37))
        - LineRange: ExtractedEntity("line_range", "45-60", 0.9, (45, 50))
    """

    type: str  # "file", "symbol", "line_range", "error_type", "language"
    value: str
    confidence: float  # 0.0 - 1.0
    span: tuple[int, int] | None = None  # Character positions in original text

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type,
            "value": self.value,
            "confidence": self.confidence,
            "span": self.span,
        }


@dataclass
class IntentResult:
    """
    Result of intent classification.

    Attributes:
        primary_intent: The main intent detected
        secondary_intents: Additional intents (for multi-intent requests)
        confidence: Confidence score for primary intent (0.0 - 1.0)
        extracted_entities: Entities found in the request (files, symbols, etc.)
        raw_scores: Optional dict of all intent scores (for debugging)
    """

    primary_intent: IntentType
    secondary_intents: list[IntentType] = field(default_factory=list)
    confidence: float = 1.0
    extracted_entities: list[ExtractedEntity] = field(default_factory=list)
    raw_scores: dict[str, float] | None = None

    @property
    def is_multi_intent(self) -> bool:
        """Check if request has multiple intents"""
        return len(self.secondary_intents) > 0

    @property
    def all_intents(self) -> list[IntentType]:
        """Get all intents (primary + secondary)"""
        return [self.primary_intent] + self.secondary_intents

    @property
    def file_entities(self) -> list[str]:
        """Get all extracted file paths"""
        return [e.value for e in self.extracted_entities if e.type == "file"]

    @property
    def symbol_entities(self) -> list[str]:
        """Get all extracted symbol names"""
        return [e.value for e in self.extracted_entities if e.type == "symbol"]

    def has_entity_type(self, entity_type: str) -> bool:
        """Check if a specific entity type was extracted"""
        return any(e.type == entity_type for e in self.extracted_entities)

    def get_entities_by_type(self, entity_type: str) -> list[ExtractedEntity]:
        """Get all entities of a specific type"""
        return [e for e in self.extracted_entities if e.type == entity_type]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "primary_intent": self.primary_intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "confidence": self.confidence,
            "extracted_entities": [e.to_dict() for e in self.extracted_entities],
            "raw_scores": self.raw_scores,
        }


class IntentClassifier(ABC):
    """
    Abstract base class for intent classifiers.

    Implementations:
        - KeywordIntentClassifier: Simple keyword matching (fast, no dependencies)
        - TransformerIntentClassifier: Embedding-based classification (accurate)
        - HybridIntentClassifier: Combines both with fallback (recommended)
    """

    @abstractmethod
    async def classify(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        """
        Classify user intent from text.

        Args:
            text: User's input text/prompt
            context: Optional context (conversation history, workspace info, etc.)

        Returns:
            IntentResult with primary intent, confidence, and extracted entities
        """
        pass

    @abstractmethod
    def get_supported_intents(self) -> list[IntentType]:
        """Return list of intents this classifier can detect"""
        pass

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """
        Extract entities from text.

        Default implementation - override for more sophisticated extraction.
        """
        return []
