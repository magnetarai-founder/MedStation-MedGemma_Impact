"""
Recursive Prompt Execution Constants and Patterns

Static data for recursive prompt decomposition and execution.
Extracted from recursive_prompt_library.py during P2 decomposition.

Contains:
- Safety limit constants (recursion, timeout, retries)
- TaskComplexity enum (SIMPLE, MODERATE, COMPLEX)
- ExecutionBackend enum (ANE, METAL_GPU, CPU)
- DECOMPOSITION_PATTERNS: Query type patterns for task breakdown
- Time and power estimation data
- Helper functions for estimation
"""

from enum import Enum
from typing import Dict, Any, List


# ============================================
# SAFETY LIMIT CONSTANTS
# ============================================

MAX_RECURSION_DEPTH: int = 5
"""Maximum recursion depth to prevent infinite loops"""

MAX_TOKENS_PER_STEP: int = 2000
"""Maximum token usage per execution step"""

TIMEOUT_PER_STEP_SECONDS: int = 15
"""Kill individual steps that take too long"""

GLOBAL_TIMEOUT_SECONDS: int = 60
"""Kill entire query if total execution exceeds this"""

MAX_RETRIES: int = 2
"""Number of retry attempts for failed steps"""

BACKOFF_BASE_SECONDS: float = 1.0
"""Base for exponential backoff between retries (1s, 2s, 4s, ...)"""

MAX_CONCURRENT_EXECUTIONS: int = 3
"""Limit concurrent execution branches"""


# ============================================
# TASK COMPLEXITY ENUM
# ============================================

class TaskComplexity(Enum):
    """
    Complexity levels for routing to ANE vs Metal GPU

    Complexity affects:
    - Which backend is selected
    - Estimated execution time
    - Power consumption

    Examples:
        >>> TaskComplexity.SIMPLE.value
        'simple'
        >>> complexity = TaskComplexity.COMPLEX
        >>> get_step_time_estimate(complexity)
        3000.0
    """
    SIMPLE = "simple"      # ANE: 0.1-0.5s, <0.5W
    MODERATE = "moderate"  # Metal: 0.5-2s, 2-5W
    COMPLEX = "complex"    # Metal: 2-10s, 5-10W


# ============================================
# EXECUTION BACKEND ENUM
# ============================================

class ExecutionBackend(Enum):
    """
    Where to run the inference

    Selection is based on TaskComplexity:
    - SIMPLE tasks → ANE (low power, fast for small tasks)
    - MODERATE/COMPLEX tasks → Metal GPU (high throughput)
    - CPU is fallback when accelerators unavailable

    Examples:
        >>> ExecutionBackend.ANE.value
        'ane'
        >>> backend = ExecutionBackend.METAL_GPU
        >>> get_power_estimate(backend)
        4.0
    """
    ANE = "ane"           # Apple Neural Engine (low power, fast for small tasks)
    METAL_GPU = "metal"   # Metal GPU (high power, fast for big tasks)
    CPU = "cpu"           # CPU fallback


# ============================================
# TIME AND POWER ESTIMATES
# ============================================

STEP_TIME_ESTIMATES_MS: Dict[TaskComplexity, float] = {
    TaskComplexity.SIMPLE: 300.0,      # 0.3s on ANE
    TaskComplexity.MODERATE: 1000.0,   # 1s on Metal
    TaskComplexity.COMPLEX: 3000.0,    # 3s on Metal
}
"""Estimated execution time in milliseconds by complexity level"""


POWER_ESTIMATES_WATTS: Dict[ExecutionBackend, float] = {
    ExecutionBackend.ANE: 0.2,        # Very low power
    ExecutionBackend.METAL_GPU: 4.0,  # Moderate power
    ExecutionBackend.CPU: 2.0,        # Low-moderate power
}
"""Estimated power usage in watts by backend"""


