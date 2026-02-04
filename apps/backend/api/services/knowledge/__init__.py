"""
Knowledge Extraction and Learning Module

Extracts and stores knowledge from conversations:
- Topics discussed
- Code patterns discovered
- Problem-solution pairs
- User preferences

This gives MagnetarCode a persistent memory that improves over time,
something Claude Code and Codex don't have.
"""

from .extractor import (
    KnowledgeExtractor,
    ExtractionResult,
    Topic,
    CodePattern,
    ProblemSolution,
    create_knowledge_extractor,
)
from .store import (
    KnowledgeStore,
    KnowledgeQuery,
    KnowledgeEntry,
    get_knowledge_store,
)
from .learner import (
    PreferenceLearner,
    UserPreferences,
    LearnedPattern,
    get_preference_learner,
)

__all__ = [
    # Extractor
    "KnowledgeExtractor",
    "ExtractionResult",
    "Topic",
    "CodePattern",
    "ProblemSolution",
    "create_knowledge_extractor",
    # Store
    "KnowledgeStore",
    "KnowledgeQuery",
    "KnowledgeEntry",
    "get_knowledge_store",
    # Learner
    "PreferenceLearner",
    "UserPreferences",
    "LearnedPattern",
    "get_preference_learner",
]
