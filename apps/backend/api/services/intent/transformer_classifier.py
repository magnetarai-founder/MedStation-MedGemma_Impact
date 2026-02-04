"""
Transformer-Based Intent Classifier

Uses sentence-transformers to classify intent via semantic similarity.
Compares user input embeddings against pre-computed intent embeddings.

More accurate than keyword matching for:
- Natural language variations
- Synonyms and paraphrasing
- Context-dependent meaning
"""

import logging
from typing import Any

import numpy as np

from .interface import (
    ExtractedEntity,
    IntentClassifier,
    IntentResult,
    IntentType,
)
from .training_data import (
    COMPATIBLE_INTENTS,
    CONFIDENCE_THRESHOLDS,
    INTENT_EXAMPLES,
    INTENT_PRIORITY,
)

logger = logging.getLogger(__name__)


class TransformerIntentClassifier(IntentClassifier):
    """
    Intent classifier using sentence-transformer embeddings.

    Computes semantic similarity between user input and intent examples.
    Supports multi-label classification for requests with multiple intents.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.5,
        secondary_threshold: float = 0.4,
        cache_embeddings: bool = True,
    ):
        """
        Initialize transformer classifier.

        Args:
            model_name: Sentence-transformer model to use
            similarity_threshold: Minimum similarity for primary intent
            secondary_threshold: Minimum similarity for secondary intents
            cache_embeddings: Whether to cache intent embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.secondary_threshold = secondary_threshold
        self.cache_embeddings = cache_embeddings

        # Lazy-loaded components
        self._model = None
        self._intent_embeddings: dict[IntentType, np.ndarray] | None = None
        self._example_embeddings: list[tuple[np.ndarray, IntentType]] | None = None

    @property
    def model(self):
        """Lazy-load the sentence transformer model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence-transformer model: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for TransformerIntentClassifier. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    def _build_intent_embeddings(self) -> dict[IntentType, np.ndarray]:
        """
        Build averaged embeddings for each intent type.

        Returns:
            Dict mapping intent types to their average embedding vectors
        """
        if self._intent_embeddings is not None and self.cache_embeddings:
            return self._intent_embeddings

        intent_embeddings = {}

        for intent_type, examples in INTENT_EXAMPLES.items():
            if not examples:
                continue

            # Embed all examples for this intent
            embeddings = self.model.encode(examples, convert_to_numpy=True)

            # Average the embeddings to get intent centroid
            centroid = np.mean(embeddings, axis=0)

            # Normalize for cosine similarity
            centroid = centroid / np.linalg.norm(centroid)

            intent_embeddings[intent_type] = centroid

        if self.cache_embeddings:
            self._intent_embeddings = intent_embeddings

        return intent_embeddings

    def _build_example_embeddings(self) -> list[tuple[np.ndarray, IntentType]]:
        """
        Build embeddings for individual examples (for fine-grained matching).

        Returns:
            List of (embedding, intent_type) tuples
        """
        if self._example_embeddings is not None and self.cache_embeddings:
            return self._example_embeddings

        example_embeddings = []

        for intent_type, examples in INTENT_EXAMPLES.items():
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            for emb in embeddings:
                # Normalize
                emb = emb / np.linalg.norm(emb)
                example_embeddings.append((emb, intent_type))

        if self.cache_embeddings:
            self._example_embeddings = example_embeddings

        return example_embeddings

    async def classify(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        """
        Classify intent using semantic similarity.

        Args:
            text: User's input text
            context: Optional context (conversation history, etc.)

        Returns:
            IntentResult with detected intent and confidence
        """
        # Embed the input text
        input_embedding = self.model.encode(text, convert_to_numpy=True)
        input_embedding = input_embedding / np.linalg.norm(input_embedding)

        # Get intent embeddings
        intent_embeddings = self._build_intent_embeddings()

        # Calculate similarity to each intent centroid
        scores: dict[IntentType, float] = {}
        for intent_type, centroid in intent_embeddings.items():
            similarity = float(np.dot(input_embedding, centroid))
            scores[intent_type] = similarity

        # Also check against individual examples for more precision
        example_scores = self._get_example_scores(input_embedding)

        # Combine centroid and example scores
        combined_scores = self._combine_scores(scores, example_scores)

        # Determine primary and secondary intents
        sorted_intents = sorted(
            combined_scores.items(), key=lambda x: (x[1], INTENT_PRIORITY.get(x[0], 0)), reverse=True
        )

        # Primary intent
        primary_intent, primary_score = sorted_intents[0]

        # Check if we meet the threshold
        if primary_score < self.similarity_threshold:
            # Low confidence - fall back to CHAT
            primary_intent = IntentType.CHAT
            primary_score = 0.5

        # Secondary intents (compatible and above threshold)
        secondary_intents = []
        for intent, score in sorted_intents[1:]:
            if score >= self.secondary_threshold:
                # Check compatibility
                if intent in COMPATIBLE_INTENTS.get(primary_intent, set()):
                    secondary_intents.append(intent)

        # Extract entities
        entities = self.extract_entities(text)

        return IntentResult(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            confidence=min(primary_score, 1.0),
            extracted_entities=entities,
            raw_scores={k.value: v for k, v in combined_scores.items()},
        )

    def _get_example_scores(self, input_embedding: np.ndarray) -> dict[IntentType, float]:
        """
        Get max similarity score per intent from individual examples.

        This catches cases where input is very similar to one specific example
        but not to the intent centroid.
        """
        example_embeddings = self._build_example_embeddings()

        # Track max score per intent
        max_scores: dict[IntentType, float] = {intent: 0.0 for intent in IntentType}

        for example_emb, intent_type in example_embeddings:
            similarity = float(np.dot(input_embedding, example_emb))
            if similarity > max_scores[intent_type]:
                max_scores[intent_type] = similarity

        return max_scores

    def _combine_scores(
        self,
        centroid_scores: dict[IntentType, float],
        example_scores: dict[IntentType, float],
    ) -> dict[IntentType, float]:
        """
        Combine centroid and example-based scores.

        Uses weighted average favoring the higher score.
        """
        combined = {}
        for intent_type in IntentType:
            centroid = centroid_scores.get(intent_type, 0.0)
            example = example_scores.get(intent_type, 0.0)

            # Weight the higher score more heavily
            if example > centroid:
                combined[intent_type] = 0.3 * centroid + 0.7 * example
            else:
                combined[intent_type] = 0.6 * centroid + 0.4 * example

        return combined

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """
        Extract entities using regex patterns.

        For more sophisticated extraction, this could use NER models.
        """
        # Import from keyword classifier for consistency
        from .keyword_classifier import KeywordIntentClassifier

        keyword_classifier = KeywordIntentClassifier()
        return keyword_classifier.extract_entities(text)

    def get_supported_intents(self) -> list[IntentType]:
        """Return all intent types"""
        return list(IntentType)

    def get_confidence_level(self, score: float) -> str:
        """
        Get human-readable confidence level.

        Args:
            score: Similarity score (0.0 - 1.0)

        Returns:
            Confidence level string
        """
        if score >= CONFIDENCE_THRESHOLDS["high"]:
            return "high"
        elif score >= CONFIDENCE_THRESHOLDS["medium"]:
            return "medium"
        elif score >= CONFIDENCE_THRESHOLDS["low"]:
            return "low"
        else:
            return "very_low"

    def explain_classification(
        self, text: str, top_k: int = 3
    ) -> dict[str, Any]:
        """
        Explain why a particular classification was made.

        Useful for debugging and understanding model behavior.

        Args:
            text: Input text
            top_k: Number of most similar examples to return

        Returns:
            Dict with classification explanation
        """
        input_embedding = self.model.encode(text, convert_to_numpy=True)
        input_embedding = input_embedding / np.linalg.norm(input_embedding)

        example_embeddings = self._build_example_embeddings()

        # Find most similar examples
        similarities = []
        for i, (example_emb, intent_type) in enumerate(example_embeddings):
            similarity = float(np.dot(input_embedding, example_emb))
            # Get the original text
            example_text = None
            idx = 0
            for intent, examples in INTENT_EXAMPLES.items():
                if idx + len(examples) > i:
                    example_text = examples[i - idx]
                    break
                idx += len(examples)

            similarities.append({
                "intent": intent_type.value,
                "example": example_text,
                "similarity": similarity,
            })

        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "input": text,
            "top_matches": similarities[:top_k],
            "intent_scores": {
                intent.value: score
                for intent, score in self._build_intent_embeddings().items()
            },
        }
