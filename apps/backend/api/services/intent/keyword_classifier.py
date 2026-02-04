"""
Keyword-Based Intent Classifier

Simple but fast intent classification using keyword matching.
Used as a fallback when transformer-based classification isn't available.

This wraps the existing logic from agent_types.get_collaborative_agents()
into the IntentClassifier interface.
"""

import re
from typing import Any

from .interface import (
    ExtractedEntity,
    IntentClassifier,
    IntentResult,
    IntentType,
)


class KeywordIntentClassifier(IntentClassifier):
    """
    Intent classifier using keyword pattern matching.

    Fast and reliable for common patterns. No external dependencies.
    Lower accuracy for ambiguous or novel requests.
    """

    # Keyword patterns for each intent type
    # Order matters - first match wins for primary intent
    INTENT_PATTERNS: dict[IntentType, list[str]] = {
        IntentType.CODE_EDIT: [
            "implement",
            "add",
            "create",
            "build",
            "write",
            "make",
            "change",
            "update",
            "modify",
            "edit",
            "insert",
            "remove",
            "delete",
            "replace",
        ],
        IntentType.DEBUG: [
            "fix",
            "bug",
            "error",
            "broken",
            "crash",
            "fail",
            "issue",
            "problem",
            "debug",
            "trace",
            "exception",
            "traceback",
            "stack trace",
        ],
        IntentType.REFACTOR: [
            "refactor",
            "improve",
            "optimize",
            "clean up",
            "cleanup",
            "reorganize",
            "restructure",
            "simplify",
            "consolidate",
        ],
        IntentType.TEST: [
            "test",
            "coverage",
            "validation",
            "verify",
            "assert",
            "mock",
            "unittest",
            "pytest",
            "spec",
        ],
        IntentType.CODE_REVIEW: [
            "review",
            "check",
            "audit",
            "quality",
            "lint",
            "analyze code",
            "code quality",
            "best practice",
        ],
        IntentType.EXPLAIN: [
            "explain",
            "document",
            "describe",
            "what does",
            "how does",
            "why does",
            "understand",
            "analyze",
            "summarize",
        ],
        IntentType.SEARCH: [
            "find",
            "search",
            "locate",
            "where is",
            "look for",
            "grep",
            "show me",
            "list all",
        ],
    }

    # Patterns for entity extraction
    FILE_PATTERNS = [
        # Explicit file references
        r'(?:in|from|to|file|edit|modify|update)\s+["\']?([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)["\']?',
        # Common file extensions
        r'([a-zA-Z0-9_\-./]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|hpp|rb|php|swift|kt))\b',
        # Paths with directories
        r'\b((?:src|lib|app|api|tests?|spec)/[a-zA-Z0-9_\-./]+)\b',
    ]

    SYMBOL_PATTERNS = [
        # Function/class/method references
        r'(?:function|class|method|def|fn)\s+[`"\']?([a-zA-Z_][a-zA-Z0-9_]*)[`"\']?',
        # Backtick-quoted symbols
        r'`([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)`',
        # CamelCase or snake_case identifiers (high confidence only in context)
        r'\b(?:the|call|use|import)\s+([A-Z][a-zA-Z0-9]*|[a-z]+_[a-z_]+)\b',
    ]

    LINE_RANGE_PATTERNS = [
        r'lines?\s+(\d+(?:\s*[-–]\s*\d+)?)',
        r'line\s+(\d+)',
        r'L(\d+(?:-\d+)?)',
    ]

    def __init__(self, confidence_boost: float = 0.1):
        """
        Initialize keyword classifier.

        Args:
            confidence_boost: Extra confidence for each additional matching keyword
        """
        self.confidence_boost = confidence_boost

    async def classify(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        """
        Classify intent using keyword matching.

        Args:
            text: User's input text
            context: Optional context (not used by keyword classifier)

        Returns:
            IntentResult with detected intent and entities
        """
        text_lower = text.lower()

        # Score each intent type
        scores: dict[IntentType, float] = {}
        for intent_type, keywords in self.INTENT_PATTERNS.items():
            score = self._calculate_score(text_lower, keywords)
            if score > 0:
                scores[intent_type] = score

        # Determine primary and secondary intents
        if not scores:
            # Default to CHAT if no patterns match
            primary_intent = IntentType.CHAT
            confidence = 0.5
            secondary_intents = []
        else:
            # Sort by score
            sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            primary_intent = sorted_intents[0][0]
            confidence = min(sorted_intents[0][1], 1.0)

            # Secondary intents are those with score > 0.3
            secondary_intents = [
                intent for intent, score in sorted_intents[1:] if score >= 0.3
            ]

        # Extract entities
        entities = self.extract_entities(text)

        return IntentResult(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            confidence=confidence,
            extracted_entities=entities,
            raw_scores={k.value: v for k, v in scores.items()},
        )

    def _calculate_score(self, text: str, keywords: list[str]) -> float:
        """Calculate match score for a list of keywords"""
        matches = 0
        for keyword in keywords:
            if keyword in text:
                matches += 1

        if matches == 0:
            return 0.0

        # Base confidence + boost for multiple matches
        base_confidence = 0.6
        return min(base_confidence + (matches - 1) * self.confidence_boost, 1.0)

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract file paths, symbols, and line ranges from text"""
        entities = []

        # Extract file paths
        for pattern in self.FILE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                # Skip common false positives
                if value.lower() in ("e.g", "i.e", "etc"):
                    continue
                entities.append(
                    ExtractedEntity(
                        type="file",
                        value=value,
                        confidence=0.8,
                        span=(match.start(1), match.end(1)),
                    )
                )

        # Extract symbols
        for pattern in self.SYMBOL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                # Skip very short symbols (likely false positives)
                if len(value) < 2:
                    continue
                entities.append(
                    ExtractedEntity(
                        type="symbol",
                        value=value,
                        confidence=0.7,
                        span=(match.start(1), match.end(1)),
                    )
                )

        # Extract line ranges
        for pattern in self.LINE_RANGE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(
                    ExtractedEntity(
                        type="line_range",
                        value=match.group(1),
                        confidence=0.9,
                        span=(match.start(1), match.end(1)),
                    )
                )

        # Deduplicate by value
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.type, entity.value)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    def get_supported_intents(self) -> list[IntentType]:
        """Return all intent types this classifier supports"""
        return list(IntentType)


# Utility function to map intent to agent roles
def intent_to_agent_roles(intent: IntentType) -> list[str]:
    """
    Map an intent type to the agent roles that should handle it.

    This bridges the new intent system with the existing agent_types module.
    """
    mapping = {
        IntentType.CODE_EDIT: ["code", "test"],
        IntentType.DEBUG: ["debug", "test"],
        IntentType.REFACTOR: ["code", "review"],
        IntentType.TEST: ["test"],
        IntentType.CODE_REVIEW: ["review"],
        IntentType.EXPLAIN: ["research"],
        IntentType.SEARCH: ["research"],
        IntentType.CHAT: ["code"],  # Default to code agent
    }
    return mapping.get(intent, ["code"])
