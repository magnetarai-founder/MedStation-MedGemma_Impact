#!/usr/bin/env python3
"""
Quick demonstration of the Smart Refactoring System

Run this file to see the refactoring engine in action.
"""

from pathlib import Path
from api.services.refactoring import get_refactoring_engine


def run_demo():
    """Run a quick demonstration."""
    # Create a test file with various issues
    test_file = Path("/tmp/test_refactor_demo.py")
    test_file.write_text("""
import os
import sys
import json  # This import is unused

def unused_function():
    # This function is never called
    return "I am dead code"

def complex_function(data):
    # This function is too complex with deep nesting
    if data:
        if isinstance(data, list):
            if len(data) > 0:
                if data[0] is not None:
                    if data[0] > 10:
                        if data[0] < 100:
                            return data[0] * 2
    return None

def used_function():
    return os.getcwd()

# Single-use variable (should be inlined)
temp = 42

def main():
    result = used_function()
    print(result)
    print(temp)
""")

    # Initialize engine and analyze
    engine = get_refactoring_engine()
    suggestions = engine.analyze_file(test_file)

    print("=" * 80)
    print("SMART REFACTORING SYSTEM - DEMONSTRATION")
    print("=" * 80)
    print(f"\nAnalyzed: {test_file}")
    print(f"Found {len(suggestions)} refactoring suggestions\n")

    # Show all suggestions
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion.type.value.upper()}")
        print(f"   Location: Line {suggestion.location.start_line}-{suggestion.location.end_line}")
        print(f"   Description: {suggestion.description}")
        print(f"   Confidence: {suggestion.confidence:.0%}")
        print(
            f"   Impact: {suggestion.impact_score:.0%} | "
            f"Effort: {suggestion.effort_score:.0%} | "
            f"Safety: {suggestion.safety_score:.0%}"
        )
        print(f"   Reasoning: {suggestion.reasoning}")
        print()

    # Show dead code in detail
    dead_code = [s for s in suggestions if s.type.value == "dead_code"]
    if dead_code:
        print("=" * 80)
        print("DEAD CODE DETECTED:")
        print("=" * 80)
        for suggestion in dead_code:
            print(f"\n{suggestion.description}")
            print(f"Preview:\n{suggestion.diff_preview}")
            print()

    # Show import optimization
    import_opts = [s for s in suggestions if s.type.value == "optimize_imports"]
    if import_opts:
        print("=" * 80)
        print("IMPORT OPTIMIZATION:")
        print("=" * 80)
        for suggestion in import_opts:
            print(f"\n{suggestion.description}")
            print(f"\n{suggestion.diff_preview}")
            print()

    # Show extract method suggestions
    extract_methods = [s for s in suggestions if s.type.value == "extract_method"]
    if extract_methods:
        print("=" * 80)
        print("EXTRACT METHOD SUGGESTIONS:")
        print("=" * 80)
        for suggestion in extract_methods:
            print(f"\n{suggestion.description}")
            print(f"Metrics: {suggestion.metadata.get('metrics', {})}")
            print()

    # Cleanup
    test_file.unlink()

    print("=" * 80)
    print("✓ Demonstration completed successfully!")
    print("=" * 80)
    print("\nThe Smart Refactoring System can:")
    print("  - Detect dead code (unused functions, variables, imports)")
    print("  - Suggest extracting complex methods")
    print("  - Optimize import statements")
    print("  - Find duplicate code")
    print("  - Suggest extracting classes from related functions")
    print("  - Inline variables used only once")
    print("  - Safely rename symbols across files")
    print("\nAll with preview-before-apply safety!")


if __name__ == "__main__":
    run_demo()
