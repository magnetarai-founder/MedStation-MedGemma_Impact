# MagnetarCode Testing Services - Quick Start Guide

Get started with the MagnetarCode Testing Services in minutes.

This guide covers both **Auto-Healing** and **Test Generation** capabilities.

---

## Part 1: Auto-Healing Test System

Automatically detect and fix test failures.

### Auto-Healing Quick Start

Get started with the MagnetarCode Auto-Healing Test System in minutes.

## Installation

The auto-healing system is part of MagnetarCode's testing services. No additional installation required if you have MagnetarCode set up.

### Prerequisites

- Python 3.9+
- pytest (for Python tests)
- Node.js 16+ and npm (for TypeScript tests)
- Git (recommended for safety)

### Verify Installation

```bash
python -c "from services.testing import AutoHealer; print('✓ Auto-healer installed')"
```

## 5-Minute Quick Start

### 1. Basic Usage - Heal a Single Test File

```python
import asyncio
from pathlib import Path
from services.testing import AutoHealer

async def heal_my_test():
    # Create healer
    healer = AutoHealer()

    # Heal a test file
    result = await healer.heal_test_failure(
        Path("tests/test_my_module.py")
    )

    # Check results
    print(result.report)
    print(f"Success: {result.success}")

# Run it
asyncio.run(heal_my_test())
```

### 2. Command Line Usage

```bash
# Heal a specific test file
python -m services.testing.auto_healer tests/test_example.py

# Run the demo
python apps/backend/api/services/testing/examples/demo_auto_healer.py

# Run with specific demo
python apps/backend/api/services/testing/examples/demo_auto_healer.py --demo basic
```

### 3. Batch Healing

```python
from pathlib import Path
from services.testing import AutoHealer

async def heal_all_tests():
    healer = AutoHealer()
    test_dir = Path("tests")

    # Find all Python test files
    for test_file in test_dir.glob("**/test_*.py"):
        print(f"Healing {test_file}...")
        result = await healer.heal_test_failure(test_file)

    # Get summary
    print(healer.get_healing_report())

    # Export results
    healer.export_results(Path("healing_results.json"))
```

## Common Use Cases

### Use Case 1: Fix Import Errors

**Problem**: Tests fail because of missing imports after refactoring

```python
# test_user.py - FAILING
def test_create_user():
    user = User(name="John")  # NameError: User not defined
    assert user.name == "John"
```

**Solution**: Auto-healer detects and fixes

```python
healer = AutoHealer()
result = await healer.heal_test_failure(Path("test_user.py"))
# ✓ Auto-adds: from models import User
```

**Result**:
```python
# test_user.py - FIXED
from models import User

def test_create_user():
    user = User(name="John")
    assert user.name == "John"
```

### Use Case 2: Update Expected Values After Code Changes

**Problem**: Code behavior changed, tests now fail

```python
# test_calculator.py - FAILING
def test_calculate_total():
    result = calculate_total([1, 2, 3])
    assert result == 6  # Code now returns 7
```

**Solution**: Auto-healer updates expected values

```python
healer = AutoHealer()
result = await healer.heal_test_failure(Path("test_calculator.py"))
# ✓ Updates: assert result == 6 → assert result == 7
```

### Use Case 3: Fix Mock Configurations After API Changes

**Problem**: API changed, mocks are outdated

```python
# test_service.py - FAILING
@patch('api.get_user')
def test_user_service(mock_get_user):
    # API now returns User object, not dict
    mock_get_user.return_value = {'name': 'John'}  # Wrong type!
    user = service.get_user(1)
    assert user.name == 'John'
```

**Solution**: Auto-healer suggests mock updates (requires manual review for complex cases)

```python
healer = AutoHealer()
result = await healer.heal_test_failure(Path("test_service.py"))
# Suggests: Update mock to return User object
```

## Configuration

### Quick Configuration

```python
from services.testing import AutoHealer
from services.testing.config import HealingMode

# Conservative mode - only high-confidence fixes
healer = AutoHealer()
healer.config = get_config("conservative")

# Aggressive mode - fix more issues
healer.config = get_config("aggressive")

# Dry-run mode - analyze only
healer.config = get_config("dry_run")
```

### Custom Configuration

```python
from services.testing.config import AutoHealerConfig, HealingMode

config = AutoHealerConfig(
    mode=HealingMode.BALANCED,
    max_healing_attempts=5,
    verify_fixes=True,
    backup_before_fix=True,
    min_confidence_import_fix=0.9,
    min_confidence_update_expected=0.7
)

healer = AutoHealer(max_healing_attempts=config.max_healing_attempts)
```

## Safety Features

### 1. Dry Run Mode

Analyze without making changes:

```python
from services.testing.config import get_config

config = get_config("dry_run")
healer = AutoHealer()

result = await healer.heal_test_failure(test_file)
# No changes made, only analysis performed
print(result.report)  # Shows what WOULD be done
```

### 2. Git Integration

Always run on a clean working directory:

