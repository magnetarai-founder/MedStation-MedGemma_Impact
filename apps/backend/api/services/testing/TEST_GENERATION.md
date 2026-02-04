# Test Generation System

Intelligent test generation system for MagnetarCode that automatically creates comprehensive test suites from code analysis.

## Features

### Core Capabilities

- **Unit Test Generation**: Analyze functions/classes and generate comprehensive unit tests
- **Edge Case Detection**: Automatically identify and test edge cases (null inputs, boundary values, empty collections)
- **Property-Based Testing**: Generate hypothesis-style property tests for pure functions
- **Integration Tests**: Create API endpoint integration tests
- **Coverage Analysis**: Identify untested code paths and coverage gaps
- **Mock/Fixture Suggestions**: Intelligent suggestions for mocks and test fixtures
- **Multi-Framework Support**: pytest (Python), jest (TypeScript)

### Intelligence Features

- AST-based code analysis
- Cyclomatic complexity calculation
- Function purity detection
- API endpoint identification
- Exception flow analysis
- Dependency graph extraction

## Installation

The test generator is part of the MagnetarCode testing services package:

```python
from api.services.testing import (
    TestGenerator,
    TestCase,
    CoverageGap,
    generate_tests_for_file,
    find_untested_code,
)
```

### Dependencies

Required Python packages:
- `ast` (built-in)
- `pytest` - For running generated tests
- `pytest-cov` - For coverage analysis
- `hypothesis` - For property-based tests (optional)
- `pytest-asyncio` - For async test support

## Quick Start

### 1. Generate Tests for a File

```python
import asyncio
from api.services.testing import generate_tests_for_file

async def main():
    # Generate complete test file
    test_file = await generate_tests_for_file(
        file_path="api/services/my_module.py",
        workspace_root="."
    )
    print(f"Tests generated: {test_file}")

asyncio.run(main())
```

### 2. Generate Unit Test for Specific Function

```python
from api.services.testing import TestGenerator

generator = TestGenerator(workspace_root=".")

# Analyze function
analysis = await generator.analyze_function(
    file_path="api/services/cache_service.py",
    function_name="get_cached_value"
)

# Generate unit test
test = await generator.generate_unit_test(
    analysis,
    include_edge_cases=True
)

print(test.code)
```

### 3. Find Coverage Gaps

```python
from api.services.testing import find_untested_code

# Find all coverage gaps
gaps = await find_untested_code(workspace_root=".")

for gap in gaps:
    print(f"{gap.file}: {gap.coverage_percent:.1f}% coverage")
    print(f"Risk: {gap.risk_level}")
    print(f"Suggested tests: {gap.suggested_tests}")
```

## API Reference

### TestGenerator

Main class for test generation.

```python
generator = TestGenerator(
    workspace_root: str | Path,
    framework: TestFramework = TestFramework.PYTEST
)
```

#### Methods

##### analyze_function()

Analyze a function to extract metadata for test generation.

```python
analysis = await generator.analyze_function(
    file_path: str | Path,
    function_name: str
) -> FunctionAnalysis | None
```

Returns `FunctionAnalysis` with:
- `signature`: Function signature
- `parameters`: List of (name, type_hint) tuples
- `return_type`: Return type annotation
- `is_async`: Whether function is async
- `cyclomatic_complexity`: Complexity score
- `is_pure`: Whether function has side effects
- `is_api_endpoint`: Whether function is API endpoint
- `raises_exceptions`: List of exceptions raised
- `calls_functions`: List of functions called

##### generate_unit_test()

Generate comprehensive unit test with multiple scenarios.

```python
test = await generator.generate_unit_test(
    analysis: FunctionAnalysis,
    include_edge_cases: bool = True
) -> TestCase
```

Returns `TestCase` with:
- `name`: Test function name
- `code`: Complete test code
- `assertions`: List of assertions
- `imports`: Required imports
- `mocks`: Required mocks
- `fixtures`: Required fixtures

##### generate_edge_cases()

Generate edge case tests (null inputs, boundaries, empty collections).

```python
edge_tests = await generator.generate_edge_cases(
    analysis: FunctionAnalysis
) -> list[TestCase]
```

##### generate_property_test()

