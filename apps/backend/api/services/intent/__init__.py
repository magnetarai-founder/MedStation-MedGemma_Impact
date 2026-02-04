"""
Intent Classification System

Provides NLP-based intent classification for user requests.
Supports keyword-based, transformer-based, and hybrid classification.

Usage:
    from api.services.intent import get_intent_classifier, IntentType, IntentResult

    # Hybrid classifier (recommended - combines keyword + transformer)
    classifier = get_intent_classifier(use_transformer=True)
    result = await classifier.classify("add a login button to the header")
    # result.primary_intent == IntentType.CODE_EDIT
    # result.confidence == 0.85

    # Quick classification function
    from api.services.intent import classify_intent
    result = await classify_intent("fix the authentication bug")
"""

from .entity_extractor import EntityExtractor, extract_entities, get_entity_extractor
from .interface import (
    ExtractedEntity,
    IntentClassifier,
    IntentResult,
    IntentType,
)
from .keyword_classifier import KeywordIntentClassifier, intent_to_agent_roles

# Default classifier instance
_default_classifier: IntentClassifier | None = None
_hybrid_classifier: IntentClassifier | None = None


def get_intent_classifier(use_transformer: bool = True) -> IntentClassifier:
    """
    Get the intent classifier instance.

    Args:
        use_transformer: If True (default), use hybrid classifier with transformer.
                        If False, use keyword-only classifier.

    Returns:
        IntentClassifier instance
    """
    global _default_classifier, _hybrid_classifier

    if use_transformer:
        if _hybrid_classifier is None:
            try:
                from .hybrid_classifier import HybridIntentClassifier

                _hybrid_classifier = HybridIntentClassifier()
            except ImportError:
                # Fall back to keyword classifier if deps not available
                _hybrid_classifier = KeywordIntentClassifier()
        return _hybrid_classifier

    if _default_classifier is None:
        _default_classifier = KeywordIntentClassifier()

    return _default_classifier


async def classify_intent(
    text: str,
    use_transformer: bool = True,
) -> IntentResult:
    """
    Convenience function for quick intent classification.

    Args:
        text: User input text
        use_transformer: Whether to use transformer-based classification

    Returns:
        IntentResult with primary intent and confidence
    """
    classifier = get_intent_classifier(use_transformer=use_transformer)
    return await classifier.classify(text)


__all__ = [
    # Core types
    "IntentType",
    "IntentResult",
    "ExtractedEntity",
    # Base class
    "IntentClassifier",
    # Implementations
    "KeywordIntentClassifier",
    # Entity extraction
    "EntityExtractor",
    "get_entity_extractor",
    "extract_entities",
    # Factory & utilities
    "get_intent_classifier",
    "classify_intent",
    "intent_to_agent_roles",
]
