# Auto-Healing Test System

A comprehensive, production-grade test auto-healing system for MagnetarCode that automatically detects, analyzes, and fixes test failures across Python (pytest) and TypeScript (jest) tests.

## Features

### 1. Test Failure Detection
- Parses pytest and jest output to extract detailed failure information
- Identifies failure types (assertion errors, import errors, API changes, etc.)
- Extracts expected vs. actual values, line numbers, and stack traces

### 2. Intelligent Analysis
- Analyzes test code using AST parsing (Python) and regex (TypeScript)
- Determines root cause of failures
- Distinguishes between test issues and code issues
- Provides confidence scores for healing strategies

### 3. Auto-Fixing Capabilities
- **Import Errors**: Automatically adds missing imports
- **Assertion Mismatches**: Updates expected values when code intentionally changed
- **Mock Data**: Adjusts mock configurations for API changes
- **Type Errors**: Identifies implementation issues
- **API Changes**: Detects and adapts to API modifications

### 4. Verification & Reporting
- Re-runs tests to verify fixes worked
- Generates comprehensive healing reports
- Tracks healing history and success rates
- Exports results to JSON for further analysis

## Architecture

### Core Components

#### AutoHealer
Main orchestrator that coordinates all healing activities.

```python
healer = AutoHealer(max_healing_attempts=3)
result = await healer.heal_test_failure(test_file_path)
```

#### TestOutputParser
Parses test framework output to extract failure details.

```python
parser = TestOutputParser()
failures = parser.parse_pytest_output(output, test_file)
```

#### CodeAnalyzer
Analyzes test code to understand context and suggest fixes.

```python
analyzer = CodeAnalyzer()
analysis = analyzer.analyze_python_test(test_file, failure)
```

#### TestFixer
Applies fixes to test files.

```python
fixer = TestFixer()
success = fixer.fix_python_import(test_file, "missing_module")
```

#### TestRunner
Executes tests and captures output.

```python
runner = TestRunner()
success, output = await runner.run_pytest(test_file)
```

### Data Models

#### TestFailure
Represents a test failure with complete context.

```python
@dataclass
class TestFailure:
    test_file: Path
    test_name: str
    failure_type: FailureType
    error_message: str
    traceback: str
    framework: TestFramework
    line_number: Optional[int]
    failed_assertion: Optional[str]
    expected_value: Optional[Any]
    actual_value: Optional[Any]
    missing_import: Optional[str]
    timestamp: datetime
```

#### HealingResult
Contains the outcome of a healing attempt.

```python
@dataclass
class HealingResult:
    success: bool
    strategy: HealingStrategy
    failure: TestFailure
    applied_fix: Optional[str]
    verification_passed: bool
    error: Optional[str]
    report: str
```

### Enumerations

#### FailureType
```python
class FailureType(Enum):
    ASSERTION_ERROR = "assertion_error"
    IMPORT_ERROR = "import_error"
    ATTRIBUTE_ERROR = "attribute_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    API_CHANGE = "api_change"
    MOCK_ERROR = "mock_error"
    TIMEOUT_ERROR = "timeout_error"
    SYNTAX_ERROR = "syntax_error"
    UNKNOWN = "unknown"
```

#### HealingStrategy
```python
class HealingStrategy(Enum):
    FIX_TEST = "fix_test"
    FIX_CODE = "fix_code"
    SKIP = "skip"
    MANUAL_REVIEW = "manual_review"
    UPDATE_EXPECTED = "update_expected"
    FIX_IMPORT = "fix_import"
    UPDATE_MOCK = "update_mock"
    ADJUST_ASSERTION = "adjust_assertion"
```

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from services.testing import AutoHealer

async def heal_tests():
    # Create healer instance
    healer = AutoHealer(max_healing_attempts=3)

    # Heal a specific test file
    test_file = Path("tests/test_example.py")
    result = await healer.heal_test_failure(test_file)

    # Print report
    print(result.report)

    # Check if healing was successful
    if result.success:
        print(f"Successfully healed with strategy: {result.strategy.value}")
    else:
        print(f"Healing failed: {result.error}")
```

### Batch Healing

```python
from pathlib import Path
from services.testing import AutoHealer

async def heal_all_tests(test_directory: Path):
    healer = AutoHealer()

    # Find all test files
    test_files = list(test_directory.glob("**/test_*.py"))

    results = []
    for test_file in test_files:
        print(f"Healing {test_file}...")
        result = await healer.heal_test_failure(test_file)
        results.append(result)

    # Get summary report
    print(healer.get_healing_report())

    # Export results
    healer.export_results(Path("healing_results.json"))
```

### Custom Analysis

```python
from services.testing import AutoHealer, FailureType, HealingStrategy

async def custom_healing():
    healer = AutoHealer()

    # Run tests manually first
    test_file = Path("tests/test_api.py")
    success, output = await healer.run_tests(test_file)

    if not success:
        # Parse failures
        failures = healer.parse_failures(output, test_file)

        for failure in failures:
            # Analyze each failure
            analysis = healer.analyze_failure(failure)

            print(f"Test: {failure.test_name}")
            print(f"Type: {failure.failure_type.value}")
            print(f"Strategy: {analysis['suggested_strategy'].value}")
            print(f"Confidence: {analysis['confidence']}")
            print(f"Reasoning: {analysis['reasoning']}")

            # Apply fix only if confidence is high
            if analysis['confidence'] > 0.8:
                fix_applied = await healer.apply_fix(analysis)
                if fix_applied:
                    # Verify the fix
                    success, verify_output = await healer.verify_fix(test_file)
                    print(f"Fix verified: {success}")
```

### CLI Usage

```bash
# Run directly as a script
python auto_healer.py tests/test_example.py

