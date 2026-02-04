# Auto-Healing Test System - Quick Reference Card

## Import

```python
from services.testing import (
    AutoHealer,
    HealingStrategy,
    FailureType,
    TestFramework,
    TestFailure,
    HealingResult
)
from services.testing.config import get_config, HealingMode
```

## Basic Usage

```python
import asyncio
from pathlib import Path

# Create healer
healer = AutoHealer()

# Heal a test file
result = await healer.heal_test_failure(Path("tests/test_api.py"))

# Check result
if result.success:
    print(f"✓ Healed successfully")
    print(f"Strategy: {result.strategy.value}")
else:
    print(f"✗ Failed: {result.error}")

# View report
print(result.report)
```

## Configuration Modes

```python
from services.testing.config import get_config

# Conservative (90%+ confidence)
config = get_config("conservative")

# Balanced (70%+ confidence) - DEFAULT
config = get_config("balanced")

# Aggressive (50%+ confidence)
config = get_config("aggressive")

# Dry-run (analysis only)
config = get_config("dry_run")
```

## Healing Strategies

| Strategy | Auto-Fix | Confidence | Use Case |
|----------|----------|------------|----------|
| `FIX_IMPORT` | ✅ Yes | 90% | Missing imports |
| `UPDATE_EXPECTED` | ✅ Yes | 70% | Changed behavior |
| `UPDATE_MOCK` | ✅ Yes | 80% | API changes |
| `ADJUST_ASSERTION` | ⚠️ Partial | 50% | Wrong assertion |
| `FIX_CODE` | ❌ No | 60-80% | Code issues |
| `MANUAL_REVIEW` | ❌ No | <50% | Complex issues |
| `SKIP` | ✅ Yes | N/A | Already passing |
| `FIX_TEST` | ✅ Yes | Variable | General fix |

## Failure Types

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

## Common Patterns

### Pattern 1: Heal Single File

```python
async def heal_file():
    healer = AutoHealer()
    result = await healer.heal_test_failure(Path("tests/test.py"))
    return result.success
```

### Pattern 2: Batch Healing

```python
async def heal_directory(directory: Path):
    healer = AutoHealer()

    for test_file in directory.glob("**/test_*.py"):
        result = await healer.heal_test_failure(test_file)
        print(f"{test_file.name}: {'✓' if result.success else '✗'}")

    print(healer.get_healing_report())
```

### Pattern 3: Dry Run Analysis

```python
async def analyze_failures(test_file: Path):
    healer = AutoHealer()

    # Run tests
    success, output = await healer.run_tests(test_file)

    if not success:
        # Parse failures
        failures = healer.parse_failures(output, test_file)

        # Analyze each
        for failure in failures:
            analysis = healer.analyze_failure(failure)
            print(f"Test: {failure.test_name}")
            print(f"Strategy: {analysis['suggested_strategy'].value}")
            print(f"Confidence: {analysis['confidence']:.2%}")
```

### Pattern 4: Custom Healing with Filters

```python
async def selective_healing(test_file: Path):
    healer = AutoHealer()

    # Run tests
    success, output = await healer.run_tests(test_file)

    if not success:
        failures = healer.parse_failures(output, test_file)

        for failure in failures:
            analysis = healer.analyze_failure(failure)

            # Only auto-fix high-confidence import errors
            if (analysis['suggested_strategy'] == HealingStrategy.FIX_IMPORT
                and analysis['confidence'] >= 0.9):

                await healer.apply_fix(analysis)
                success, _ = await healer.verify_fix(test_file)

                print(f"Fixed {failure.test_name}: {success}")
```

### Pattern 5: Export Results

```python
async def heal_and_export():
    healer = AutoHealer()

    # Heal multiple files
    for test_file in Path("tests").glob("**/test_*.py"):
        await healer.heal_test_failure(test_file)

    # Export results
    healer.export_results(Path("healing_results.json"))

    # Get summary
    print(healer.get_healing_report())
```

## CLI Commands

```bash
# Heal a specific file
python -m services.testing.auto_healer tests/test_api.py

# Run interactive demo
python apps/backend/api/services/testing/examples/demo_auto_healer.py

# Run specific demo
python apps/backend/api/services/testing/examples/demo_auto_healer.py --demo basic

# Dry run
python apps/backend/api/services/testing/examples/demo_auto_healer.py \
    --test-file tests/test.py --dry-run

# Batch healing
python apps/backend/api/services/testing/examples/demo_auto_healer.py \
    --batch tests/
```

## Configuration Options

