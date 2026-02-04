#!/usr/bin/env python3
"""
Demonstration script for the Auto-Healing Test System.

This script shows how to use the AutoHealer to automatically detect,
analyze, and fix test failures in both Python and TypeScript tests.

Usage:
    python demo_auto_healer.py [--test-file PATH] [--batch] [--dry-run]
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.testing import (
    AutoHealer,
    HealingStrategy,
    FailureType,
    TestFramework
)


async def demo_basic_healing():
    """Demonstrate basic auto-healing functionality."""
    print("\n" + "="*70)
    print("DEMO 1: Basic Auto-Healing")
    print("="*70)

    # Create healer instance
    healer = AutoHealer(max_healing_attempts=3)

    # Example test file with failures
    test_file = Path(__file__).parent / "example_python_test.py"

    if not test_file.exists():
        print(f"Warning: Example test file not found at {test_file}")
        return

    print(f"\nHealing test file: {test_file}")

    # Heal the test failures
    result = await healer.heal_test_failure(test_file)

    # Display results
    print("\n" + "-"*70)
    print("HEALING RESULTS")
    print("-"*70)
    print(result.report)

    if result.success:
        print("\n✓ Healing completed successfully!")
        print(f"  Strategy: {result.strategy.value}")
        print(f"  Verification: {'PASSED' if result.verification_passed else 'FAILED'}")
    else:
        print("\n✗ Healing failed")
        if result.error:
            print(f"  Error: {result.error}")


async def demo_failure_analysis():
    """Demonstrate detailed failure analysis."""
    print("\n" + "="*70)
    print("DEMO 2: Detailed Failure Analysis")
    print("="*70)

    healer = AutoHealer()
    test_file = Path(__file__).parent / "example_python_test.py"

    if not test_file.exists():
        print(f"Warning: Example test file not found at {test_file}")
        return

    # Run tests to get failures
    print(f"\nRunning tests: {test_file}")
    success, output = await healer.run_tests(test_file)

    if success:
        print("All tests passed - nothing to analyze!")
        return

    # Parse failures
    failures = healer.parse_failures(output, test_file)
    print(f"\nFound {len(failures)} test failures")

    # Analyze each failure
    for i, failure in enumerate(failures, 1):
        print(f"\n{'-'*70}")
        print(f"FAILURE #{i}: {failure.test_name}")
        print(f"{'-'*70}")

        # Perform analysis
        analysis = healer.analyze_failure(failure)

        # Display analysis results
        print(f"Type:       {failure.failure_type.value}")
        print(f"Strategy:   {analysis['suggested_strategy'].value}")
        print(f"Confidence: {analysis['confidence']:.2%}")
        print(f"Reasoning:  {analysis['reasoning']}")

        if failure.expected_value and failure.actual_value:
            print(f"Expected:   {failure.expected_value}")
            print(f"Actual:     {failure.actual_value}")

        if failure.missing_import:
            print(f"Missing:    {failure.missing_import}")

        # Show suggested fix
        suggested_fix = healer.suggest_fix(analysis)
        if suggested_fix:
            print(f"Fix:        {suggested_fix}")


async def demo_batch_healing(test_directory: Path):
    """Demonstrate batch healing of multiple test files."""
    print("\n" + "="*70)
    print("DEMO 3: Batch Healing")
    print("="*70)

    healer = AutoHealer()

    # Find all test files
    test_files = list(test_directory.glob("**/test_*.py"))
    test_files.extend(test_directory.glob("**/*.test.ts"))

    print(f"\nFound {len(test_files)} test files in {test_directory}")

    if not test_files:
        print("No test files found!")
        return

    # Heal each file
    results = []
    for test_file in test_files:
        print(f"\n{'-'*70}")
        print(f"Processing: {test_file.name}")
        print(f"{'-'*70}")

        result = await healer.heal_test_failure(test_file)
        results.append((test_file, result))

        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"Status: {status}")

    # Summary report
    print("\n" + "="*70)
    print("BATCH HEALING SUMMARY")
    print("="*70)
    print(healer.get_healing_report())

    # Export results
    output_file = test_directory / "batch_healing_results.json"
    healer.export_results(output_file)
    print(f"\nResults exported to: {output_file}")


async def demo_strategy_showcase():
    """Showcase different healing strategies."""
    print("\n" + "="*70)
    print("DEMO 4: Healing Strategy Showcase")
    print("="*70)

    # Examples of different failure types and their healing strategies
    strategies_info = {
        HealingStrategy.FIX_IMPORT: {
            'description': 'Automatically adds missing import statements',
            'example': 'ImportError: No module named "datetime" → Add "from datetime import datetime"',
            'confidence': '90%',
            'auto_fix': True
        },
        HealingStrategy.UPDATE_EXPECTED: {
            'description': 'Updates expected values when code behavior changed',
            'example': 'assert result == 6  # Code now returns 7 → Update to assert result == 7',
            'confidence': '70%',
            'auto_fix': True
        },
        HealingStrategy.UPDATE_MOCK: {
            'description': 'Updates mock configurations for API changes',
            'example': 'Mock returns old structure → Update to new API structure',
            'confidence': '80%',
            'auto_fix': True
        },
        HealingStrategy.ADJUST_ASSERTION: {
            'description': 'Adjusts assertion logic for API changes',
            'example': 'Assertion checks wrong field → Update to check correct field',
            'confidence': '50%',
            'auto_fix': False
        },
        HealingStrategy.FIX_CODE: {
            'description': 'Flags implementation code issues',
            'example': 'Type error in function call → Requires code fix',
            'confidence': '60-80%',
            'auto_fix': False
        },
        HealingStrategy.MANUAL_REVIEW: {
            'description': 'Complex issues requiring human judgment',
            'example': 'Business logic error → Requires developer review',
            'confidence': '<50%',
            'auto_fix': False
        }
    }

    for strategy, info in strategies_info.items():
        print(f"\n{strategy.value.upper().replace('_', ' ')}")
        print(f"{'-'*70}")
        print(f"Description: {info['description']}")
        print(f"Example:     {info['example']}")
        print(f"Confidence:  {info['confidence']}")
        print(f"Auto-Fix:    {'Yes' if info['auto_fix'] else 'No'}")


async def demo_dry_run(test_file: Path):
    """Demonstrate dry-run mode (analysis only, no fixes applied)."""
    print("\n" + "="*70)
    print("DEMO 5: Dry Run (Analysis Only)")
    print("="*70)

    healer = AutoHealer()

    print(f"\nAnalyzing: {test_file}")
    print("(No fixes will be applied)")

    # Run tests
    success, output = await healer.run_tests(test_file)

    if success:
        print("\nAll tests passed - nothing to analyze!")
        return

    # Parse and analyze failures
    failures = healer.parse_failures(output, test_file)

    print(f"\nFound {len(failures)} failures\n")

    # Create dry-run report
    for failure in failures:
        analysis = healer.analyze_failure(failure)
        suggested_fix = healer.suggest_fix(analysis)

        print(f"Test: {failure.test_name}")
        print(f"  Type: {failure.failure_type.value}")
        print(f"  Strategy: {analysis['suggested_strategy'].value}")
        print(f"  Confidence: {analysis['confidence']:.2%}")

        if suggested_fix:
            print(f"  Would apply: {suggested_fix}")
        else:
            print(f"  Action: Manual review required")

        print()


async def demo_confidence_filtering():
    """Demonstrate healing with different confidence thresholds."""
    print("\n" + "="*70)
    print("DEMO 6: Confidence-Based Healing")
    print("="*70)

    test_file = Path(__file__).parent / "example_python_test.py"

    if not test_file.exists():
        print(f"Warning: Example test file not found at {test_file}")
        return

    # Test with different confidence thresholds
    thresholds = [0.5, 0.7, 0.9]

    for threshold in thresholds:
        print(f"\n{'-'*70}")
        print(f"THRESHOLD: {threshold:.0%}")
        print(f"{'-'*70}")

        healer = AutoHealer()

        # Run tests
        success, output = await healer.run_tests(test_file)
        if success:
            print("All tests passed!")
            continue

        # Analyze failures
        failures = healer.parse_failures(output, test_file)

        # Count how many would be auto-fixed at this threshold
        auto_fix_count = 0
        manual_review_count = 0

        for failure in failures:
            analysis = healer.analyze_failure(failure)
            if analysis['confidence'] >= threshold:
                auto_fix_count += 1
            else:
                manual_review_count += 1

        print(f"Total failures:     {len(failures)}")
        print(f"Would auto-fix:     {auto_fix_count}")
        print(f"Manual review:      {manual_review_count}")
        print(f"Auto-fix rate:      {auto_fix_count/len(failures):.1%}")


async def demo_progressive_healing():
    """Demonstrate progressive healing with multiple attempts."""
    print("\n" + "="*70)
    print("DEMO 7: Progressive Healing")
    print("="*70)

    test_file = Path(__file__).parent / "example_python_test.py"

    if not test_file.exists():
        print(f"Warning: Example test file not found at {test_file}")
        return

    print(f"\nHealing: {test_file}")
    print("Max attempts: 3\n")

    healer = AutoHealer(max_healing_attempts=3)

    # This will attempt healing up to 3 times
    result = await healer.heal_test_failure(test_file)

    # Show attempt history from report
    print(result.report)


async def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(
        description='Auto-Healing Test System Demonstration'
    )
    parser.add_argument(
        '--test-file',
        type=Path,
        help='Specific test file to heal'
    )
    parser.add_argument(
        '--batch',
        type=Path,
        help='Directory containing tests for batch healing'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze only, do not apply fixes'
    )
    parser.add_argument(
        '--demo',
        choices=['all', 'basic', 'analysis', 'batch', 'strategies', 'confidence', 'progressive'],
        default='all',
        help='Which demo to run'
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("AUTO-HEALING TEST SYSTEM DEMONSTRATION")
    print("="*70)

    try:
        if args.test_file:
            if args.dry_run:
                await demo_dry_run(args.test_file)
            else:
                healer = AutoHealer()
                result = await healer.heal_test_failure(args.test_file)
                print(result.report)

        elif args.batch:
            await demo_batch_healing(args.batch)

        else:
            # Run selected demo(s)
            if args.demo in ['all', 'basic']:
                await demo_basic_healing()

            if args.demo in ['all', 'analysis']:
                await demo_failure_analysis()

            if args.demo in ['all', 'strategies']:
                await demo_strategy_showcase()

            if args.demo in ['all', 'confidence']:
                await demo_confidence_filtering()

            if args.demo in ['all', 'progressive']:
                await demo_progressive_healing()

            # Note: batch demo requires a directory argument
            if args.demo == 'batch':
                print("\nNote: Batch demo requires --batch argument with directory path")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
