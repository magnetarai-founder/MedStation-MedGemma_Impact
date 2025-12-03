"""
Model Tag Detection System
Auto-detects model capabilities from model names and metadata
"""

from typing import List, Set, Dict
import re


# Tag definitions (Updated for MagnetarStudio)
class ModelTag:
    """Model capability tags - predefined categories"""
    # Core capabilities
    GENERAL = "general"
    REASONING = "reasoning"
    DEEP_REASONING = "deep-reasoning"  # Advanced CoT (R1, o1)
    MATH = "math"
    DATA = "data"
    CODE = "code"
    CHAT = "chat"
    ORCHESTRATION = "orchestration"  # Model routing capability

    # Specialized capabilities
    VISION = "vision"
    CREATIVE = "creative"
    FUNCTION_CALLING = "function-calling"
    MULTILINGUAL = "multilingual"

    # Deprecated/legacy tags (kept for backwards compatibility)
    REFACTOR = "refactor"  # Use CODE instead
    RESEARCH = "research"  # Use REASONING + DATA instead
    SUMMARIZATION = "summarization"  # Use GENERAL instead
    EMBEDDING = "embedding"  # Special type, not for chat models


# Pattern-based tag detection (Updated for MagnetarStudio)
TAG_PATTERNS = {
    ModelTag.CODE: [
        r'code',
        r'coder',
        r'codestral',
        r'starcoder',
        r'deepseek-coder',
        r'qwen.*coder',
        r'phind',
        r'wizardcoder',
    ],
    ModelTag.REASONING: [
        r'think',
        r'reason',
        r'qwen.*plus',
        r'pro',  # Often indicates reasoning capability
        r'phi',  # phi models good at reasoning
    ],
    ModelTag.DEEP_REASONING: [
        r'deepthink',
        r'deepseek-r1',
        r'o1',
        r'r1',
        r'chain.*thought',
        r'cot',
    ],
    ModelTag.MATH: [
        r'math',
        r'mathstral',
        r'llemma',
        r'minerva',
    ],
    ModelTag.DATA: [
        r'data',
        r'analyst',
        r'sql',
        r'phi',  # phi trained on data analysis
    ],
    ModelTag.CHAT: [
        r'chat',
        r'instruct',
        r'llama',
        r'mistral',
    ],
    ModelTag.ORCHESTRATION: [
        r'qwen2.5-coder:3b',  # Small, fast orchestrator
        r'phi',  # Good for routing decisions
    ],
    ModelTag.VISION: [
        r'vision',
        r'llava',
        r'bakllava',
        r'minicpm-v',
        r'moondream',
        r'cogvlm',
    ],
    ModelTag.CREATIVE: [
        r'creative',
        r'writer',
        r'storytell',
        r'mixtral',  # Known for creative writing
    ],
    ModelTag.EMBEDDING: [
        r'embed',
        r'embedding',
        r'nomic-embed',
        r'mxbai-embed',
        r'bge-',
        r'e5-',
        r'gte-',
        r'sentence-',
    ],
    ModelTag.MULTILINGUAL: [
        r'multilingual',
        r'polyglot',
        r'qwen',  # Known for good multilingual support
        r'aya',
    ],
    ModelTag.FUNCTION_CALLING: [
        r'function',
        r'tool',
        r'gorilla',
        r'functionary',
    ],
}


# Model families with known capabilities
MODEL_FAMILY_TAGS = {
    'llama': [ModelTag.GENERAL],
    'mistral': [ModelTag.GENERAL, ModelTag.REASONING],
    'mixtral': [ModelTag.GENERAL, ModelTag.CREATIVE, ModelTag.REASONING],
    'qwen': [ModelTag.GENERAL, ModelTag.MULTILINGUAL, ModelTag.REASONING],
    'gemma': [ModelTag.GENERAL],
    'phi': [ModelTag.GENERAL, ModelTag.REASONING],
    'neural-chat': [ModelTag.GENERAL],
    'openchat': [ModelTag.GENERAL],
    'dolphin': [ModelTag.GENERAL, ModelTag.FUNCTION_CALLING],
    'orca': [ModelTag.GENERAL, ModelTag.REASONING],
    'yi': [ModelTag.GENERAL, ModelTag.MULTILINGUAL],
}


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


def get_tag_description(tag: str) -> str:
    """Get human-readable description for a tag"""
    descriptions = {
        # Core capabilities
        ModelTag.GENERAL: "General conversation",
        ModelTag.REASONING: "Complex reasoning & thinking",
        ModelTag.DEEP_REASONING: "Advanced chain-of-thought reasoning",
        ModelTag.MATH: "Mathematical problem solving",
        ModelTag.DATA: "Data analysis & SQL",
        ModelTag.CODE: "Code generation & analysis",
        ModelTag.CHAT: "Conversational AI",
        ModelTag.ORCHESTRATION: "Model routing & orchestration",

        # Specialized capabilities
        ModelTag.VISION: "Image understanding",
        ModelTag.CREATIVE: "Creative writing",
        ModelTag.FUNCTION_CALLING: "Tool use & function calling",
        ModelTag.MULTILINGUAL: "Multiple languages",

        # Deprecated
        ModelTag.REFACTOR: "Code refactoring",
        ModelTag.RESEARCH: "Research & analysis",
        ModelTag.SUMMARIZATION: "Text summarization",
        ModelTag.EMBEDDING: "Text embeddings",
    }
    return descriptions.get(tag, tag.replace("-", " ").title())


def get_tag_icon(tag: str) -> str:
    """Get SF Symbol name for a tag"""
    icons = {
        # Core capabilities
        ModelTag.GENERAL: "bubble.left",
        ModelTag.REASONING: "brain",
        ModelTag.DEEP_REASONING: "brain.head.profile",
        ModelTag.MATH: "function",
        ModelTag.DATA: "chart.bar",
        ModelTag.CODE: "chevron.left.forwardslash.chevron.right",
        ModelTag.CHAT: "message",
        ModelTag.ORCHESTRATION: "arrow.triangle.branch",

        # Specialized capabilities
        ModelTag.VISION: "eye",
        ModelTag.CREATIVE: "pencil.and.outline",
        ModelTag.FUNCTION_CALLING: "wrench.and.screwdriver",
        ModelTag.MULTILINGUAL: "globe",

        # Deprecated
        ModelTag.REFACTOR: "arrow.triangle.2.circlepath",
        ModelTag.RESEARCH: "magnifyingglass",
        ModelTag.SUMMARIZATION: "doc.text",
        ModelTag.EMBEDDING: "textformat",
    }
    return icons.get(tag, "tag")


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
