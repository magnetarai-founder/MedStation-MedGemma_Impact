#!/usr/bin/env python3
"""
Example usage of the Smart Refactoring System

This demonstrates how to use the refactoring engine to:
- Analyze files for refactoring opportunities
- Get specific refactoring suggestions
- Preview changes before applying
- Apply refactorings safely
"""

import asyncio
from pathlib import Path

from api.services.refactoring import (
    RefactoringEngine,
    RefactoringType,
    get_refactoring_engine,
)


async def example_analyze_file():
    """Example: Analyze a file for all refactoring opportunities."""
    print("=" * 80)
    print("Example 1: Analyze File for Refactoring Opportunities")
    print("=" * 80)

    # Initialize engine
    engine = get_refactoring_engine(workspace_root="/Users/indiedevhipps/Documents/MagnetarCode")

    # Analyze a file
    file_path = Path(__file__).parent / "engine.py"
    suggestions = engine.analyze_file(file_path)

    print(f"\nAnalyzing: {file_path}")
    print(f"Found {len(suggestions)} refactoring suggestions:\n")

    # Show top 5 suggestions
    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"{i}. {suggestion.type.value.upper()}")
        print(f"   Location: {suggestion.location}")
        print(f"   Description: {suggestion.description}")
        print(f"   Confidence: {suggestion.confidence:.1%}")
        print(f"   Impact: {suggestion.impact_score:.1%}")
        print(f"   Effort: {suggestion.effort_score:.1%}")
        print(f"   Safety: {suggestion.safety_score:.1%}")
        print(f"   Reasoning: {suggestion.reasoning}")
        print()


async def example_dead_code_detection():
    """Example: Find dead code in a file."""
    print("=" * 80)
    print("Example 2: Dead Code Detection")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file with dead code
    test_file = Path("/tmp/test_dead_code.py")
    test_file.write_text("""
import os
import sys
import json  # Not used

def used_function():
    return "I am used"

def unused_function():
    return "I am never called"

def another_used_function():
    result = used_function()
    return result

UNUSED_CONSTANT = 42
USED_CONSTANT = 100

def main():
    print(USED_CONSTANT)
    another_used_function()
""")

    suggestions = engine.find_dead_code(test_file)

    print(f"\nDead code found in {test_file}:")
    for suggestion in suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  Line: {suggestion.location.start_line}")
        print(f"  Preview:\n{suggestion.diff_preview}")

    # Cleanup
    test_file.unlink()


async def example_import_optimization():
    """Example: Optimize imports."""
    print("=" * 80)
    print("Example 3: Import Optimization")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file with messy imports
    test_file = Path("/tmp/test_imports.py")
    test_file.write_text("""
import json
import os
from pathlib import Path
import sys
from datetime import datetime
import os  # Duplicate!
from typing import Any, Dict
import asyncio
from .local_module import something
import requests
import ast
""")

    suggestions = engine.optimize_imports(test_file)

    print(f"\nImport optimization suggestions for {test_file}:")
    for suggestion in suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  Reasoning: {suggestion.reasoning}")
        print(f"\n{suggestion.diff_preview}")

    # Cleanup
    test_file.unlink()


async def example_extract_method():
    """Example: Suggest extracting a complex method."""
    print("=" * 80)
    print("Example 4: Extract Method Suggestion")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file with complex function
    test_file = Path("/tmp/test_complex.py")
    test_file.write_text("""
def complex_function(data):
    # This function is too complex and should be broken down
    results = []

    # Data validation (should be extracted)
    if not data:
        raise ValueError("No data")
    if not isinstance(data, list):
        raise TypeError("Data must be list")
    if len(data) > 1000:
        raise ValueError("Too much data")

    # Data processing (should be extracted)
    for item in data:
        if item is None:
            continue
        if isinstance(item, str):
            processed = item.strip().lower()
        elif isinstance(item, int):
            processed = str(item)
        else:
            processed = repr(item)

        # Data transformation (should be extracted)
        if len(processed) > 100:
            processed = processed[:100] + "..."
        if processed.startswith("error"):
            continue

        results.append(processed)

    # Results aggregation (should be extracted)
    unique_results = list(set(results))
    sorted_results = sorted(unique_results)

    if len(sorted_results) > 50:
        return sorted_results[:50]

    return sorted_results
""")

    suggestions = engine.analyze_file(test_file)

    # Filter for extract method suggestions
    extract_suggestions = [
        s for s in suggestions if s.type == RefactoringType.EXTRACT_METHOD
    ]

    print(f"\nExtract method suggestions for {test_file}:")
    for suggestion in extract_suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  Confidence: {suggestion.confidence:.1%}")
        print(f"  Reasoning: {suggestion.reasoning}")
        print(f"\nPreview:")
        print(suggestion.diff_preview)

    # Cleanup
    test_file.unlink()


