"""
Recursive Prompt Package

Recursive NLP prompt decomposition for Metal 4 + ANE acceleration:
- Breaks complex prompts into optimized sub-tasks
- Routes to ANE (simple) or Metal GPU (complex) based on complexity
- Provides caching and retry logic with safety limits
"""

from api.recursive_prompt.constants import (
    # Safety constants
    MAX_RECURSION_DEPTH,
    MAX_TOKENS_PER_STEP,
    TIMEOUT_PER_STEP_SECONDS,
    GLOBAL_TIMEOUT_SECONDS,
    MAX_RETRIES,
    BACKOFF_BASE_SECONDS,
    MAX_CONCURRENT_EXECUTIONS,
    # Enums
    TaskComplexity,
    ExecutionBackend,
    # Estimate data
    STEP_TIME_ESTIMATES_MS,
    POWER_ESTIMATES_WATTS,
    COMPLEXITY_TO_BACKEND,
    # Decomposition patterns
    DECOMPOSITION_PATTERNS,
    # Model config
    ANE_MODEL,
    METAL_MODEL,
    ANE_MAX_TOKENS,
    METAL_MAX_TOKENS,
    ESTIMATED_SINGLE_PROMPT_TIME_MS,
    # Helper functions
    get_step_time_estimate,
    get_power_estimate,
    select_backend_for_complexity,
    detect_query_type,
    get_pattern_steps,
    get_all_pattern_types,
    get_pattern_keywords,
)
from api.recursive_prompt.library import (
    PromptStep,
    StepResult,
    RecursiveExecutionPlan,
    PromptDecomposer,
    RecursiveExecutor,
    RecursivePromptLibrary,
    get_recursive_library,
)

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
    # Library classes
    "PromptStep",
    "StepResult",
    "RecursiveExecutionPlan",
    "PromptDecomposer",
    "RecursiveExecutor",
    "RecursivePromptLibrary",
    "get_recursive_library",
]
