"""
Model Tag Detection Patterns and Constants

Static data for model capability tag detection.
Extracted from model_tags.py during P2 decomposition.

Contains:
- ModelTag class with string constants for capability tags
- TAG_PATTERNS: Regex patterns for detecting tags from model names
- MODEL_FAMILY_TAGS: Known model families and their default tags
- TAG_DESCRIPTIONS: Human-readable descriptions for each tag
- TAG_ICONS: SF Symbol icons for UI display
- Helper functions for tag lookup
"""

from typing import Dict, List


# ============================================
# MODEL TAG CONSTANTS
# ============================================

class ModelTag:
    """
    Model capability tags - predefined categories

    Tags are used to classify models by their capabilities for:
    - Task routing (matching models to appropriate tasks)
    - UI filtering (showing relevant models)
    - Performance optimization (selecting efficient models)

    Examples:
        >>> ModelTag.CODE
        'code'
        >>> task_tags = [ModelTag.CODE, ModelTag.REASONING]
    """
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


# ============================================
# TAG DETECTION PATTERNS
# ============================================

TAG_PATTERNS: Dict[str, List[str]] = {
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
"""
Regex patterns for detecting model tags from model names.

Each tag maps to a list of regex patterns. If any pattern matches
the model name (case-insensitive), the tag is assigned.

Examples:
    >>> import re
    >>> any(re.search(p, 'qwen2.5-coder:32b') for p in TAG_PATTERNS[ModelTag.CODE])
    True
"""


# ============================================
# MODEL FAMILY TAGS
# ============================================

MODEL_FAMILY_TAGS: Dict[str, List[str]] = {
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
"""
Default tags for known model families.

When a model name contains a family name, these tags are
automatically added in addition to pattern-based detection.

Examples:
    >>> 'llama' in 'llama3.1:8b'.lower()
    True
    >>> MODEL_FAMILY_TAGS['llama']
    ['general']
"""


# ============================================
# TAG METADATA
# ============================================

TAG_DESCRIPTIONS: Dict[str, str] = {
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
"""Human-readable descriptions for each tag."""


TAG_ICONS: Dict[str, str] = {
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
"""SF Symbol icon names for each tag (for macOS/iOS UI)."""


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_tag_description(tag: str) -> str:
    """
    Get human-readable description for a tag.

    Args:
        tag: Tag string (e.g., ModelTag.CODE)

    Returns:
        Description string, or formatted tag name if not found

    Examples:
        >>> get_tag_description(ModelTag.CODE)
        'Code generation & analysis'
        >>> get_tag_description('unknown-tag')
        'Unknown Tag'
    """
    return TAG_DESCRIPTIONS.get(tag, tag.replace("-", " ").title())


def get_tag_icon(tag: str) -> str:
    """
    Get SF Symbol name for a tag.

    Args:
        tag: Tag string (e.g., ModelTag.VISION)

    Returns:
        SF Symbol name, or 'tag' as fallback

    Examples:
        >>> get_tag_icon(ModelTag.VISION)
        'eye'
        >>> get_tag_icon('unknown')
        'tag'
    """
    return TAG_ICONS.get(tag, "tag")


def get_all_tag_constants() -> List[str]:
    """
    Get all defined tag constant values.

    Returns:
        List of all tag strings

    Examples:
        >>> tags = get_all_tag_constants()
        >>> ModelTag.CODE in tags
        True
    """
    return [
        ModelTag.GENERAL,
        ModelTag.REASONING,
        ModelTag.DEEP_REASONING,
        ModelTag.MATH,
        ModelTag.DATA,
        ModelTag.CODE,
        ModelTag.CHAT,
        ModelTag.ORCHESTRATION,
        ModelTag.VISION,
        ModelTag.CREATIVE,
        ModelTag.FUNCTION_CALLING,
        ModelTag.MULTILINGUAL,
        ModelTag.REFACTOR,
        ModelTag.RESEARCH,
        ModelTag.SUMMARIZATION,
        ModelTag.EMBEDDING,
    ]


__all__ = [
    # Constants
    "ModelTag",
    # Pattern data
    "TAG_PATTERNS",
    "MODEL_FAMILY_TAGS",
    # Metadata
    "TAG_DESCRIPTIONS",
    "TAG_ICONS",
    # Helper functions
    "get_tag_description",
    "get_tag_icon",
    "get_all_tag_constants",
]
