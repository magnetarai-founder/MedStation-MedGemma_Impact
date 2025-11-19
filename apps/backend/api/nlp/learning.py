"""
Learning templates (LEARNING category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all LEARNING templates."""
    return [
        NLPTemplate(
            id="LN_001",
            name="Learn Pattern",
            category=IntentCategory.LEARNING,
            patterns=[
                r"(?:learn|remember)\s+(?:that\s+)?(.+)",
                r"(?:next time|always)\s+(.+)",
                r"(?:my\s+)?preference\s+(?:is\s+)?(.+)"
            ],
            keywords=["learn", "remember", "preference", "always"],
            entities=["pattern", "context", "preference_type"],
            response_template="Learning: {pattern}",
            tool_suggestions=["learning_system"],
            examples=[
                "remember that I prefer tabs over spaces",
                "always use pytest for testing",
                "my preference is qwen for code generation"
            ]
        ),

        NLPTemplate(
            id="LN_002",
            name="Recall Information",
            category=IntentCategory.LEARNING,
            patterns=[
                r"(?:what\s+)?(?:do you\s+)?remember\s+(?:about\s+)?(.+)",
                r"(?:what\s+)?(?:did I\s+)?(?:say|tell you)\s+about\s+(.+)",
                r"(?:recall|show)\s+(?:my\s+)?(?:previous|past)\s+(.+)"
            ],
            keywords=["remember", "recall", "previous", "history"],
            entities=["memory_query", "time_range"],
            response_template="Recalling information about {memory_query}",
            tool_suggestions=["memory", "history"],
            examples=[
                "what do you remember about the auth system",
                "what did I say about testing",
                "recall previous commands"
            ]
        ),

        NLPTemplate(
            id="LN_003",
            name="Improve Performance",
            category=IntentCategory.LEARNING,
            patterns=[
                r"(?:how can you|can you)\s+(?:improve|get better)\s+(?:at\s+)?(.+)",
                r"(?:learn to|learn how to)\s+(.+)\s+better",
                r"(?:optimize|improve)\s+(?:your\s+)?performance\s+(?:on\s+)?(.+)"
            ],
            keywords=["improve", "better", "optimize", "performance"],
            entities=["improvement_area", "metrics"],
            response_template="Analyzing how to improve {improvement_area}",
            tool_suggestions=["learning_system", "analytics"],
            examples=[
                "how can you improve at debugging",
                "learn to write tests better",
                "optimize your code generation performance"
            ]
        ),

        NLPTemplate(
            id="ML_001",
            name="Train Model",
            category=IntentCategory.LEARNING,
            patterns=[
                r"train\s+(?:a\s+)?(?:model|classifier|network)\s+(?:on|for|with)\s+(.+)",
                r"(?:machine\s+)?learning\s+(?:model\s+)?(?:for\s+)?(.+)"
            ],
            keywords=["train", "model", "machine learning", "ml"],
            entities=["model_type", "dataset"],
            response_template="Training model for {model_type}",
            tool_suggestions=["scikit-learn", "tensorflow", "pytorch"],
            examples=["train model on dataset", "train classifier for spam detection"]
        ),

        NLPTemplate(
            id="ML_002",
            name="Evaluate Model",
            category=IntentCategory.LEARNING,
            patterns=[
                r"evaluate\s+(?:the\s+)?model",
                r"(?:test|validate)\s+(?:model\s+)?performance",
                r"(?:check|measure)\s+accuracy"
            ],
            keywords=["evaluate", "test", "accuracy", "performance"],
            entities=["model_name", "metrics"],
            response_template="Evaluating model performance",
            tool_suggestions=["scikit-learn", "metrics"],
            examples=["evaluate the model", "test model performance", "check accuracy"]
        ),
    ]
