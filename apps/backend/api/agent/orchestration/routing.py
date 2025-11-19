"""
Agent Orchestration - Intent Routing

User input classification and routing decisions:
- Intent classification (shell, code_edit, question)
- Confidence scoring
- Model hint suggestions
- Next action determination
- Learning-aware tool selection (Phase A)

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
from typing import Optional, Dict

try:
    from ..intent_classifier import Phi3IntentClassifier as IntentClassifier
except ImportError:
    from intent_classifier import Phi3IntentClassifier as IntentClassifier

try:
    from .models import RouteResponse
except ImportError:
    from models import RouteResponse

try:
    from .config import get_agent_config
except ImportError:
    from config import get_agent_config

# Learning system import with fallback
try:
    from api.learning_system import LearningSystem
except ImportError:
    try:
        from learning_system import LearningSystem
    except ImportError:
        LearningSystem = None  # Graceful degradation if learning system unavailable

logger = logging.getLogger(__name__)

# Candidate tools for learning-aware routing
CANDIDATE_TOOLS = ["aider", "continue", "assistant", "system"]

# Tool to model config key mapping
TOOL_MODEL_KEYS = {
    "aider": "coder",
    "assistant": "planner",
    "system": "committer",
    "continue": "coder",  # use same as coder for now
}

# Strong recommendation threshold
STRONG_RATE_THRESHOLD = 0.7

# Module-level singleton for LearningSystem
_learning_system: Optional[LearningSystem] = None


def get_learning_system() -> Optional[LearningSystem]:
    """
    Get or create module-level LearningSystem singleton.

    Returns:
        LearningSystem instance or None if unavailable
    """
    global _learning_system
    if LearningSystem is None:
        return None
    if _learning_system is None:
        try:
            _learning_system = LearningSystem()
        except Exception as e:
            logger.warning(f"Failed to initialize LearningSystem: {e}")
            return None
    return _learning_system


def route_input_logic(text: str, user_id: Optional[str] = None) -> RouteResponse:
    """
    Route user input to determine intent with learning-aware tool selection.

    Uses IntentClassifier to classify input and LearningSystem to recommend
    tools/models based on historical success rates and user preferences.

    Args:
        text: User's natural language input
        user_id: Optional user ID for personalized recommendations

    Returns:
        RouteResponse with:
        - intent: Detected intent type (shell, code_edit, question)
        - confidence: Confidence score 0-1
        - model_hint: Suggested model for task (learning-enhanced)
        - next_action: Suggested next step
    """
    # Use intent classifier
    classifier = IntentClassifier()
    intent_result = classifier.classify(text)

    # Map to our response format
    intent_type = intent_result.get('type', 'question')
    confidence = intent_result.get('confidence', 0.5)

    # Base model hints based on intent (fallback behavior)
    model_hint = None
    if intent_type == 'code_edit':
        model_hint = 'qwen2.5-coder:32b'
    elif intent_type == 'question':
        model_hint = 'deepseek-r1:32b'

    # === Learning-Aware Tool Selection (Phase A) ===
    learning = get_learning_system()
    if learning is not None:
        try:
            # Compute success rates for each candidate tool
            rates: Dict[str, float] = {}
            for tool in CANDIDATE_TOOLS:
                try:
                    rate = learning.get_success_rate(text, tool)
                except Exception:
                    rate = 0.5  # Default if error
                rates[tool] = rate

            # Select best tool based on success rate
            best_tool, best_rate = max(rates.items(), key=lambda kv: kv[1])

            # Consult explicit user preferences
            try:
                prefs = learning.get_preferences("tool")
                if prefs:
                    top_pref = prefs[0]
                    if top_pref.preference in CANDIDATE_TOOLS and top_pref.confidence > 0.8:
                        # Strong user preference - override if rate not much worse
                        if rates.get(top_pref.preference, 0.0) >= best_rate - 0.1:
                            best_tool = top_pref.preference
                            best_rate = rates[best_tool]
            except Exception:
                pass  # Preferences not available

            # Determine if this is a strong recommendation
            strong_recommendation = best_rate >= STRONG_RATE_THRESHOLD

            # Map tool to model using config if strong recommendation
            if strong_recommendation:
                cfg = get_agent_config()
                models_cfg = cfg.get("models", {})
                model_key = TOOL_MODEL_KEYS.get(best_tool)
                if model_key and model_key in models_cfg:
                    # Override base model_hint with learning recommendation
                    model_hint = models_cfg[model_key]

            # Log learning info for observability
            logger.info(
                "Agent routing learning info",
                extra={
                    "user_id": user_id,
                    "best_tool": best_tool,
                    "best_rate": round(best_rate, 2),
                    "strong_recommendation": strong_recommendation,
                    "rates": {k: round(v, 2) for k, v in rates.items()}
                }
            )

        except Exception as e:
            # Learning system error - fall back to base behavior
            logger.warning(f"Learning-aware routing failed, using base behavior: {e}")

    # Next action suggestion
    next_action = "call /agent/plan" if intent_type == 'code_edit' else "answer directly"

    return RouteResponse(
        intent=intent_type,
        confidence=confidence,
        model_hint=model_hint,
        next_action=next_action
    )
