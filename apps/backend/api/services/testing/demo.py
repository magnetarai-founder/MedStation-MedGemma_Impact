#!/usr/bin/env python3
"""
Test Generator Demo

Quick demonstration of the test generation capabilities.
Run this to see the generator in action.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.services.testing import (
    TestGenerator,
    TestFramework,
    TestType,
)


async def demo_analyze_function():
    """Demo: Analyze a function and show its properties."""
    print("\n" + "=" * 70)
    print("DEMO 1: Function Analysis")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create a sample function to analyze
    sample_code = '''
def calculate_discount(price: float, discount_percent: int) -> float:
    """
    Calculate discounted price.

    Args:
        price: Original price
        discount_percent: Discount percentage (0-100)

    Returns:
        Discounted price

    Raises:
        ValueError: If discount_percent is invalid
    """
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")

    discount_amount = price * (discount_percent / 100)
    return price - discount_amount
'''

    # Write sample file
    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        # Analyze the function
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="calculate_discount",
        )

        if analysis:
            print(f"\n📝 Function: {analysis.name}")
            print(f"📍 Location: Line {analysis.line_number}")
            print(f"✍️  Signature: {analysis.signature}")
            print(f"\n📊 Analysis Results:")
            print(f"  • Parameters: {len(analysis.parameters)}")
            for param_name, param_type in analysis.parameters:
                print(f"    - {param_name}: {param_type or 'Any'}")
            print(f"  • Return type: {analysis.return_type}")
            print(f"  • Is async: {analysis.is_async}")
            print(f"  • Cyclomatic complexity: {analysis.cyclomatic_complexity}")
            print(f"  • Is pure function: {analysis.is_pure}")
            print(f"  • Has conditionals: {analysis.has_conditionals}")
            print(f"  • Has loops: {analysis.has_loops}")
            print(f"  • Raises exceptions: {analysis.raises_exceptions}")
            print(f"  • Calls functions: {analysis.calls_functions[:3]}")
    finally:
        # Cleanup
        if sample_file.exists():
            sample_file.unlink()


async def demo_generate_unit_test():
    """Demo: Generate a unit test."""
    print("\n" + "=" * 70)
    print("DEMO 2: Unit Test Generation")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create sample function
    sample_code = '''
def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or "@" not in email:
        return False
    return True
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        # Analyze
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="validate_email",
        )

        if analysis:
            # Generate unit test
            test = await generator.generate_unit_test(analysis, include_edge_cases=True)

            print(f"\n✅ Generated Test: {test.name}")
            print(f"📌 Test Type: {test.test_type.value}")
            print(f"🎯 Priority: {test.priority}")
            print(f"📈 Estimated Coverage Gain: {test.estimated_coverage_gain:.1f}%")
            print(f"\n📋 Test Code:")
            print("-" * 70)
            print(test.code)
            print("-" * 70)

            print(f"\n📦 Required Imports:")
            for imp in test.imports:
                print(f"  • {imp}")

            print(f"\n✓ Assertions ({len(test.assertions)}):")
            for assertion in test.assertions[:5]:
                print(f"  • {assertion}")
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def demo_edge_cases():
    """Demo: Generate edge case tests."""
    print("\n" + "=" * 70)
    print("DEMO 3: Edge Case Test Generation")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create sample function with various parameter types
    sample_code = '''
def process_data(
    text: str,
    numbers: list[int],
    config: dict[str, any]
) -> dict[str, any]:
    """Process data with various inputs."""
    return {
        "text_length": len(text),
        "sum": sum(numbers),
        "config_keys": len(config)
    }
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="process_data",
        )

        if analysis:
            # Generate edge case tests
            edge_tests = await generator.generate_edge_cases(analysis)

            print(f"\n🎯 Generated {len(edge_tests)} Edge Case Tests:")
            for i, test in enumerate(edge_tests, 1):
                print(f"\n{i}. {test.name}")
                print(f"   Description: {test.description}")
                print(f"   Test Type: {test.test_type.value}")
                print(f"   Code Preview:")
                preview = test.code.split('\n')[:5]
                for line in preview:
                    print(f"   {line}")
                if len(test.code.split('\n')) > 5:
                    print("   ...")
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def demo_property_test():
    """Demo: Generate property-based test."""
    print("\n" + "=" * 70)
    print("DEMO 4: Property-Based Test Generation")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create a pure function
    sample_code = '''
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="add_numbers",
        )

        if analysis:
            print(f"\n📊 Function Analysis:")
            print(f"  • Is pure: {analysis.is_pure}")
            print(f"  • Has side effects: {not analysis.is_pure}")

            # Generate property test
            prop_test = await generator.generate_property_test(analysis)

            if prop_test:
                print(f"\n✅ Generated Property Test: {prop_test.name}")
                print(f"📌 Test Type: {prop_test.test_type.value}")
                print(f"\n📋 Test Code:")
                print("-" * 70)
                print(prop_test.code)
                print("-" * 70)

                print(f"\n📦 Required Imports:")
                for imp in prop_test.imports:
                    print(f"  • {imp}")
            else:
                print("\n⚠️  Property-based test not applicable for this function")
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def demo_api_test():
    """Demo: Generate API integration test."""
    print("\n" + "=" * 70)
    print("DEMO 5: API Integration Test Generation")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create sample API endpoint
    sample_code = '''
from fastapi import APIRouter

router = APIRouter()

@router.post("/users")
async def create_user(name: str, email: str) -> dict:
    """Create a new user."""
    return {"id": 1, "name": name, "email": email}
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="create_user",
        )

        if analysis:
            print(f"\n📊 Endpoint Analysis:")
            print(f"  • Is API endpoint: {analysis.is_api_endpoint}")
            print(f"  • Decorators: {analysis.decorators}")

            # Generate API test
            api_test = await generator.generate_api_test(
                endpoint_path="/users",
                http_method="POST",
                analysis=analysis,
            )

            print(f"\n✅ Generated API Test: {api_test.name}")
            print(f"📌 Test Type: {api_test.test_type.value}")
            print(f"🎯 Priority: {api_test.priority}")
            print(f"\n📋 Test Code:")
            print("-" * 70)
            print(api_test.code)
            print("-" * 70)

            print(f"\n🔧 Required Fixtures:")
            for fixture in api_test.fixtures:
                print(f"  • {fixture}")

            print(f"\n✓ Assertions:")
            for assertion in api_test.assertions:
                print(f"  • {assertion}")
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def demo_mock_suggestions():
    """Demo: Generate mock suggestions."""
    print("\n" + "=" * 70)
    print("DEMO 6: Mock and Fixture Suggestions")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create function with dependencies
    sample_code = '''
import requests
from database import Database

def fetch_user_data(user_id: int, db: Database) -> dict:
    """Fetch user data from API and database."""
    # Call external API
    response = requests.get(f"https://api.example.com/users/{user_id}")
    api_data = response.json()

    # Query database
    db_data = db.query("SELECT * FROM users WHERE id = ?", user_id)

    return {**api_data, **db_data}
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_sample.py"
    sample_file.write_text(sample_code)

    try:
        analysis = await generator.analyze_function(
            file_path=sample_file,
            function_name="fetch_user_data",
        )

        if analysis:
            print(f"\n📊 Function Dependencies:")
            print(f"  • Calls functions: {analysis.calls_functions[:5]}")

            # Get mock suggestions
            suggestions = await generator.suggest_mocks(analysis)

            print(f"\n💡 Generated {len(suggestions)} Mock/Fixture Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n{i}. Type: {suggestion['type'].upper()}")
                print(f"   Target: {suggestion['target']}")
                print(f"   Description: {suggestion['description']}")
                print(f"   Code Example:")
                code_lines = suggestion['code'].split('\n')[:4]
                for line in code_lines:
                    print(f"   {line}")
                if len(suggestion['code'].split('\n')) > 4:
                    print("   ...")
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def demo_complete_workflow():
    """Demo: Complete test generation workflow."""
    print("\n" + "=" * 70)
    print("DEMO 7: Complete Test Generation Workflow")
    print("=" * 70)

    generator = TestGenerator(workspace_root=project_root)

    # Create a complete module
    sample_code = '''
"""Sample user management module."""

class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

def validate_user(user: User) -> bool:
    """Validate user data."""
    if not user.name or len(user.name) < 2:
        return False
    if not user.email or "@" not in user.email:
        return False
    return True

def create_user(name: str, email: str) -> User:
    """Create a new user."""
    user = User(name, email)
    if not validate_user(user):
        raise ValueError("Invalid user data")
    return user

def format_user_display(user: User) -> str:
    """Format user for display."""
    return f"{user.name} <{user.email}>"
'''

    sample_file = project_root / "apps/backend/api/services/testing/_demo_user_module.py"
    sample_file.write_text(sample_code)

    try:
        print("\n📝 Generating comprehensive test suite...")
        print(f"   Source: {sample_file.name}")

        # Generate complete test file
        test_file = await generator.generate_test_file(
            source_file=sample_file,
            output_file=project_root
            / "apps/backend/api/services/testing/_demo_test_user_module.py",
        )

        print(f"\n✅ Generated test file: {Path(test_file).name}")

        # Read and show preview
        test_content = Path(test_file).read_text()
        lines = test_content.split('\n')

        print(f"\n📋 Test File Preview (first 30 lines):")
        print("-" * 70)
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3d} | {line}")
        print("-" * 70)
        print(f"Total lines: {len(lines)}")

        # Cleanup
        Path(test_file).unlink()
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def main():
    """Run all demos."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║         Test Generator - Interactive Demonstration                  ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    demos = [
        ("Function Analysis", demo_analyze_function),
        ("Unit Test Generation", demo_generate_unit_test),
        ("Edge Case Tests", demo_edge_cases),
        ("Property-Based Tests", demo_property_test),
        ("API Integration Tests", demo_api_test),
        ("Mock Suggestions", demo_mock_suggestions),
        ("Complete Workflow", demo_complete_workflow),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n\n[Demo {i}/{len(demos)}] {name}")
        try:
            await demo_func()
        except Exception as e:
            print(f"\n❌ Error in demo: {e}")
            import traceback

            traceback.print_exc()

        if i < len(demos):
            print("\n" + "-" * 70)
            try:
                input("Press Enter to continue to next demo (Ctrl+C to exit)...")
            except KeyboardInterrupt:
                print("\n\nDemo interrupted by user.")
                break

    print("\n\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)
    print("\nTo use the test generator in your own code:")
    print("  from api.services.testing import TestGenerator")
    print("  generator = TestGenerator(workspace_root='.')")
    print("\nSee TEST_GENERATION.md for full documentation.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