# Or use as a module
python -m services.testing.auto_healer tests/test_example.py
```

## Healing Strategies

### 1. FIX_IMPORT
**When Used**: Import errors detected (ImportError, ModuleNotFoundError)

**Action**: Automatically adds missing import statements

**Example**:
```python
# Before
def test_user_creation():
    user = User(name="John")  # NameError: User is not defined

# After (auto-healed)
from models import User

def test_user_creation():
    user = User(name="John")
```

### 2. UPDATE_EXPECTED
**When Used**: Assertion errors where code behavior intentionally changed

**Action**: Updates expected values to match new actual values

**Example**:
```python
# Before
def test_calculate_total():
    assert calculate_total([1, 2, 3]) == 6  # AssertionError: 7 != 6

# After (auto-healed)
def test_calculate_total():
    assert calculate_total([1, 2, 3]) == 7  # Updated to new behavior
```

### 3. UPDATE_MOCK
**When Used**: Mock-related errors when API changes

**Action**: Updates mock configurations

**Example**:
```python
# Before
@patch('service.get_user')
def test_user_service(mock_get):
    mock_get.return_value = {'name': 'John'}  # API now returns User object

# After (auto-healed)
@patch('service.get_user')
def test_user_service(mock_get):
    mock_get.return_value = User(name='John')
```

### 4. FIX_CODE
**When Used**: Issues in implementation code detected

**Action**: Flags for manual code fixes (cannot auto-fix implementation)

### 5. MANUAL_REVIEW
**When Used**: Complex issues requiring human judgment

**Action**: Generates detailed report for developer review

## Confidence Scoring

The system assigns confidence scores (0.0 to 1.0) to healing strategies:

- **0.9+**: Very high confidence - auto-fix without hesitation
- **0.7-0.9**: High confidence - auto-fix with logging
- **0.5-0.7**: Medium confidence - suggest fix, require approval
- **< 0.5**: Low confidence - manual review required

## Error Handling

The system includes comprehensive error handling:

```python
try:
    result = await healer.heal_test_failure(test_file)
except FileNotFoundError:
    print(f"Test file not found: {test_file}")
except ValueError as e:
    print(f"Invalid test file: {e}")
except Exception as e:
    logger.error(f"Unexpected error during healing: {e}")
```

## Best Practices

### 1. Version Control
Always run auto-healer on version-controlled code:

```bash
# Create a branch for auto-healing
git checkout -b auto-heal-tests

# Run healer
python auto_healer.py tests/

# Review changes
git diff

# Commit if satisfied
git commit -am "Auto-heal test failures"
```

### 2. Gradual Rollout
Start with high-confidence fixes only:

```python
healer = AutoHealer()
result = await healer.heal_test_failure(test_file)

# Only apply if confidence is very high
if result.strategy.confidence >= 0.9:
    # Changes were already applied and verified
    print("High-confidence fix applied")
else:
    print("Manual review required")
```

### 3. Review Reports
Always review healing reports before committing:

```python
# Get detailed report
print(healer.get_healing_report())

# Export for review
healer.export_results(Path("healing_audit.json"))
```

### 4. Test After Healing
Run full test suite after healing:

```bash
# Heal individual tests
python auto_healer.py tests/test_api.py

# Run full suite to check for side effects
pytest tests/
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Auto-Heal Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  auto-heal:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        id: tests
        continue-on-error: true
        run: pytest tests/

      - name: Auto-heal failures
        if: steps.tests.outcome == 'failure'
        run: |
          python -m services.testing.auto_healer tests/

      - name: Verify healing
        run: pytest tests/

      - name: Upload healing report
        uses: actions/upload-artifact@v2
        with:
          name: healing-report
          path: healing_results.json
```

## Performance Considerations

- **Parallel Healing**: Process multiple test files concurrently
- **Caching**: Cache AST analysis results for repeated runs
- **Timeout Management**: Configure appropriate timeouts for test execution
- **Resource Limits**: Set max healing attempts to prevent infinite loops

## Limitations

1. **Complex Logic**: Cannot fix complex algorithmic issues
2. **Business Logic**: Cannot determine correct business behavior
3. **External Dependencies**: Limited ability to fix external service issues
4. **Security**: Won't fix security-related test failures automatically
5. **Performance Tests**: Cannot optimize performance issues

## Security Considerations

The auto-healer uses secure subprocess execution:

- Uses `asyncio.create_subprocess_exec` (no shell injection risk)
- Validates file paths before operations
- Limits file modifications to test files only
- Logs all changes for audit trail
- Respects file permissions

## Logging

Comprehensive logging is built-in:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Get healer logger
logger = logging.getLogger('services.testing.auto_healer')

# Healer automatically logs:
# - Test execution
# - Failure detection
# - Analysis results
# - Fix applications
# - Verification results
```

## Troubleshooting

### Issue: Tests not detected
**Solution**: Ensure test files follow naming conventions (`test_*.py` or `*.test.ts`)

### Issue: Fixes not applied
**Solution**: Check file permissions and ensure files are writable

### Issue: Verification fails
**Solution**: Review the healing report for details; may require manual intervention

### Issue: Import fixes incorrect
**Solution**: Ensure project structure is correct and modules are importable

## Future Enhancements

- Machine learning for better failure prediction
- Integration with code review tools
- Support for more test frameworks (unittest, mocha, etc.)
- Visual diff reports for applied changes
- Automatic PR creation for healed tests
- Integration with test coverage tools
- Support for flaky test detection and stabilization

## Contributing

When extending the auto-healer:

1. Add new failure types to `FailureType` enum
2. Implement detection logic in `TestOutputParser`
3. Add analysis logic in `CodeAnalyzer`
4. Implement fix logic in `TestFixer`
5. Add comprehensive tests
6. Update documentation

## License

Part of MagnetarCode - see main project license.
