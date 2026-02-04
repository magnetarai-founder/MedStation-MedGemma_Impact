#!/usr/bin/env python3
"""
Test Generator Usage Examples

Demonstrates various ways to use the test generation system.
"""

import asyncio
from pathlib import Path

from api.services.testing import (
    CoverageGap,
    TestGenerator,
    TestType,
    find_untested_code,
    generate_tests_for_file,
)


async def example_1_generate_unit_test():
    """Example 1: Generate unit test for a specific function."""
    print("=" * 60)
    print("Example 1: Generate Unit Test for Specific Function")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Analyze a function
    analysis = await generator.analyze_function(
        file_path="api/services/cache_service.py",
        function_name="get_cached_value",
    )

    if analysis:
        print(f"\nAnalyzed function: {analysis.signature}")
        print(f"Complexity: {analysis.cyclomatic_complexity}")
        print(f"Is async: {analysis.is_async}")
        print(f"Parameters: {len(analysis.parameters)}")

        # Generate unit test
        test = await generator.generate_unit_test(analysis, include_edge_cases=True)

        print(f"\nGenerated test: {test.name}")
        print(f"Test type: {test.test_type.value}")
        print(f"Assertions: {len(test.assertions)}")
        print(f"\nTest code preview:")
        print("-" * 60)
        print(test.code[:500] + "..." if len(test.code) > 500 else test.code)
        print("-" * 60)


async def example_2_generate_edge_cases():
    """Example 2: Generate edge case tests."""
    print("\n" + "=" * 60)
    print("Example 2: Generate Edge Case Tests")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Analyze a function
    analysis = await generator.analyze_function(
        file_path="api/services/file_operations.py",
        function_name="read_file_safely",
    )

    if analysis:
        print(f"\nAnalyzing: {analysis.name}")

        # Generate edge case tests
        edge_tests = await generator.generate_edge_cases(analysis)

        print(f"\nGenerated {len(edge_tests)} edge case tests:")
        for test in edge_tests:
            print(f"  - {test.name}: {test.description}")


async def example_3_property_based_test():
    """Example 3: Generate property-based test."""
    print("\n" + "=" * 60)
    print("Example 3: Generate Property-Based Test")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Analyze a pure function
    analysis = await generator.analyze_function(
        file_path="api/utils/path_security.py",
        function_name="is_safe_path",
    )

    if analysis:
        print(f"\nAnalyzing: {analysis.name}")
        print(f"Is pure function: {analysis.is_pure}")

        # Generate property-based test
        prop_test = await generator.generate_property_test(analysis)

        if prop_test:
            print(f"\nGenerated property test: {prop_test.name}")
            print(f"\nTest code:")
            print("-" * 60)
            print(prop_test.code)
            print("-" * 60)
        else:
            print("\nProperty-based test not applicable for this function")


async def example_4_api_test():
    """Example 4: Generate API integration test."""
    print("\n" + "=" * 60)
    print("Example 4: Generate API Integration Test")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Analyze an API endpoint handler
    analysis = await generator.analyze_function(
        file_path="api/routes/health.py",
        function_name="health_check",
    )

    if analysis:
        print(f"\nAnalyzing API endpoint: {analysis.name}")
        print(f"Is API endpoint: {analysis.is_api_endpoint}")

        # Generate API test
        api_test = await generator.generate_api_test(
            endpoint_path="/health",
            http_method="GET",
            analysis=analysis,
        )

        print(f"\nGenerated API test: {api_test.name}")
        print(f"\nTest code:")
        print("-" * 60)
        print(api_test.code)
        print("-" * 60)


async def example_5_suggest_mocks():
    """Example 5: Suggest mocks and fixtures."""
    print("\n" + "=" * 60)
    print("Example 5: Suggest Mocks and Fixtures")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Analyze a function with dependencies
    analysis = await generator.analyze_function(
        file_path="api/services/github_client.py",
        function_name="get_repository",
    )

    if analysis:
        print(f"\nAnalyzing: {analysis.name}")
        print(f"Calls functions: {analysis.calls_functions[:5]}")

        # Get mock suggestions
        suggestions = await generator.suggest_mocks(analysis)

        print(f"\nMock/Fixture suggestions ({len(suggestions)}):")
        for suggestion in suggestions:
            print(f"\n  Type: {suggestion['type']}")
            print(f"  Target: {suggestion['target']}")
            print(f"  Description: {suggestion['description']}")
            print(f"  Code snippet:")
            print("  " + "\n  ".join(suggestion['code'].split("\n")[:5]))