async def example_rename_symbol():
    """Example: Rename a symbol across files."""
    print("=" * 80)
    print("Example 5: Rename Symbol")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create test files
    test_file1 = Path("/tmp/test_rename1.py")
    test_file1.write_text("""
def old_function_name():
    return "Hello"

def another_function():
    result = old_function_name()
    return result
""")

    test_file2 = Path("/tmp/test_rename2.py")
    test_file2.write_text("""
from test_rename1 import old_function_name

def use_old_name():
    return old_function_name()
""")

    # Get rename suggestions
    suggestions = engine.rename_symbol(
        symbol_name="old_function_name",
        new_name="new_function_name",
        file_path=test_file1,
    )

    print("\nRename suggestions:")
    for suggestion in suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  In: {suggestion.location.file_path}")
        print(f"  Occurrences: {suggestion.metadata['occurrence_count']}")
        print(f"\nDiff preview:")
        print(suggestion.diff_preview)

    # Cleanup
    test_file1.unlink()
    test_file2.unlink()


async def example_inline_variable():
    """Example: Find variables that should be inlined."""
    print("=" * 80)
    print("Example 6: Inline Variable")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file with variables that could be inlined
    test_file = Path("/tmp/test_inline.py")
    test_file.write_text("""
def process_data(data):
    # This variable is only used once - should be inlined
    threshold = 100

    # This is used multiple times - should NOT be inlined
    max_items = 50

    results = []
    for item in data:
        if item > threshold:  # Only use of threshold
            results.append(item)

        if len(results) >= max_items:  # First use of max_items
            break

    return results[:max_items]  # Second use of max_items
""")

    suggestions = engine.analyze_file(test_file)

    # Filter for inline suggestions
    inline_suggestions = [
        s for s in suggestions if s.type == RefactoringType.INLINE_VARIABLE
    ]

    print(f"\nInline variable suggestions for {test_file}:")
    for suggestion in inline_suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  Variable: {suggestion.metadata['variable_name']}")
        print(f"  Value: {suggestion.metadata['value']}")
        print(f"  Reasoning: {suggestion.reasoning}")

    # Cleanup
    test_file.unlink()


async def example_apply_refactoring():
    """Example: Apply a refactoring (dry run)."""
    print("=" * 80)
    print("Example 7: Apply Refactoring (Dry Run)")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file
    test_file = Path("/tmp/test_apply.py")
    test_file.write_text("""
import json  # Unused
import os

def main():
    print(os.getcwd())
""")

    # Get suggestions
    suggestions = engine.find_dead_code(test_file)

    if suggestions:
        suggestion = suggestions[0]
        print(f"\nApplying refactoring (dry run):")
        print(f"Type: {suggestion.type.value}")
        print(f"Description: {suggestion.description}")

        # Apply in dry run mode
        result = engine.apply_refactoring(suggestion, dry_run=True)

        print(f"\nResult: {result['status']}")
        print(f"Changes:\n{result['diff']}")

        # For actual application, you would do:
        # result = engine.apply_refactoring(suggestion, dry_run=False)

    # Cleanup
    test_file.unlink()


async def example_extract_class():
    """Example: Suggest extracting related functions into a class."""
    print("=" * 80)
    print("Example 8: Extract Class")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Create a test file with related functions
    test_file = Path("/tmp/test_extract_class.py")
    test_file.write_text("""
# These functions are all related to user management
def user_validate_email(email):
    return "@" in email

def user_validate_password(password):
    return len(password) >= 8

def user_create(email, password):
    if not user_validate_email(email):
        raise ValueError("Invalid email")
    if not user_validate_password(password):
        raise ValueError("Invalid password")
    return {"email": email, "password": password}

def user_delete(user_id):
    # Delete user
    pass

def user_update(user_id, data):
    # Update user
    pass
""")

    suggestions = engine.analyze_file(test_file)

    # Filter for extract class suggestions
    class_suggestions = [
        s for s in suggestions if s.type == RefactoringType.EXTRACT_CLASS
    ]

    print(f"\nExtract class suggestions for {test_file}:")
    for suggestion in class_suggestions:
        print(f"\n- {suggestion.description}")
        print(f"  Functions: {', '.join(suggestion.metadata['function_names'])}")
        print(f"  Reasoning: {suggestion.reasoning}")
        print(f"\nPreview:")
        print(suggestion.diff_preview)

    # Cleanup
    test_file.unlink()


async def example_get_stats():
    """Example: Get refactoring engine statistics."""
    print("=" * 80)
    print("Example 9: Engine Statistics")
    print("=" * 80)

    engine = get_refactoring_engine()

    # Analyze a few files to populate cache
    engine.analyze_file(Path(__file__))

    stats = engine.get_stats()

    print("\nRefactoring Engine Statistics:")
    print(f"Files cached: {stats['files_cached']}")
    print(f"Workspace root: {stats['workspace_root']}")
    print(f"\nConfiguration:")
    for key, value in stats['config'].items():
        print(f"  {key}: {value}")


async def main():
    """Run all examples."""
    examples = [
        ("Analyze File", example_analyze_file),
        ("Dead Code Detection", example_dead_code_detection),
        ("Import Optimization", example_import_optimization),
        ("Extract Method", example_extract_method),
        ("Rename Symbol", example_rename_symbol),
        ("Inline Variable", example_inline_variable),
        ("Apply Refactoring", example_apply_refactoring),
        ("Extract Class", example_extract_class),
        ("Engine Statistics", example_get_stats),
    ]

    print("\n" + "=" * 80)
    print("SMART REFACTORING SYSTEM - EXAMPLES")
    print("=" * 80)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\n" + "=" * 80)

    # Run all examples
    for name, example_func in examples:
        try:
            await example_func()
            print()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 80)
    print("Examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
