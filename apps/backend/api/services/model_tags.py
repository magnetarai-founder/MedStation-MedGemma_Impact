"""
Model Tag Detection System
Auto-detects model capabilities from model names and metadata

Extracted modules (P2 decomposition):
- model_tag_patterns.py: ModelTag constants, pattern definitions, and metadata
"""

from typing import List, Set, Dict
import re

# Import from extracted module (P2 decomposition)
from api.services.model_tag_patterns import (
    # Constants
    ModelTag,
    # Pattern data
    TAG_PATTERNS,
    MODEL_FAMILY_TAGS,
    # Helper functions
    get_tag_description,
    get_tag_icon,
)


def detect_tags_from_name(model_name: str) -> Set[str]:
    """
    Auto-detect tags from model name using pattern matching

    Args:
        model_name: Model name (e.g., "qwen2.5-coder:32b")

    Returns:
        Set of detected tags
    """
    tags = set()
    name_lower = model_name.lower()

    # Pattern-based detection
    for tag, patterns in TAG_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_lower):
                tags.add(tag)
                break

    # Family-based detection
    for family, family_tags in MODEL_FAMILY_TAGS.items():
        if family in name_lower:
            tags.update(family_tags)
            break

    # If no specific tags detected, assume general
    if not tags:
        tags.add(ModelTag.GENERAL)

    # Remove embedding tag from general tags (embeddings are not chat models)
    if ModelTag.EMBEDDING in tags:
        tags.discard(ModelTag.GENERAL)
        tags.discard(ModelTag.CODE)
        tags.discard(ModelTag.REASONING)

    return tags


def rank_model_for_task(model_name: str, task_tags: List[str]) -> int:
    """
    Rank how suitable a model is for a given task

    Args:
        model_name: Model name
        task_tags: Required tags for the task

    Returns:
        Score (higher is better)
    """
    model_tags = detect_tags_from_name(model_name)

    # Count matching tags
    matches = sum(1 for tag in task_tags if tag in model_tags)

    # Bonus for exact family match
    name_lower = model_name.lower()
    if 'coder' in name_lower and ModelTag.CODE in task_tags:
        matches += 2
    if 'math' in name_lower and ModelTag.MATH in task_tags:
        matches += 2
    if 'vision' in name_lower and ModelTag.VISION in task_tags:
        matches += 2

    return matches


def get_all_tags() -> List[Dict[str, str]]:
    """Get all available tags with metadata (sorted by priority)"""
    return [
        # Core capabilities (most important)
        {
            "id": ModelTag.GENERAL,
            "name": "General",
            "description": get_tag_description(ModelTag.GENERAL),
            "icon": get_tag_icon(ModelTag.GENERAL),
        },
        {
            "id": ModelTag.CHAT,
            "name": "Chat",
            "description": get_tag_description(ModelTag.CHAT),
            "icon": get_tag_icon(ModelTag.CHAT),
        },
        {
            "id": ModelTag.CODE,
            "name": "Code",
            "description": get_tag_description(ModelTag.CODE),
            "icon": get_tag_icon(ModelTag.CODE),
        },
        {
            "id": ModelTag.REASONING,
            "name": "Reasoning",
            "description": get_tag_description(ModelTag.REASONING),
            "icon": get_tag_icon(ModelTag.REASONING),
        },
        {
            "id": ModelTag.DEEP_REASONING,
            "name": "Deep Reasoning",
            "description": get_tag_description(ModelTag.DEEP_REASONING),
            "icon": get_tag_icon(ModelTag.DEEP_REASONING),
        },
        {
            "id": ModelTag.DATA,
            "name": "Data",
            "description": get_tag_description(ModelTag.DATA),
            "icon": get_tag_icon(ModelTag.DATA),
        },
        {
            "id": ModelTag.MATH,
            "name": "Math",
            "description": get_tag_description(ModelTag.MATH),
            "icon": get_tag_icon(ModelTag.MATH),
        },
        {
            "id": ModelTag.ORCHESTRATION,
            "name": "Orchestration",
            "description": get_tag_description(ModelTag.ORCHESTRATION),
            "icon": get_tag_icon(ModelTag.ORCHESTRATION),
        },

        # Specialized capabilities
        {
            "id": ModelTag.VISION,
            "name": "Vision",
            "description": get_tag_description(ModelTag.VISION),
            "icon": get_tag_icon(ModelTag.VISION),
        },
        {
            "id": ModelTag.CREATIVE,
            "name": "Creative",
            "description": get_tag_description(ModelTag.CREATIVE),
            "icon": get_tag_icon(ModelTag.CREATIVE),
        },
        {
            "id": ModelTag.FUNCTION_CALLING,
            "name": "Function Calling",
            "description": get_tag_description(ModelTag.FUNCTION_CALLING),
            "icon": get_tag_icon(ModelTag.FUNCTION_CALLING),
        },
        {
            "id": ModelTag.MULTILINGUAL,
            "name": "Multilingual",
            "description": get_tag_description(ModelTag.MULTILINGUAL),
            "icon": get_tag_icon(ModelTag.MULTILINGUAL),
        },
    ]