```python
from services.testing.config import AutoHealerConfig, HealingMode

config = AutoHealerConfig(
    mode=HealingMode.BALANCED,
    max_healing_attempts=3,
    verify_fixes=True,

    # Confidence thresholds
    min_confidence_import_fix=0.9,
    min_confidence_update_expected=0.7,
    min_confidence_update_mock=0.8,

    # Timeouts
    test_execution_timeout=60,
    verification_timeout=30,

    # Safety
    backup_before_fix=True,
    require_git_clean=False,

    # Reporting
    generate_reports=True,
    export_json=True
)

healer = AutoHealer(max_healing_attempts=config.max_healing_attempts)
```

## API Reference

### AutoHealer

```python
class AutoHealer:
    def __init__(self, max_healing_attempts: int = 3)

    async def run_tests(self, test_file: Path) -> Tuple[bool, str]
    def parse_failures(self, output: str, test_file: Path) -> List[TestFailure]
    def analyze_failure(self, failure: TestFailure) -> Dict[str, Any]
    def suggest_fix(self, analysis: Dict[str, Any]) -> Optional[str]
    async def apply_fix(self, analysis: Dict[str, Any]) -> bool
    async def verify_fix(self, test_file: Path) -> Tuple[bool, str]
    async def heal_test_failure(self, test_file: Path, initial_output: Optional[str] = None) -> HealingResult

    def get_healing_report(self) -> str
    def export_results(self, output_file: Path) -> None
    def detect_test_framework(self, test_file: Path) -> TestFramework
```

### TestFailure

```python
@dataclass
class TestFailure:
    test_file: Path
    test_name: str
    failure_type: FailureType
    error_message: str
    traceback: str
    framework: TestFramework
    line_number: Optional[int] = None
    failed_assertion: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    missing_import: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]
```

### HealingResult

```python
@dataclass
class HealingResult:
    success: bool
    strategy: HealingStrategy
    failure: TestFailure
    applied_fix: Optional[str] = None
    verification_passed: bool = False
    error: Optional[str] = None
    report: str = ""

    def to_dict(self) -> Dict[str, Any]
```

## File Locations

```
/Users/indiedevhipps/Documents/MagnetarCode/apps/backend/api/services/testing/
├── auto_healer.py           # Main implementation
├── config.py                # Configuration system
├── test_auto_healer.py      # Test suite
├── __init__.py              # Package exports
├── README.md                # Full documentation
├── QUICKSTART.md            # Quick start guide
├── REFERENCE.md             # This file
└── examples/
    ├── demo_auto_healer.py  # Interactive demo
    ├── example_python_test.py
    └── example_typescript_test.ts
```

## Troubleshooting

### Import Error

```python
# Error: ModuleNotFoundError
# Solution: Check Python path
import sys
sys.path.insert(0, '/path/to/MagnetarCode/apps/backend')
from api.services.testing import AutoHealer
```

### Tests Not Running

```python
# Error: Command not found: pytest
# Solution: Install pytest
pip install pytest

# Error: Command not found: npm
# Solution: Install Node.js and npm
```

### No Failures Detected

```python
# Check if tests actually failed
success, output = await healer.run_tests(test_file)
print(f"Success: {success}")
print(f"Output:\n{output}")

# If parsing failed, check output format
failures = healer.parse_failures(output, test_file)
print(f"Detected {len(failures)} failures")
```

## Best Practices

1. **Start with dry-run mode**
   ```python
   config = get_config("dry_run")
   ```

2. **Use version control**
   ```bash
   git checkout -b auto-heal-tests
   ```

3. **Review changes before committing**
   ```bash
   git diff tests/
   ```

4. **Run full test suite after healing**
   ```bash
   pytest tests/ -v
   ```

5. **Export results for review**
   ```python
   healer.export_results(Path("results.json"))
   ```

## Security Notes

- ✅ Uses `asyncio.create_subprocess_exec` (secure)
- ✅ No shell injection vulnerabilities
- ✅ No `shell=True` usage
- ✅ Array-based command arguments
- ✅ File path validation
- ✅ Permission checks

## Performance Tips

- Use parallel healing for large test suites
- Cache analysis results with `cache_analysis_results=True`
- Set appropriate timeouts
- Use `max_healing_attempts` wisely (default: 3)

## Support

- **Documentation**: README.md, QUICKSTART.md
- **Examples**: examples/demo_auto_healer.py
- **Tests**: test_auto_healer.py
- **Issues**: Check logs for detailed error messages

---

**Quick Help**: `python -m services.testing.auto_healer --help`