Generate property-based test using hypothesis-style testing.

```python
prop_test = await generator.generate_property_test(
    analysis: FunctionAnalysis
) -> TestCase | None
```

Returns `None` if function is not suitable for property-based testing.

##### generate_api_test()

Generate integration test for API endpoint.

```python
api_test = await generator.generate_api_test(
    endpoint_path: str,
    http_method: str,
    analysis: FunctionAnalysis
) -> TestCase
```

Example:
```python
api_test = await generator.generate_api_test(
    endpoint_path="/api/users",
    http_method="POST",
    analysis=analysis
)
```

##### find_coverage_gaps()

Find untested code using coverage.py data.

```python
gaps = await generator.find_coverage_gaps(
    coverage_file: str | Path | None = None
) -> list[CoverageGap]
```

Returns list of `CoverageGap` with:
- `file`: File path
- `uncovered_lines`: List of line numbers
- `coverage_percent`: Coverage percentage
- `risk_level`: "critical", "high", "medium", "low"
- `suggested_tests`: List of test suggestions

##### suggest_mocks()

Suggest mocks and fixtures for testing a function.

```python
suggestions = await generator.suggest_mocks(
    analysis: FunctionAnalysis
) -> list[dict[str, Any]]
```

Returns list of suggestions with:
- `type`: "mock" or "fixture"
- `target`: What to mock/fixture
- `code`: Example implementation
- `description`: Explanation

##### generate_test_file()

Generate complete test file for a source file.

```python
test_file_path = await generator.generate_test_file(
    source_file: str | Path,
    output_file: str | Path | None = None
) -> str
```

### Data Classes

#### TestCase

Represents a generated test case.

```python
@dataclass
class TestCase:
    name: str                    # Test function name
    description: str             # Human-readable description
    code: str                    # Complete test code
    test_type: TestType         # UNIT, INTEGRATION, EDGE_CASE, etc.
    framework: TestFramework    # PYTEST, JEST, etc.
    assertions: list[str]       # List of assertions
    fixtures: list[str]         # Required fixtures
    mocks: list[str]            # Required mocks
    imports: list[str]          # Required imports
    setup_code: str | None      # Setup code
    teardown_code: str | None   # Teardown code
    tags: list[str]             # Test tags
    priority: int               # 1=high, 2=medium, 3=low
    estimated_coverage_gain: float
```

#### CoverageGap

Represents a gap in test coverage.

```python
@dataclass
class CoverageGap:
    file: str                   # File path
    function: str | None        # Function name
    class_name: str | None      # Class name
    uncovered_lines: list[int]  # Line numbers
    total_lines: int            # Total lines
    coverage_percent: float     # Coverage %
    complexity: int             # Cyclomatic complexity
    risk_level: str            # "critical", "high", "medium", "low"
    suggested_tests: list[str]  # Test suggestions
```

#### FunctionAnalysis

Analysis result for a function.

```python
@dataclass
class FunctionAnalysis:
    name: str
    file_path: str
    line_number: int
    signature: str
    docstring: str | None
    parameters: list[tuple[str, str | None]]
    return_type: str | None
    is_async: bool
    decorators: list[str]
    raises_exceptions: list[str]
    calls_functions: list[str]
    has_conditionals: bool
    has_loops: bool
    cyclomatic_complexity: int
    is_pure: bool
    is_api_endpoint: bool
```

### Enums

#### TestType

```python
class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"
    PROPERTY = "property"
    API = "api"
    E2E = "e2e"
```

#### TestFramework

```python
class TestFramework(Enum):
    PYTEST = "pytest"
    JEST = "jest"
    UNITTEST = "unittest"
    MOCHA = "mocha"
```

## Advanced Usage

### Custom Test Templates

The generator uses intelligent template-based generation. You can customize by extending the `TestGenerator` class:

```python
class CustomTestGenerator(TestGenerator):
    def _generate_happy_path_scenario(self, analysis):
        # Custom scenario generation
        return {
            "description": "Custom test scenario",
            "args": ["custom_arg"],
            "assertions": ["custom_assertion"]
        }
```

### Batch Processing

Generate tests for multiple files:

