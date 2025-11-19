"""
Learning System - Pattern Detection

Pattern initialization and detection helpers:
- initialize_pattern_rules: Creates pattern detection ruleset
- Helper methods for detecting workflow/tool/style patterns

Extracted from learning_system.py during Phase 6.3c modularization.
"""

from typing import Dict, List, Callable


def initialize_pattern_rules() -> Dict[str, Dict[str, Callable]]:
    """
    Initialize pattern detection rules.

    Returns:
        Dict mapping pattern categories to detection functions:
        - tool_preference: Which tools user prefers
        - workflow_preference: User's development workflow patterns
        - style_preference: Output/execution style preferences
    """
    return {
        'tool_preference': {
            'aider_preferred': lambda history: _count_tool_usage(history, 'aider') > 5,
            'ollama_preferred': lambda history: _count_tool_usage(history, 'ollama') > 5,
            'assistant_preferred': lambda history: _count_tool_usage(history, 'assistant') > 3,
        },
        'workflow_preference': {
            'test_first': lambda history: _detect_test_first_pattern(history),
            'documentation_focus': lambda history: _detect_doc_pattern(history),
            'iterative_development': lambda history: _detect_iterative_pattern(history),
        },
        'style_preference': {
            'verbose_output': lambda history: _detect_verbosity_preference(history),
            'minimal_output': lambda history: not _detect_verbosity_preference(history),
            'parallel_execution': lambda history: _detect_parallel_preference(history),
        }
    }


# ============= PATTERN DETECTION HELPERS =============

def _count_tool_usage(history: List, tool: str) -> int:
    """Count how many times a tool was used in history"""
    return sum(1 for h in history if h.get('tool') == tool)


def _detect_test_first_pattern(history: List) -> bool:
    """
    Detect if user follows test-first development.

    Looks for patterns where test files are created before implementation.
    """
    # Simplified for now - could analyze command sequence
    return False


def _detect_doc_pattern(history: List) -> bool:
    """
    Detect if user prioritizes documentation.

    Returns True if >20% of commands involve documentation.
    """
    doc_commands = sum(1 for h in history if 'doc' in h.get('command', '').lower())
    return doc_commands > len(history) * 0.2


def _detect_iterative_pattern(history: List) -> bool:
    """
    Detect iterative development style.

    Looks for repeated edit-test cycles.
    """
    # Simplified for now - could analyze edit/test command patterns
    return False


def _detect_verbosity_preference(history: List) -> bool:
    """
    Detect if user prefers verbose output.

    Would analyze command flags and patterns in real implementation.
    """
    # Default to verbose for now
    return True


def _detect_parallel_preference(history: List) -> bool:
    """
    Detect if user prefers parallel execution.

    Checks for parallel flags in commands.
    """
    # Simplified for now - could check for parallel/concurrent flags
    return False