async def example_6_find_coverage_gaps():
    """Example 6: Find coverage gaps."""
    print("\n" + "=" * 60)
    print("Example 6: Find Coverage Gaps")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # Find coverage gaps
    print("\nAnalyzing coverage data...")
    gaps = await generator.find_coverage_gaps()

    if gaps:
        print(f"\nFound {len(gaps)} coverage gaps:")
        for gap in gaps[:5]:  # Show top 5
            print(f"\n  File: {gap.file}")
            print(f"  Coverage: {gap.coverage_percent:.1f}%")
            print(f"  Risk level: {gap.risk_level}")
            print(f"  Uncovered lines: {len(gap.uncovered_lines)}")
            if gap.suggested_tests:
                print(f"  Suggestions:")
                for suggestion in gap.suggested_tests[:2]:
                    print(f"    - {suggestion}")
    else:
        print("\nNo coverage data available or all files have good coverage!")


async def example_7_generate_complete_test_file():
    """Example 7: Generate complete test file for a module."""
    print("\n" + "=" * 60)
    print("Example 7: Generate Complete Test File")
    print("=" * 60)

    # Use convenience function
    print("\nGenerating tests for cache_service.py...")
    try:
        test_file = await generate_tests_for_file(
            file_path="api/services/cache_service.py",
            workspace_root=".",
        )
        print(f"\nGenerated test file: {test_file}")
        print("Check the file to see all generated tests!")
    except Exception as e:
        print(f"\nError: {e}")
        print("This is normal if the file doesn't exist in the current directory")


async def example_8_batch_processing():
    """Example 8: Batch process multiple files."""
    print("\n" + "=" * 60)
    print("Example 8: Batch Process Multiple Files")
    print("=" * 60)

    generator = TestGenerator(workspace_root=".")

    # List of files to generate tests for
    files_to_test = [
        "api/utils/cache.py",
        "api/utils/retry.py",
        "api/utils/decorators.py",
    ]

    print(f"\nProcessing {len(files_to_test)} files...")

    results = []
    for file_path in files_to_test:
        try:
            test_file = await generator.generate_test_file(file_path)
            results.append((file_path, test_file, "success"))
            print(f"  ✓ {file_path}")
        except Exception as e:
            results.append((file_path, None, str(e)))
            print(f"  ✗ {file_path}: {e}")

    print(f"\nResults: {sum(1 for _, _, status in results if status == 'success')}/{len(results)} succeeded")


async def example_9_analyze_test_coverage():
    """Example 9: Comprehensive coverage analysis."""
    print("\n" + "=" * 60)
    print("Example 9: Comprehensive Coverage Analysis")
    print("=" * 60)

    # Find untested code
    print("\nFinding untested code across workspace...")
    gaps = await find_untested_code(workspace_root=".")

    if gaps:
        # Group by risk level
        by_risk = {}
        for gap in gaps:
            risk = gap.risk_level
            if risk not in by_risk:
                by_risk[risk] = []
            by_risk[risk].append(gap)

        print(f"\nCoverage gaps by risk level:")
        for risk in ["critical", "high", "medium", "low"]:
            if risk in by_risk:
                print(f"\n  {risk.upper()}: {len(by_risk[risk])} files")
                for gap in by_risk[risk][:3]:  # Show top 3
                    print(f"    - {gap.file}: {gap.coverage_percent:.1f}% coverage")
    else:
        print("\nExcellent! No significant coverage gaps found.")


async def main():
    """Run all examples."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         Test Generator - Usage Examples                   ║")
    print("╔════════════════════════════════════════════════════════════╗")
    print("\n")

    examples = [
        example_1_generate_unit_test,
        example_2_generate_edge_cases,
        example_3_property_based_test,
        example_4_api_test,
        example_5_suggest_mocks,
        example_6_find_coverage_gaps,
        example_7_generate_complete_test_file,
        example_8_batch_processing,
        example_9_analyze_test_coverage,
    ]

    for i, example in enumerate(examples, 1):
        try:
            await example()
        except Exception as e:
            print(f"\nExample {i} error: {e}")
            print("(This is expected if running outside the actual project)")

        if i < len(examples):
            print("\n")
            input("Press Enter to continue to next example...")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
