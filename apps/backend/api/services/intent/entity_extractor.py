"""
Entity Extraction for Intent Classification

Extracts structured entities from user input:
- File paths and directories
- Function/class/variable names
- Line numbers and ranges
- Error types and messages
- Programming languages

Designed to be extensible with more sophisticated extraction (NER, LLM-based).
"""

import re
from dataclasses import dataclass
from typing import Any

from .interface import ExtractedEntity


@dataclass
class ExtractionPattern:
    """A pattern for extracting a specific entity type"""

    entity_type: str
    pattern: str
    confidence: float = 0.8
    flags: int = re.IGNORECASE
    group: int = 1  # Capture group to extract
    validator: callable | None = None  # Optional validation function


class EntityExtractor:
    """
    Extracts entities from text using regex patterns.

    Extensible design allows adding new entity types easily.
    Future: Add NER model integration for better accuracy.
    """

    # ===== File and Path Patterns =====
    FILE_PATTERNS = [
        ExtractionPattern(
            entity_type="file",
            pattern=r'(?:in|from|to|file|edit|modify|update|read|open)\s+["\']?([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)["\']?',
            confidence=0.9,
        ),
        ExtractionPattern(
            entity_type="file",
            pattern=r'([a-zA-Z0-9_\-./]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|hpp|rb|php|swift|kt|vue|svelte|html|css|scss|json|yaml|yml|toml|md|sql))\b',
            confidence=0.85,
        ),
        ExtractionPattern(
            entity_type="file",
            pattern=r'\b((?:src|lib|app|api|tests?|spec|components?|pages?|utils?|hooks?|services?)/[a-zA-Z0-9_\-./]+)\b',
            confidence=0.8,
        ),
        ExtractionPattern(
            entity_type="file",
            pattern=r'`([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)`',
            confidence=0.9,
        ),
    ]

    # ===== Symbol Patterns (functions, classes, variables) =====
    SYMBOL_PATTERNS = [
        ExtractionPattern(
            entity_type="function",
            pattern=r'(?:function|def|fn|func|method)\s+[`"\']?([a-zA-Z_][a-zA-Z0-9_]*)[`"\']?',
            confidence=0.9,
        ),
        ExtractionPattern(
            entity_type="class",
            pattern=r'(?:class|struct|interface|type)\s+[`"\']?([A-Z][a-zA-Z0-9_]*)[`"\']?',
            confidence=0.9,
        ),
        ExtractionPattern(
            entity_type="symbol",
            pattern=r'`([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)`',
            confidence=0.85,
        ),
        ExtractionPattern(
            entity_type="symbol",
            pattern=r'\b(?:the|call|use|import|from)\s+([A-Z][a-zA-Z0-9]*|[a-z]+_[a-z_]+)\b',
            confidence=0.7,
        ),
        ExtractionPattern(
            entity_type="variable",
            pattern=r'(?:variable|var|const|let)\s+[`"\']?([a-zA-Z_][a-zA-Z0-9_]*)[`"\']?',
            confidence=0.85,
        ),
    ]

    # ===== Line Number Patterns =====
    LINE_PATTERNS = [
        ExtractionPattern(
            entity_type="line_number",
            pattern=r'(?:line|L)\s*(\d+)',
            confidence=0.95,
        ),
        ExtractionPattern(
            entity_type="line_range",
            pattern=r'lines?\s+(\d+)\s*[-–to]+\s*(\d+)',
            confidence=0.95,
            group=0,  # Get full match, parse later
        ),
        ExtractionPattern(
            entity_type="line_range",
            pattern=r'L(\d+)-L?(\d+)',
            confidence=0.95,
            group=0,
        ),
    ]

    # ===== Error Patterns =====
    ERROR_PATTERNS = [
        ExtractionPattern(
            entity_type="error_type",
            pattern=r'(TypeError|ValueError|KeyError|AttributeError|ImportError|SyntaxError|RuntimeError|IndexError|NameError|FileNotFoundError|PermissionError|ConnectionError|TimeoutError)\b',
            confidence=0.95,
            flags=0,  # Case-sensitive for error types
        ),
        ExtractionPattern(
            entity_type="error_type",
            pattern=r'(NullPointerException|ArrayIndexOutOfBoundsException|ClassNotFoundException|IOException)\b',
            confidence=0.95,
            flags=0,
        ),
        ExtractionPattern(
            entity_type="http_error",
            pattern=r'\b(4\d{2}|5\d{2})\s*(?:error|status)?\b',
            confidence=0.85,
        ),
        ExtractionPattern(
            entity_type="error_message",
            pattern=r'(?:error|exception|failed):\s*["\']?([^"\']+)["\']?',
            confidence=0.7,
        ),
    ]

    # ===== Language Patterns =====
    LANGUAGE_PATTERNS = [
        ExtractionPattern(
            entity_type="language",
            pattern=r'\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|Ruby|PHP|Swift|Kotlin)\b',
            confidence=0.9,
        ),
        ExtractionPattern(
            entity_type="framework",
            pattern=r'\b(React|Vue|Angular|Django|Flask|FastAPI|Express|Next\.js|Rails|Spring)\b',
            confidence=0.85,
        ),
    ]

    # ===== Command/Tool Patterns =====
    COMMAND_PATTERNS = [
        ExtractionPattern(
            entity_type="command",
            pattern=r'(?:run|execute|call)\s+[`"\']?([a-z][a-z0-9_\-]*(?:\s+[^\s]+)*)[`"\']?',
            confidence=0.7,
        ),
        ExtractionPattern(
            entity_type="test_command",
            pattern=r'\b(pytest|jest|mocha|go test|cargo test|npm test)\b',
            confidence=0.9,
        ),
    ]

    def __init__(self, custom_patterns: list[ExtractionPattern] | None = None):
        """
        Initialize entity extractor.

        Args:
            custom_patterns: Additional patterns to use
        """
        self.patterns = (
            self.FILE_PATTERNS
            + self.SYMBOL_PATTERNS
            + self.LINE_PATTERNS
            + self.ERROR_PATTERNS
            + self.LANGUAGE_PATTERNS
            + self.COMMAND_PATTERNS
        )

        if custom_patterns:
            self.patterns.extend(custom_patterns)

    def extract(self, text: str) -> list[ExtractedEntity]:
        """
        Extract all entities from text.

        Args:
            text: Input text to extract entities from

        Returns:
            List of extracted entities
        """
        entities = []

        for pattern_def in self.patterns:
            try:
                regex = re.compile(pattern_def.pattern, pattern_def.flags)
                for match in regex.finditer(text):
                    value = match.group(pattern_def.group)

                    # Skip if value is too short or a common false positive
                    if self._should_skip(value, pattern_def.entity_type):
                        continue

                    # Run validator if present
                    if pattern_def.validator and not pattern_def.validator(value):
                        continue

                    entities.append(
                        ExtractedEntity(
                            type=pattern_def.entity_type,
                            value=value,
                            confidence=pattern_def.confidence,
                            span=(match.start(pattern_def.group), match.end(pattern_def.group)),
                        )
                    )
            except re.error as e:
                # Log and skip invalid patterns
                continue

        # Deduplicate and resolve conflicts
        return self._deduplicate(entities)

    def _should_skip(self, value: str, entity_type: str) -> bool:
        """Check if value should be skipped as a false positive"""
        if not value or len(value) < 2:
            return True

        # Common false positives
        false_positives = {"e.g", "i.e", "etc", "vs", "ie", "eg"}
        if value.lower() in false_positives:
            return True

        # Skip very short symbols unless they're specific types
        if entity_type in ("symbol", "variable") and len(value) < 3:
            return True

        return False

    def _deduplicate(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """
        Deduplicate entities, keeping highest confidence for each unique value.
        """
        # Group by (type, value)
        entity_map: dict[tuple[str, str], ExtractedEntity] = {}

        for entity in entities:
            key = (entity.type, entity.value)
            if key in entity_map:
                # Keep higher confidence
                if entity.confidence > entity_map[key].confidence:
                    entity_map[key] = entity
            else:
                entity_map[key] = entity

        return list(entity_map.values())

    def extract_by_type(self, text: str, entity_type: str) -> list[ExtractedEntity]:
        """Extract only entities of a specific type"""
        all_entities = self.extract(text)
        return [e for e in all_entities if e.type == entity_type]

    def extract_files(self, text: str) -> list[str]:
        """Convenience method to extract file paths"""
        return [e.value for e in self.extract_by_type(text, "file")]

    def extract_symbols(self, text: str) -> list[str]:
        """Convenience method to extract symbol names"""
        symbol_types = {"symbol", "function", "class", "variable"}
        entities = self.extract(text)
        return [e.value for e in entities if e.type in symbol_types]

    def extract_with_context(
        self, text: str, context_chars: int = 50
    ) -> list[dict[str, Any]]:
        """
        Extract entities with surrounding context.

        Useful for debugging and understanding extractions.
        """
        entities = self.extract(text)
        results = []

        for entity in entities:
            if entity.span:
                start, end = entity.span
                context_start = max(0, start - context_chars)
                context_end = min(len(text), end + context_chars)
                context = text[context_start:context_end]
            else:
                context = None

            results.append({
                "entity": entity.to_dict(),
                "context": context,
            })

        return results


# Singleton instance
_default_extractor: EntityExtractor | None = None


def get_entity_extractor() -> EntityExtractor:
    """Get the default entity extractor instance"""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = EntityExtractor()
    return _default_extractor


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Convenience function for entity extraction"""
    return get_entity_extractor().extract(text)