```bash
# Create a healing branch
git checkout -b auto-heal-tests

# Run healer
python -m services.testing.auto_healer tests/

# Review changes
git diff

# Commit if satisfied
git add -A
git commit -m "Auto-heal test failures"
```

### 3. Backup Files

Enable automatic backups:

```python
from services.testing.config import AutoHealerConfig

config = AutoHealerConfig(backup_before_fix=True)
healer = AutoHealer()

# Files are backed up before modification
result = await healer.heal_test_failure(test_file)
# Original saved as: test_file.backup
```

## Understanding Results

### Success Result

```python
result = await healer.heal_test_failure(test_file)

if result.success:
    print(f"✓ Healed successfully")
    print(f"Strategy: {result.strategy.value}")
    print(f"Fix applied: {result.applied_fix}")
    print(f"Verified: {result.verification_passed}")
```

### Failure Result

```python
if not result.success:
    print(f"✗ Healing failed")
    print(f"Error: {result.error}")
    print(f"Strategy attempted: {result.strategy.value}")
    # Manual intervention required
```

### Confidence Scores

```python
healer = AutoHealer()
# ... run tests ...
failures = healer.parse_failures(output, test_file)

for failure in failures:
    analysis = healer.analyze_failure(failure)
    confidence = analysis['confidence']

    if confidence >= 0.9:
        print("✓ Very confident - auto-fix safe")
    elif confidence >= 0.7:
        print("⚠ Moderately confident - review recommended")
    else:
        print("✗ Low confidence - manual review required")
```

## Healing Strategies Reference

| Strategy | Description | Auto-Fix | Confidence |
|----------|-------------|----------|------------|
| FIX_IMPORT | Add missing imports | ✓ Yes | 90%+ |
| UPDATE_EXPECTED | Update expected values | ✓ Yes | 70%+ |
| UPDATE_MOCK | Update mock configs | ✓ Yes | 80%+ |
| ADJUST_ASSERTION | Adjust assertion logic | ⚠ Partial | 50%+ |
| FIX_CODE | Fix implementation | ✗ No | 60-80% |
| MANUAL_REVIEW | Requires human review | ✗ No | <50% |

## Best Practices

### 1. Start Conservative

```python
# First run: dry-run to see what would be changed
config = get_config("dry_run")
result = await healer.heal_test_failure(test_file)
print(result.report)

# Then run: conservative mode for high-confidence fixes only
config = get_config("conservative")
result = await healer.heal_test_failure(test_file)
```

### 2. Review Changes

```python
# Run healer
result = await healer.heal_test_failure(test_file)

# Review the report
print(result.report)

# Check what was changed
import subprocess
subprocess.run(["git", "diff", str(test_file)])
```

### 3. Run Tests After Healing

```bash
# Heal tests
python -m services.testing.auto_healer tests/

# Run full test suite to verify no side effects
pytest tests/ -v

# Or for TypeScript
npm test
```

### 4. Use Version Control

```bash
# Always work on a branch
git checkout -b auto-heal-$(date +%Y%m%d)

# Commit incrementally
python -m services.testing.auto_healer tests/test_module1.py
git add tests/test_module1.py
git commit -m "Auto-heal: test_module1"

python -m services.testing.auto_healer tests/test_module2.py
git add tests/test_module2.py
git commit -m "Auto-heal: test_module2"
```

## Troubleshooting

### Problem: "No healing attempts recorded"

**Solution**: Tests are already passing or couldn't be run

```python
# Check if tests run
success, output = await healer.run_tests(test_file)
if success:
    print("Tests already pass!")
else:
    print(output)  # See the actual error
```

### Problem: "Could not parse test failures"

**Solution**: Ensure test framework is installed and configured

```bash
# For Python tests
pip install pytest

# For TypeScript tests
npm install --save-dev jest @types/jest
```

### Problem: "Fix applied but verification failed"

**Solution**: May need multiple fixes or manual intervention

```python
# Increase max attempts
healer = AutoHealer(max_healing_attempts=5)

# Or check the specific failure
result = await healer.heal_test_failure(test_file)
print(result.report)  # See what went wrong
```

### Problem: "Permission denied"

**Solution**: Ensure test files are writable

```bash
# Check permissions
ls -l test_file.py

# Make writable if needed
chmod u+w test_file.py
```

## Examples

### Example 1: Single File Healing

```bash
cd /path/to/MagnetarCode/apps/backend
python api/services/testing/examples/demo_auto_healer.py \
    --test-file api/services/testing/examples/example_python_test.py
```

### Example 2: Batch Healing

```bash
python api/services/testing/examples/demo_auto_healer.py \
    --batch tests/
```

### Example 3: Dry Run Analysis

```bash
python api/services/testing/examples/demo_auto_healer.py \
    --test-file tests/test_example.py \
    --dry-run
```

### Example 4: Custom Script

