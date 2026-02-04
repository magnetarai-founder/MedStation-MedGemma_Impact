"""
Smart Refactoring System

Provides intelligent code refactoring suggestions and transformations:
- Extract Method: Identify code blocks that should be functions
- Extract Class: Identify related functions that should be a class
- Dead Code Detection: Find unused functions, variables, imports
- Import Optimization: Organize, dedupe, remove unused imports
- Rename Symbol: Safely rename across entire codebase
- Inline Variable: Replace variable with its value where appropriate
- Move to File: Suggest better file locations for code

All refactorings are AST-based with safe preview-before-apply.
"""

from .engine import (
    RefactoringEngine,
    RefactoringSuggestion,
    RefactoringType,
    get_refactoring_engine,
)

__all__ = [
    "RefactoringEngine",
    "RefactoringSuggestion",
    "RefactoringType",
    "get_refactoring_engine",
]
