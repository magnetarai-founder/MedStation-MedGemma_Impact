"""
Compatibility Shim for Learning Engine

The implementation now lives in the `api.learning` package:
- api.learning.engine: LearningEngine class

This shim maintains backward compatibility.
"""

from api.learning.engine import LearningEngine, get_learning_engine

__all__ = [
    "LearningEngine",
    "get_learning_engine",
]