```python
# heal_tests.py
import asyncio
from pathlib import Path
from services.testing import AutoHealer

async def main():
    healer = AutoHealer(max_healing_attempts=5)

    # Heal specific tests
    tests_to_heal = [
        "tests/test_api.py",
        "tests/test_auth.py",
        "tests/test_database.py"
    ]

    for test in tests_to_heal:
        print(f"\nHealing {test}...")
        result = await healer.heal_test_failure(Path(test))

        if result.success:
            print(f"✓ {test} healed")
        else:
            print(f"✗ {test} requires manual review")

    # Export comprehensive report
    healer.export_results(Path("healing_report.json"))
    print("\nReport saved to healing_report.json")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python heal_tests.py
```

## Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Run the examples**: Explore `examples/demo_auto_healer.py`
3. **Customize configuration**: See [config.py](config.py)
4. **Integrate with CI/CD**: Add to your build pipeline
5. **Contribute**: Extend healing strategies for your use cases

## Getting Help

- Check the full documentation: `README.md`
- Run examples: `python examples/demo_auto_healer.py --demo all`
- Review test suite: `test_auto_healer.py`
- See configuration options: `config.py`

## Quick Reference

```python
# Import
from services.testing import AutoHealer

# Create healer
healer = AutoHealer(max_healing_attempts=3)

# Heal single file
result = await healer.heal_test_failure(Path("test.py"))

# Check result
print(f"Success: {result.success}")
print(f"Strategy: {result.strategy.value}")
print(result.report)

# Get summary
print(healer.get_healing_report())

# Export results
healer.export_results(Path("results.json"))
```

Happy healing! 🔧✨

---

## Part 2: Test Generation System

Automatically generate comprehensive test suites from code analysis.

### Test Generation Quick Start

Generate tests in 5 minutes.

### Installation

```python
from api.services.testing import TestGenerator, generate_tests_for_file
```

### Use Case 1: Generate Tests for a File

**The fastest way:**

```python
import asyncio
from api.services.testing import generate_tests_for_file

async def main():
    test_file = await generate_tests_for_file(
        file_path="api/services/cache_service.py",
        workspace_root="."
    )
    print(f"Generated: {test_file}")

asyncio.run(main())
```

### Use Case 2: Generate Test for Specific Function

```python
from api.services.testing import TestGenerator

async def generate_test():
    generator = TestGenerator(workspace_root=".")

    # Analyze function
    analysis = await generator.analyze_function(
        file_path="api/services/my_module.py",
        function_name="my_function"
    )

    # Generate test
    test = await generator.generate_unit_test(analysis)
    print(test.code)
```

### Use Case 3: Find Coverage Gaps

```python
from api.services.testing import find_untested_code

async def check_coverage():
    gaps = await find_untested_code(workspace_root=".")

    for gap in gaps:
        if gap.risk_level in ["critical", "high"]:
            print(f"{gap.file}: {gap.coverage_percent:.1f}%")
```

### Use Case 4: Generate API Tests

```python
async def generate_api_test():
    generator = TestGenerator(workspace_root=".")

    analysis = await generator.analyze_function(
        file_path="api/routes/users.py",
        function_name="create_user"
    )

    api_test = await generator.generate_api_test(
        endpoint_path="/api/users",
        http_method="POST",
        analysis=analysis
    )

    print(api_test.code)
```

### Quick Reference - Test Generator

```python
# Import
from api.services.testing import TestGenerator

# Create generator
generator = TestGenerator(workspace_root=".")

# Analyze function
analysis = await generator.analyze_function(file_path, function_name)

# Generate tests
unit_test = await generator.generate_unit_test(analysis)
edge_tests = await generator.generate_edge_cases(analysis)
prop_test = await generator.generate_property_test(analysis)
api_test = await generator.generate_api_test(endpoint, method, analysis)

# Find coverage gaps
gaps = await generator.find_coverage_gaps()

# Get mock suggestions
suggestions = await generator.suggest_mocks(analysis)
```

### Running the Demo

See test generation in action:

```bash
python -m api.services.testing.demo
```

### Next Steps for Test Generation

1. **Try the demo**: `python -m api.services.testing.demo`
2. **Read full docs**: [TEST_GENERATION.md](TEST_GENERATION.md)
3. **Run examples**: `python -m api.services.testing.examples`

---

## Combined Workflow

Use both systems together for maximum effectiveness:

```python
from api.services.testing import AutoHealer, find_untested_code, TestGenerator

async def complete_testing_workflow():
    # Step 1: Find coverage gaps
    gaps = await find_untested_code()
    critical = [g for g in gaps if g.risk_level == "critical"]

    # Step 2: Generate tests for critical gaps
    generator = TestGenerator(workspace_root=".")
    for gap in critical:
        test_file = await generator.generate_test_file(gap.file)
        print(f"Generated: {test_file}")

    # Step 3: Run tests
    # (run pytest or jest here)

    # Step 4: Auto-heal any failures
    healer = AutoHealer()
    for test_file in generated_tests:
        result = await healer.heal_test_failure(test_file)
        if result.success:
            print(f"✓ {test_file} healed")

    print("Testing workflow complete!")
```

Happy testing! 🧪✨