COMPLEXITY_TO_BACKEND: Dict[TaskComplexity, ExecutionBackend] = {
    TaskComplexity.SIMPLE: ExecutionBackend.ANE,
    TaskComplexity.MODERATE: ExecutionBackend.METAL_GPU,
    TaskComplexity.COMPLEX: ExecutionBackend.METAL_GPU,
}
"""Default backend selection by complexity level"""


# ============================================
# DECOMPOSITION PATTERNS
# ============================================

DECOMPOSITION_PATTERNS: Dict[str, Dict[str, Any]] = {
    'data_analysis': {
        'keywords': ['analyze', 'data', 'sales', 'trends', 'patterns'],
        'steps': [
            {'description': 'Identify data requirements', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Generate SQL queries', 'complexity': TaskComplexity.MODERATE},
            {'description': 'Execute analysis', 'complexity': TaskComplexity.COMPLEX},
            {'description': 'Interpret results', 'complexity': TaskComplexity.SIMPLE},
        ]
    },
    'missionary_report': {
        'keywords': ['field', 'report', 'missionary', 'health', 'security'],
        'steps': [
            {'description': 'Extract key information', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Categorize by type', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Identify risks/concerns', 'complexity': TaskComplexity.MODERATE},
            {'description': 'Generate recommendations', 'complexity': TaskComplexity.MODERATE},
        ]
    },
    'message_compose': {
        'keywords': ['send', 'message', 'email', 'update', 'notify'],
        'steps': [
            {'description': 'Identify recipients', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Detect language preferences', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Compose message', 'complexity': TaskComplexity.MODERATE},
            {'description': 'Translate if needed', 'complexity': TaskComplexity.MODERATE},
        ]
    },
    'prediction': {
        'keywords': ['predict', 'forecast', 'estimate', 'project'],
        'steps': [
            {'description': 'Gather historical data', 'complexity': TaskComplexity.MODERATE},
            {'description': 'Identify trends', 'complexity': TaskComplexity.COMPLEX},
            {'description': 'Apply forecasting model', 'complexity': TaskComplexity.COMPLEX},
            {'description': 'Generate prediction', 'complexity': TaskComplexity.SIMPLE},
        ]
    },
    'general': {
        'keywords': [],  # Fallback - matches when no other pattern matches
        'steps': [
            {'description': 'Understand question', 'complexity': TaskComplexity.SIMPLE},
            {'description': 'Generate answer', 'complexity': TaskComplexity.MODERATE},
        ]
    }
}
"""
Query decomposition patterns for recursive prompt execution.

Each pattern contains:
- keywords: List of trigger words that identify this query type
- steps: List of execution steps with complexity levels

The 'general' pattern is the fallback when no keywords match.
"""


# ============================================
# MODEL CONFIGURATION
# ============================================

ANE_MODEL: str = "qwen2.5-coder:1.5b-instruct"
"""Small/fast model for ANE execution (simple tasks)"""

METAL_MODEL: str = "qwen2.5-coder:7b-instruct"
"""Larger model for Metal GPU execution (moderate/complex tasks)"""

ANE_MAX_TOKENS: int = 128
"""Token limit for ANE execution (speed optimization)"""

METAL_MAX_TOKENS: int = 512
"""Token limit for Metal GPU execution"""

ESTIMATED_SINGLE_PROMPT_TIME_MS: float = 8000.0
"""Estimated time for a complex single-prompt execution (for time-saved calculation)"""


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_step_time_estimate(complexity: TaskComplexity) -> float:
    """
    Get estimated execution time for a complexity level.

    Args:
        complexity: Task complexity level

    Returns:
        Estimated time in milliseconds

    Examples:
        >>> get_step_time_estimate(TaskComplexity.SIMPLE)
        300.0
        >>> get_step_time_estimate(TaskComplexity.COMPLEX)
        3000.0
    """
    return STEP_TIME_ESTIMATES_MS.get(complexity, 1000.0)


def get_power_estimate(backend: ExecutionBackend) -> float:
    """
    Get estimated power usage for a backend.

    Args:
        backend: Execution backend

    Returns:
        Estimated power in watts

    Examples:
        >>> get_power_estimate(ExecutionBackend.ANE)
        0.2
        >>> get_power_estimate(ExecutionBackend.METAL_GPU)
        4.0
    """
    return POWER_ESTIMATES_WATTS.get(backend, 2.0)


def select_backend_for_complexity(complexity: TaskComplexity) -> ExecutionBackend:
    """
    Select optimal backend based on task complexity.

    Args:
        complexity: Task complexity level

    Returns:
        Recommended execution backend

    Examples:
        >>> select_backend_for_complexity(TaskComplexity.SIMPLE)
        <ExecutionBackend.ANE: 'ane'>
        >>> select_backend_for_complexity(TaskComplexity.COMPLEX)
        <ExecutionBackend.METAL_GPU: 'metal'>
    """
    return COMPLEXITY_TO_BACKEND.get(complexity, ExecutionBackend.METAL_GPU)


def detect_query_type(query: str) -> str:
    """
    Detect the query type based on keywords.

    Args:
        query: User query string

    Returns:
        Pattern type name (e.g., 'data_analysis', 'prediction', 'general')

    Examples:
        >>> detect_query_type("Analyze the sales data for Q4")
        'data_analysis'
        >>> detect_query_type("What is the weather today?")
        'general'
    """
    query_lower = query.lower()

    for pattern_type, pattern_data in DECOMPOSITION_PATTERNS.items():
        if pattern_type == 'general':
            continue
        keywords = pattern_data['keywords']
        if any(kw in query_lower for kw in keywords):
            return pattern_type

    return 'general'


def get_pattern_steps(pattern_type: str) -> List[Dict[str, Any]]:
    """
    Get the execution steps for a pattern type.

    Args:
        pattern_type: Pattern type name

    Returns:
        List of step definitions with description and complexity

    Examples:
        >>> steps = get_pattern_steps('data_analysis')
        >>> len(steps)
        4
        >>> steps[0]['description']
        'Identify data requirements'
    """
    pattern = DECOMPOSITION_PATTERNS.get(pattern_type, DECOMPOSITION_PATTERNS['general'])
    return pattern['steps']


def get_all_pattern_types() -> List[str]:
    """Get list of all available pattern type names."""
    return list(DECOMPOSITION_PATTERNS.keys())


def get_pattern_keywords(pattern_type: str) -> List[str]:
    """Get keywords for a specific pattern type."""
    pattern = DECOMPOSITION_PATTERNS.get(pattern_type)
    return pattern['keywords'] if pattern else []


__all__ = [
    # Safety constants
    "MAX_RECURSION_DEPTH",
    "MAX_TOKENS_PER_STEP",
    "TIMEOUT_PER_STEP_SECONDS",
    "GLOBAL_TIMEOUT_SECONDS",
    "MAX_RETRIES",
    "BACKOFF_BASE_SECONDS",
    "MAX_CONCURRENT_EXECUTIONS",
    # Enums
    "TaskComplexity",
    "ExecutionBackend",
    # Estimate data
    "STEP_TIME_ESTIMATES_MS",
    "POWER_ESTIMATES_WATTS",
    "COMPLEXITY_TO_BACKEND",
    # Decomposition patterns
    "DECOMPOSITION_PATTERNS",
    # Model config
    "ANE_MODEL",
    "METAL_MODEL",
    "ANE_MAX_TOKENS",
    "METAL_MAX_TOKENS",
    "ESTIMATED_SINGLE_PROMPT_TIME_MS",
    # Helper functions
    "get_step_time_estimate",
    "get_power_estimate",
    "select_backend_for_complexity",
    "detect_query_type",
    "get_pattern_steps",
    "get_all_pattern_types",
    "get_pattern_keywords",
]
