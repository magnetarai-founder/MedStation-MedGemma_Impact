"""
Compatibility Shim for Recursive Prompt Library

The implementation now lives in the `api.recursive_prompt` package:
- api.recursive_prompt.library: Classes and singleton factory

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
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
    "PromptStep",
    "StepResult",
    "RecursiveExecutionPlan",
    "PromptDecomposer",
    "RecursiveExecutor",
    "RecursivePromptLibrary",
    "get_recursive_library",
]
