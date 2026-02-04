"""
Hybrid Intent Classifier

Combines keyword and transformer-based classification for best of both worlds:
- Fast keyword matching for common patterns
- Semantic understanding for novel/ambiguous requests
- Graceful fallback when transformer unavailable

This is the recommended classifier for production use.
"""

import logging
from typing import Any

from .interface import (
    ExtractedEntity,
    IntentClassifier,
    IntentResult,
    IntentType,
)
from .keyword_classifier import KeywordIntentClassifier
from .training_data import CONFIDENCE_THRESHOLDS

logger = logging.getLogger(__name__)


class HybridIntentClassifier(IntentClassifier):
    """
    Hybrid classifier combining keyword and transformer approaches.

    Strategy:
    1. Run keyword classifier first (fast)
    2. If high confidence (>0.8), use keyword result
    3. If low confidence (<0.5), use transformer
    4. If medium confidence, combine both results

    Falls back to keyword-only if transformer unavailable.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        keyword_weight: float = 0.3,
        transformer_weight: float = 0.7,
        high_confidence_threshold: float = 0.85,
        low_confidence_threshold: float = 0.5,
        fallback_to_keywords: bool = True,
    ):
        """
        Initialize hybrid classifier.

        Args:
            model_name: Sentence-transformer model name
            keyword_weight: Weight for keyword scores in combination
            transformer_weight: Weight for transformer scores
            high_confidence_threshold: Above this, trust keyword result
            low_confidence_threshold: Below this, prefer transformer
            fallback_to_keywords: Use keywords if transformer fails
        """
        self.model_name = model_name
        self.keyword_weight = keyword_weight
        self.transformer_weight = transformer_weight
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self.fallback_to_keywords = fallback_to_keywords

        # Initialize keyword classifier (always available)
        self.keyword_classifier = KeywordIntentClassifier()

        # Lazy-load transformer classifier
        self._transformer_classifier = None
        self._transformer_available = None

    @property
    def transformer_classifier(self):
        """Lazy-load transformer classifier"""
        if self._transformer_classifier is None:
            try:
                from .transformer_classifier import TransformerIntentClassifier

                self._transformer_classifier = TransformerIntentClassifier(
                    model_name=self.model_name
                )
                self._transformer_available = True
                logger.info("Transformer classifier loaded successfully")
            except ImportError as e:
                logger.warning(
                    f"Transformer classifier not available: {e}. "
                    "Falling back to keyword-only classification."
                )
                self._transformer_available = False

        return self._transformer_classifier

    @property
    def transformer_available(self) -> bool:
        """Check if transformer is available (triggers lazy load)"""
        if self._transformer_available is None:
            _ = self.transformer_classifier
        return self._transformer_available

    async def classify(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        """
        Classify intent using hybrid approach.

        Args:
            text: User's input text
            context: Optional context

        Returns:
            IntentResult with best classification
        """
        # Always run keyword classifier first (fast)
        keyword_result = await self.keyword_classifier.classify(text, context)

        # Fast path: high confidence keyword match
        if keyword_result.confidence >= self.high_confidence_threshold:
            logger.debug(
                f"High confidence keyword match: {keyword_result.primary_intent.value} "
                f"({keyword_result.confidence:.2f})"
            )
            return keyword_result

        # Check if transformer is available
        if not self.transformer_available:
            if self.fallback_to_keywords:
                return keyword_result
            else:
                raise RuntimeError("Transformer classifier not available")

        # Run transformer classifier
        try:
            transformer_result = await self.transformer_classifier.classify(text, context)
        except Exception as e:
            logger.error(f"Transformer classification failed: {e}")
            if self.fallback_to_keywords:
                return keyword_result
            raise

        # Low keyword confidence: trust transformer
        if keyword_result.confidence < self.low_confidence_threshold:
            logger.debug(
                f"Low keyword confidence, using transformer: "
                f"{transformer_result.primary_intent.value} "
                f"({transformer_result.confidence:.2f})"
            )
            return transformer_result

        # Medium confidence: combine results
        return self._combine_results(keyword_result, transformer_result, text)

    def _combine_results(
        self,
        keyword_result: IntentResult,
        transformer_result: IntentResult,
        text: str,
    ) -> IntentResult:
        """
        Combine keyword and transformer results.

        Uses weighted scoring with agreement bonus.
        """
        # Build combined score map
        combined_scores: dict[IntentType, float] = {}

        # Add keyword scores
        if keyword_result.raw_scores:
            for intent_str, score in keyword_result.raw_scores.items():
                intent = IntentType.from_string(intent_str)
                combined_scores[intent] = score * self.keyword_weight

        # Add transformer scores
        if transformer_result.raw_scores:
            for intent_str, score in transformer_result.raw_scores.items():
                intent = IntentType.from_string(intent_str)
                current = combined_scores.get(intent, 0.0)
                combined_scores[intent] = current + score * self.transformer_weight

        # Agreement bonus: if both agree on primary intent, boost confidence
        if keyword_result.primary_intent == transformer_result.primary_intent:
            primary = keyword_result.primary_intent
            combined_scores[primary] = combined_scores.get(primary, 0.0) + 0.1

        # Find best intent
        if not combined_scores:
            # Fallback
            return keyword_result

        sorted_intents = sorted(
            combined_scores.items(), key=lambda x: x[1], reverse=True
        )

        primary_intent = sorted_intents[0][0]
        primary_score = min(sorted_intents[0][1], 1.0)

        # Get secondary intents
        secondary_intents = []
        for intent, score in sorted_intents[1:]:
            if score >= CONFIDENCE_THRESHOLDS["low"]:
                secondary_intents.append(intent)

        # Merge entities from both results
        entities = self._merge_entities(
            keyword_result.extracted_entities,
            transformer_result.extracted_entities,
        )

        return IntentResult(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            confidence=primary_score,
            extracted_entities=entities,
            raw_scores={k.value: v for k, v in combined_scores.items()},
        )

    def _merge_entities(
        self,
        keyword_entities: list[ExtractedEntity],
        transformer_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Merge entities from both classifiers, preferring higher confidence.
        """
        # Use dict to deduplicate by (type, value)
        entity_map: dict[tuple[str, str], ExtractedEntity] = {}

        for entity in keyword_entities:
            key = (entity.type, entity.value)
            entity_map[key] = entity

        for entity in transformer_entities:
            key = (entity.type, entity.value)
            if key in entity_map:
                # Keep higher confidence
                if entity.confidence > entity_map[key].confidence:
                    entity_map[key] = entity
            else:
                entity_map[key] = entity

        return list(entity_map.values())

    def get_supported_intents(self) -> list[IntentType]:
        """Return all intent types"""
        return list(IntentType)

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities using keyword classifier's patterns"""
        return self.keyword_classifier.extract_entities(text)

    async def classify_with_explanation(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Classify with detailed explanation of how the result was determined.

        Useful for debugging and understanding model behavior.
        """
        keyword_result = await self.keyword_classifier.classify(text, context)

        explanation = {
            "input": text,
            "keyword_result": {
                "intent": keyword_result.primary_intent.value,
                "confidence": keyword_result.confidence,
                "scores": keyword_result.raw_scores,
            },
            "transformer_available": self.transformer_available,
            "decision_path": None,
            "final_result": None,
        }

        if keyword_result.confidence >= self.high_confidence_threshold:
            explanation["decision_path"] = "high_confidence_keyword"
            explanation["final_result"] = keyword_result.to_dict()
            return explanation

        if self.transformer_available:
            try:
                transformer_result = await self.transformer_classifier.classify(
                    text, context
                )
                explanation["transformer_result"] = {
                    "intent": transformer_result.primary_intent.value,
                    "confidence": transformer_result.confidence,
                    "scores": transformer_result.raw_scores,
                }

                if keyword_result.confidence < self.low_confidence_threshold:
                    explanation["decision_path"] = "low_confidence_use_transformer"
                    explanation["final_result"] = transformer_result.to_dict()
                else:
                    explanation["decision_path"] = "combined_scores"
                    combined = self._combine_results(
                        keyword_result, transformer_result, text
                    )
                    explanation["final_result"] = combined.to_dict()

            except Exception as e:
                explanation["transformer_error"] = str(e)
                explanation["decision_path"] = "transformer_error_fallback"
                explanation["final_result"] = keyword_result.to_dict()
        else:
            explanation["decision_path"] = "transformer_unavailable_fallback"
            explanation["final_result"] = keyword_result.to_dict()

        return explanation


# Convenience function for quick classification
async def classify_intent(
    text: str,
    use_transformer: bool = True,
    context: dict[str, Any] | None = None,
) -> IntentResult:
    """
    Convenience function for intent classification.

    Args:
        text: User input text
        use_transformer: Whether to use transformer (falls back if unavailable)
        context: Optional context

    Returns:
        IntentResult
    """
    if use_transformer:
        classifier = HybridIntentClassifier()
    else:
        classifier = KeywordIntentClassifier()

    return await classifier.classify(text, context)
