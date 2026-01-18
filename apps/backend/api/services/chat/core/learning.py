"""
Chat service - Learning system operations.

Handles:
- Usage pattern analysis
- Model recommendations
- Recommendation acceptance/rejection
- Optimal model selection for tasks
- Manual usage tracking
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def get_learning_patterns(days: int = 30) -> Dict[str, Any]:
    """Get usage patterns and learning insights"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    patterns = learning_engine.analyze_patterns(days=days)
    return patterns


async def get_recommendations() -> Dict[str, Any]:
    """Get current classification recommendations"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    recommendations = learning_engine.get_recommendations()
    return {"recommendations": recommendations}


async def accept_recommendation(recommendation_id: int, feedback: Optional[str] = None) -> bool:
    """Accept a classification recommendation"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    return learning_engine.accept_recommendation(recommendation_id, feedback)


async def reject_recommendation(recommendation_id: int, feedback: Optional[str] = None) -> bool:
    """Reject a classification recommendation"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    return learning_engine.reject_recommendation(recommendation_id, feedback)


async def get_optimal_model_for_task(task_type: str, top_n: int = 3) -> Dict[str, Any]:
    """Get the optimal models for a specific task type"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    models = learning_engine.get_optimal_model_for_task(task_type, top_n)

    return {
        "task_type": task_type,
        "recommended_models": [
            {"model": model, "confidence": confidence}
            for model, confidence in models
        ]
    }


async def track_usage_manually(
    model_name: str,
    classification: Optional[str] = None,
    session_id: Optional[str] = None,
    message_count: int = 1,
    tokens_used: int = 0,
    task_detected: Optional[str] = None
):
    """Manually track model usage"""
    from api.learning_engine import get_learning_engine

    learning_engine = get_learning_engine()
    learning_engine.track_usage(
        model_name=model_name,
        classification=classification,
        session_id=session_id,
        message_count=message_count,
        tokens_used=tokens_used,
        task_detected=task_detected
    )
    return {"status": "success", "message": "Usage tracked"}
