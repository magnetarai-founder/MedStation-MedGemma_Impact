"""
Testing Services for MagnetarCode

Provides automated test healing, generation, analysis, and maintenance capabilities.

Features:
- Auto-healing test system that detects and fixes test failures
- Intelligent test generation from code analysis
- Coverage gap detection and analysis
- Edge case and property-based test generation
- API integration test generation
- Support for pytest (Python) and jest (TypeScript) frameworks
- Intelligent failure analysis and root cause detection
- Automatic fixes for common issues (imports, assertions, mocks)
- Mock/fixture suggestions

Components:
Auto-Healing:
- AutoHealer: Main auto-healing orchestrator
- TestOutputParser: Parse pytest/jest output for failures
- CodeAnalyzer: Analyze test code to understand failures
- TestFixer: Apply fixes to test files
- TestRunner: Execute tests and capture output

Test Generation:
- TestGenerator: Intelligent test suite generator
- TestCase: Generated test case representation
- CoverageGap: Coverage gap analysis
- FunctionAnalysis: Function metadata for test generation

Usage:
    # Auto-healing
    from services.testing import AutoHealer, HealingStrategy

    healer = AutoHealer()
    result = await healer.heal_test_failure(test_file_path)
    print(result.report)

    # Test generation
    from services.testing import TestGenerator, generate_tests_for_file

    # Generate tests for a file
    test_file = await generate_tests_for_file("my_module.py")

    # Or use the generator directly
    generator = TestGenerator(workspace_root=".")
    analysis = await generator.analyze_function("my_module.py", "my_function")
    test = await generator.generate_unit_test(analysis)
"""

# Import test generation (always available)
from .generator import (
    CoverageGap,
    FunctionAnalysis,
    TestCase,
    TestFramework,
    TestGenerator,
    TestType,
    find_untested_code,
    generate_tests_for_file,
)

# Try to import auto-healer (may not be available yet)
try:
    from .auto_healer import (
        AutoHealer,
        CodeAnalyzer,
        FailureType,
        HealingResult,
        HealingStrategy,
        TestFailure,
        TestFixer,
        TestOutputParser,
        TestRunner,
    )

    __all__ = [
        # Auto-Healing (if available)
        "AutoHealer",
        "TestOutputParser",
        "CodeAnalyzer",
        "TestFixer",
        "TestRunner",
        "TestFailure",
        "HealingResult",
        "FailureType",
        "HealingStrategy",
        # Test Generation
        "TestGenerator",
        "TestCase",
        "CoverageGap",
        "FunctionAnalysis",
        "TestType",
        "generate_tests_for_file",
        "find_untested_code",
        # Shared
        "TestFramework",
    ]
except ImportError:
    # Auto-healer not available, only export test generation
    __all__ = [
        # Test Generation
        "TestGenerator",
        "TestCase",
        "CoverageGap",
        "FunctionAnalysis",
        "TestType",
        "generate_tests_for_file",
        "find_untested_code",
        "TestFramework",
    ]
