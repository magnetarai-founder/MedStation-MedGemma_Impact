"""
Agent Orchestration - Intent Routing

User input classification and routing decisions:
- Intent classification (shell, code_edit, question)
- Confidence scoring
- Model hint suggestions
- Next action determination

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
from typing import Optional

try:
    from ..intent_classifier import Phi3IntentClassifier as IntentClassifier
except ImportError:
    from intent_classifier import Phi3IntentClassifier as IntentClassifier

try:
    from .models import RouteResponse
except ImportError:
    from models import RouteResponse

logger = logging.getLogger(__name__)


def route_input_logic(text: str) -> RouteResponse:
    """
    Route user input to determine intent.

    Uses IntentClassifier to classify input and map to response format.

    Args:
        text: User's natural language input

    Returns:
        RouteResponse with:
        - intent: Detected intent type (shell, code_edit, question)
        - confidence: Confidence score 0-1
        - model_hint: Suggested model for task
        - next_action: Suggested next step
    """
    # Use intent classifier
    classifier = IntentClassifier()
    intent_result = classifier.classify(text)

    # Map to our response format
    intent_type = intent_result.get('type', 'question')
    confidence = intent_result.get('confidence', 0.5)

    # Model hints based on intent
    model_hint = None
    if intent_type == 'code_edit':
        model_hint = 'qwen2.5-coder:32b'
    elif intent_type == 'question':
        model_hint = 'deepseek-r1:32b'

    # Next action suggestion
    next_action = "call /agent/plan" if intent_type == 'code_edit' else "answer directly"

    return RouteResponse(
        intent=intent_type,
        confidence=confidence,
        model_hint=model_hint,
        next_action=next_action
    )