```python
async def batch_generate_tests(file_paths: list[str]):
    generator = TestGenerator(workspace_root=".")

    results = []
    for file_path in file_paths:
        try:
            test_file = await generator.generate_test_file(file_path)
            results.append((file_path, test_file, "success"))
        except Exception as e:
            results.append((file_path, None, str(e)))

    return results
```

### Integration with CI/CD

```python
async def ci_coverage_check():
    """Check coverage and generate tests for gaps."""
    gaps = await find_untested_code()

    critical_gaps = [g for g in gaps if g.risk_level == "critical"]

    if critical_gaps:
        print(f"Found {len(critical_gaps)} critical coverage gaps!")
        for gap in critical_gaps:
            print(f"  {gap.file}: {gap.coverage_percent:.1f}%")

        # Fail CI if critical gaps exist
        return False

    return True
```

## Coverage Integration

The test generator integrates with `coverage.py` to identify untested code.

### Running with Coverage

```bash
# Run tests with coverage
pytest --cov=api --cov-report=json

# Generate tests for gaps
python -c "
import asyncio
from api.services.testing import find_untested_code

async def main():
    gaps = await find_untested_code()
    for gap in gaps:
        print(f'{gap.file}: {gap.coverage_percent:.1f}%')

asyncio.run(main())
"
```

### Coverage Configuration

Add to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["api"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
precision = 2
show_missing = true
fail_under = 80
```

## Best Practices

### 1. Review Generated Tests

Always review and customize generated tests:

```python
# Generate base test
test = await generator.generate_unit_test(analysis)

# Review and customize
print(test.code)
# Edit as needed before saving
```

### 2. Use Property-Based Tests for Pure Functions

```python
# Pure functions are ideal for property tests
if analysis.is_pure:
    prop_test = await generator.generate_property_test(analysis)
    if prop_test:
        # Add property test to suite
        print(prop_test.code)
```

### 3. Prioritize by Complexity

```python
# Focus on complex functions first
if analysis.cyclomatic_complexity > 5:
    # Generate comprehensive tests
    unit_test = await generator.generate_unit_test(analysis)
    edge_tests = await generator.generate_edge_cases(analysis)
```

### 4. Regular Coverage Analysis

```python
# Run weekly coverage analysis
async def weekly_coverage_report():
    gaps = await find_untested_code()

    # Generate report
    report = {
        "total_gaps": len(gaps),
        "critical": [g for g in gaps if g.risk_level == "critical"],
        "high": [g for g in gaps if g.risk_level == "high"],
    }

    return report
```

## TypeScript Support

While the current implementation focuses on Python, the architecture supports TypeScript:

```python
# Configure for TypeScript
generator = TestGenerator(
    workspace_root=".",
    framework=TestFramework.JEST
)

# Generate Jest tests (future feature)
# test = await generator.generate_test_file("myModule.ts")
```

## Examples

See `examples.py` for comprehensive usage examples:

```bash
python -m api.services.testing.examples
```

Examples include:
1. Generate unit test for specific function
2. Generate edge case tests
3. Generate property-based tests
4. Generate API integration tests
5. Suggest mocks and fixtures
6. Find coverage gaps
7. Generate complete test file
8. Batch process multiple files
9. Comprehensive coverage analysis

## Troubleshooting

### No Coverage Data

If `find_coverage_gaps()` returns empty:

```bash
# Run tests with coverage first
pytest --cov=api --cov-report=term

# Then find gaps
python -c "import asyncio; from api.services.testing import find_untested_code; asyncio.run(find_untested_code())"
```

### AST Parse Errors

If file parsing fails:

```python
try:
    analysis = await generator.analyze_function(file_path, function_name)
except SyntaxError as e:
    print(f"Syntax error in {file_path}: {e}")
```

### Import Path Issues

Ensure proper Python path:

```python
import sys
sys.path.insert(0, "/path/to/project")

from api.services.testing import TestGenerator
```

## Contributing

To extend the test generator:

1. Add new test type to `TestType` enum
2. Implement generation method in `TestGenerator`
3. Add template in `_generate_*` methods
4. Update `generate_test_file()` to include new type
5. Add tests for new functionality

## License

Part of MagnetarCode - see main project license.
