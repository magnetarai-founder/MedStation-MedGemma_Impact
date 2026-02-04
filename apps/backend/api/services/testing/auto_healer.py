"""
Auto-Healing Test System for MagnetarCode

Automatically detects, analyzes, and fixes test failures across Python (pytest) and TypeScript (jest) tests.

Features:
- Parse test output to identify failures
- Analyze root cause (assertion mismatch, import error, API change, etc.)
- Determine if test needs fixing or code needs fixing
- Auto-fix simple issues (imports, expected values, mocks, assertions)
- Re-run tests to verify fixes
- Generate comprehensive healing reports

Usage:
    healer = AutoHealer()
    result = await healer.heal_test_failure(test_file_path)
    print(result.report)

Note: This implementation uses asyncio.create_subprocess_exec which is secure
and does not have shell injection vulnerabilities (no shell=True).
"""

import ast
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of test failures that can be detected."""
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


class HealingStrategy(Enum):
    """Strategies for healing test failures."""
    FIX_TEST = "fix_test"
    FIX_CODE = "fix_code"
    SKIP = "skip"
    MANUAL_REVIEW = "manual_review"
    UPDATE_EXPECTED = "update_expected"
    FIX_IMPORT = "fix_import"
    UPDATE_MOCK = "update_mock"
    ADJUST_ASSERTION = "adjust_assertion"


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JEST = "jest"
    UNITTEST = "unittest"


@dataclass
class TestFailure:
    """Represents a test failure with all relevant details."""
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'test_file': str(self.test_file),
            'test_name': self.test_name,
            'failure_type': self.failure_type.value,
            'error_message': self.error_message,
            'traceback': self.traceback,
            'framework': self.framework.value,
            'line_number': self.line_number,
            'failed_assertion': self.failed_assertion,
            'expected_value': str(self.expected_value),
            'actual_value': str(self.actual_value),
            'missing_import': self.missing_import,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class HealingResult:
    """Result of attempting to heal a test failure."""
    success: bool
    strategy: HealingStrategy
    failure: TestFailure
    applied_fix: Optional[str] = None
    verification_passed: bool = False
    error: Optional[str] = None
    report: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'strategy': self.strategy.value,
            'failure': self.failure.to_dict(),
            'applied_fix': self.applied_fix,
            'verification_passed': self.verification_passed,
            'error': self.error,
            'report': self.report
        }


class TestOutputParser:
    """Parses test output from pytest and jest to extract failure information."""

    @staticmethod
    def parse_pytest_output(output: str, test_file: Path) -> List[TestFailure]:
        """Parse pytest output to extract test failures."""
        failures = []
        # Pattern to match FAILED line and capture the error line that follows
        # Matches blocks like: FAILED path::test_name\nE       ErrorType: message
        failure_block_pattern = r'FAILED\s+([\w\./]+)::([\w]+)\s*\n\s*E\s+(.+?)(?=\n\s*FAILED|\n\s*=|\Z)'
        assertion_pattern = r'assert\s+(.+?)\s+==\s+(.+)'
        import_error_pattern = r"No module named ['\"]?(.+?)['\"]?"

        for match in re.finditer(failure_block_pattern, output, re.DOTALL):
            test_name = match.group(2)
            error_block = match.group(3).strip()
            error_message = error_block

            failure_type = FailureType.UNKNOWN
            expected_val = None
            actual_val = None
            missing_import = None

            # Determine failure type from THIS test's error block, not the whole output
            if 'AssertionError' in error_block:
                failure_type = FailureType.ASSERTION_ERROR
                assertion_match = re.search(assertion_pattern, error_block)
                if assertion_match:
                    actual_val = assertion_match.group(1).strip()
                    expected_val = assertion_match.group(2).strip()
            elif 'ImportError' in error_block or 'ModuleNotFoundError' in error_block:
                failure_type = FailureType.IMPORT_ERROR
                import_match = re.search(import_error_pattern, error_block)
                if import_match:
                    missing_import = import_match.group(1).strip()
            elif 'AttributeError' in error_block:
                failure_type = FailureType.ATTRIBUTE_ERROR
            elif 'TypeError' in error_block:
                failure_type = FailureType.TYPE_ERROR
            elif 'ValueError' in error_block:
                failure_type = FailureType.VALUE_ERROR

            line_match = re.search(rf'{re.escape(str(test_file))}:(\d+)', error_block)
            line_number = int(line_match.group(1)) if line_match else None

            failures.append(TestFailure(
                test_file=test_file,
                test_name=test_name,
                failure_type=failure_type,
                error_message=error_message,
                traceback=output,
                framework=TestFramework.PYTEST,
                line_number=line_number,
                expected_value=expected_val,
                actual_value=actual_val,
                missing_import=missing_import
            ))

        return failures

    @staticmethod
    def parse_jest_output(output: str, test_file: Path) -> List[TestFailure]:
        """Parse jest output to extract test failures."""
        failures = []
        # Updated pattern to match test names with › separator and other special chars
        # Jest format: ● TestSuite › test name\n\n  error block
        failure_pattern = r'●\s+([^\n]+)\n\n\s+(.*?)(?=\n\n●|\n\n\s*$|\Z)'
        expected_pattern = r'Expected:\s+(.+)'
        received_pattern = r'Received:\s+(.+)'

        for match in re.finditer(failure_pattern, output, re.DOTALL):
            test_name = match.group(1).strip()
            error_block = match.group(2)

            failure_type = FailureType.UNKNOWN
            expected_val = None
            actual_val = None
            error_message = error_block

            if 'expect' in error_block.lower():
                failure_type = FailureType.ASSERTION_ERROR
                exp_match = re.search(expected_pattern, error_block)
                rec_match = re.search(received_pattern, error_block)
                if exp_match:
                    expected_val = exp_match.group(1).strip()
                if rec_match:
                    actual_val = rec_match.group(1).strip()
            elif 'Cannot find module' in error_block or 'is not defined' in error_block:
                failure_type = FailureType.IMPORT_ERROR
            elif 'TypeError' in error_block:
                failure_type = FailureType.TYPE_ERROR

            line_match = re.search(rf'{test_file.name}:(\d+):\d+', error_block)
            line_number = int(line_match.group(1)) if line_match else None

            failures.append(TestFailure(
                test_file=test_file,
                test_name=test_name,
                failure_type=failure_type,
                error_message=error_message,
                traceback=error_block,
                framework=TestFramework.JEST,
                line_number=line_number,
                expected_value=expected_val,
                actual_value=actual_val
            ))

        return failures


class CodeAnalyzer:
    """Analyzes code to understand test failures and suggest fixes."""

    @staticmethod
    def analyze_python_test(test_file: Path, failure: TestFailure) -> Dict[str, Any]:
        """Analyze Python test file to understand the failure."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            analysis = {
                'imports': [],
                'test_functions': [],
                'assertions': [],
                'mocks': [],
                'fixtures': []
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    analysis['imports'].extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    analysis['imports'].extend([f"{module}.{alias.name}" for alias in node.names])

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    analysis['test_functions'].append(node.name)
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assert):
                            try:
                                assertion_code = ast.unparse(child)
                                analysis['assertions'].append({
                                    'function': node.name,
                                    'code': assertion_code,
                                    'line': child.lineno
                                })
                            except Exception:
                                pass

            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze Python test {test_file}: {e}")
            return {}

    @staticmethod
    def analyze_typescript_test(test_file: Path, failure: TestFailure) -> Dict[str, Any]:
        """Analyze TypeScript test file to understand the failure."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()

            analysis = {
                'imports': [],
                'test_blocks': [],
                'assertions': [],
                'mocks': []
            }

            import_pattern = r'import\s+(?:{([^}]+)}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'
            for match in re.finditer(import_pattern, content):
                if match.group(1):
                    imports = [imp.strip() for imp in match.group(1).split(',')]
                    analysis['imports'].extend(imports)
                elif match.group(2):
                    analysis['imports'].append(match.group(2))

            test_pattern = r'(?:it|test)\([\'"](.+?)[\'"]'
            for match in re.finditer(test_pattern, content):
                analysis['test_blocks'].append(match.group(1))

            expect_pattern = r'expect\((.+?)\)\.(.+?)(?:\((.+?)\))?;'
            for match in re.finditer(expect_pattern, content):
                analysis['assertions'].append({
                    'actual': match.group(1),
                    'matcher': match.group(2),
                    'expected': match.group(3) if match.group(3) else None
                })

            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze TypeScript test {test_file}: {e}")
            return {}


class TestFixer:
    """Applies fixes to test files."""

    @staticmethod
    def fix_python_import(test_file: Path, missing_import: str) -> bool:
        """Fix missing import in Python test file."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    last_import_idx = i

            if '.' in missing_import:
                parts = missing_import.split('.')
                import_stmt = f"from {'.'.join(parts[:-1])} import {parts[-1]}\n"
            else:
                import_stmt = f"import {missing_import}\n"

            insert_idx = last_import_idx + 1 if last_import_idx >= 0 else 0
            lines.insert(insert_idx, import_stmt)

            with open(test_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            logger.info(f"Fixed import in {test_file}: {import_stmt.strip()}")
            return True
        except Exception as e:
            logger.error(f"Failed to fix import in {test_file}: {e}")
            return False

    @staticmethod
    def update_python_assertion(test_file: Path, line_number: int,
                                old_value: str, new_value: str) -> bool:
        """Update assertion expected value in Python test."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_number and 1 <= line_number <= len(lines):
                line = lines[line_number - 1]
                updated_line = line.replace(old_value, new_value)
                lines[line_number - 1] = updated_line

                with open(test_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"Updated assertion in {test_file}:{line_number}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update assertion in {test_file}: {e}")
            return False

    @staticmethod
    def fix_typescript_import(test_file: Path, missing_module: str) -> bool:
        """Fix missing import in TypeScript test file."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('import '):
                    last_import_idx = i

            import_stmt = f"import {{ {missing_module} }} from './{missing_module}';\n"
            insert_idx = last_import_idx + 1 if last_import_idx >= 0 else 0
            lines.insert(insert_idx, import_stmt)

            with open(test_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            logger.info(f"Fixed TypeScript import in {test_file}: {import_stmt.strip()}")
            return True
        except Exception as e:
            logger.error(f"Failed to fix TypeScript import in {test_file}: {e}")
            return False

    @staticmethod
    def update_typescript_expectation(test_file: Path, line_number: int,
                                      old_value: str, new_value: str) -> bool:
        """Update expectation in TypeScript test."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_number and 1 <= line_number <= len(lines):
                line = lines[line_number - 1]
                updated_line = line.replace(old_value, new_value)
                lines[line_number - 1] = updated_line

                with open(test_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"Updated expectation in {test_file}:{line_number}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update expectation in {test_file}: {e}")
            return False


class TestRunner:
    """Runs tests and captures output. Uses secure subprocess execution."""

    @staticmethod
    async def run_pytest(test_file: Path, timeout: int = 60) -> Tuple[bool, str]:
        """Run pytest on a specific test file. Uses secure subprocess (no shell injection)."""
        try:
            cmd = ['pytest', str(test_file), '-v', '--tb=short']
            # Using create_subprocess_exec (secure - no shell injection)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=test_file.parent
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                output = stdout.decode('utf-8', errors='replace')
                success = process.returncode == 0
                return success, output
            except asyncio.TimeoutError:
                process.kill()
                return False, f"Test execution timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Failed to run pytest on {test_file}: {e}")
            return False, str(e)

    @staticmethod
    async def run_jest(test_file: Path, timeout: int = 60) -> Tuple[bool, str]:
        """Run jest on a specific test file. Uses secure subprocess (no shell injection)."""
        try:
            cmd = ['npm', 'test', '--', str(test_file)]
            # Using create_subprocess_exec (secure - no shell injection)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=test_file.parent
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                output = stdout.decode('utf-8', errors='replace')
                success = process.returncode == 0
                return success, output
            except asyncio.TimeoutError:
                process.kill()
                return False, f"Test execution timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Failed to run jest on {test_file}: {e}")
            return False, str(e)


class AutoHealer:
    """
    Main auto-healing system that orchestrates test failure detection,
    analysis, fixing, and verification.
    """

    def __init__(self, max_healing_attempts: int = 3):
        """Initialize the auto-healer."""
        self.max_healing_attempts = max_healing_attempts
        self.parser = TestOutputParser()
        self.analyzer = CodeAnalyzer()
        self.fixer = TestFixer()
        self.runner = TestRunner()
        self.healing_history: List[HealingResult] = []

    def detect_test_framework(self, test_file: Path) -> TestFramework:
        """Detect which test framework is used based on file extension."""
        if test_file.suffix == '.py':
            return TestFramework.PYTEST
        elif test_file.suffix in ['.ts', '.tsx', '.js', '.jsx']:
            return TestFramework.JEST
        else:
            raise ValueError(f"Unsupported test file type: {test_file.suffix}")

    async def run_tests(self, test_file: Path) -> Tuple[bool, str]:
        """Run tests for the given file using appropriate framework."""
        framework = self.detect_test_framework(test_file)
        if framework == TestFramework.PYTEST:
            return await self.runner.run_pytest(test_file)
        elif framework == TestFramework.JEST:
            return await self.runner.run_jest(test_file)
        else:
            raise ValueError(f"Unsupported framework: {framework}")

    def parse_failures(self, output: str, test_file: Path) -> List[TestFailure]:
        """Parse test output to extract failures."""
        framework = self.detect_test_framework(test_file)
        if framework == TestFramework.PYTEST:
            return self.parser.parse_pytest_output(output, test_file)
        elif framework == TestFramework.JEST:
            return self.parser.parse_jest_output(output, test_file)
        else:
            return []

    def analyze_failure(self, failure: TestFailure) -> Dict[str, Any]:
        """Analyze a test failure to understand its root cause."""
        analysis = {
            'failure': failure,
            'code_analysis': {},
            'suggested_strategy': HealingStrategy.MANUAL_REVIEW,
            'confidence': 0.0,
            'reasoning': ''
        }

        if failure.framework == TestFramework.PYTEST:
            analysis['code_analysis'] = self.analyzer.analyze_python_test(
                failure.test_file, failure
            )
        elif failure.framework == TestFramework.JEST:
            analysis['code_analysis'] = self.analyzer.analyze_typescript_test(
                failure.test_file, failure
            )

        if failure.failure_type == FailureType.IMPORT_ERROR:
            analysis['suggested_strategy'] = HealingStrategy.FIX_IMPORT
            analysis['confidence'] = 0.9
            analysis['reasoning'] = "Missing import can be automatically added"
        elif failure.failure_type == FailureType.ASSERTION_ERROR:
            if failure.expected_value and failure.actual_value:
                if self._looks_like_intentional_change(failure):
                    analysis['suggested_strategy'] = HealingStrategy.UPDATE_EXPECTED
                    analysis['confidence'] = 0.7
                    analysis['reasoning'] = "Code behavior appears to have intentionally changed"
                else:
                    analysis['suggested_strategy'] = HealingStrategy.FIX_CODE
                    analysis['confidence'] = 0.6
                    analysis['reasoning'] = "Assertion failure may indicate bug in implementation"
            else:
                analysis['suggested_strategy'] = HealingStrategy.ADJUST_ASSERTION
                analysis['confidence'] = 0.5
                analysis['reasoning'] = "Assertion logic may need adjustment"
        elif failure.failure_type == FailureType.ATTRIBUTE_ERROR:
            if 'mock' in failure.error_message.lower():
                analysis['suggested_strategy'] = HealingStrategy.UPDATE_MOCK
                analysis['confidence'] = 0.8
                analysis['reasoning'] = "Mock configuration needs updating"
            else:
                analysis['suggested_strategy'] = HealingStrategy.FIX_CODE
                analysis['confidence'] = 0.7
                analysis['reasoning'] = "API may have changed, implementation needs fix"
        elif failure.failure_type == FailureType.TYPE_ERROR:
            analysis['suggested_strategy'] = HealingStrategy.FIX_CODE
            analysis['confidence'] = 0.8
            analysis['reasoning'] = "Type mismatch indicates implementation issue"

        return analysis

    def _looks_like_intentional_change(self, failure: TestFailure) -> bool:
        """Heuristic to determine if a test failure is due to intentional code change."""
        if not failure.expected_value or not failure.actual_value:
            return False
        try:
            expected = ast.literal_eval(str(failure.expected_value))
            actual = ast.literal_eval(str(failure.actual_value))
            return type(expected) == type(actual)
        except Exception:
            return False

    def suggest_fix(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Suggest a specific fix based on the analysis."""
        failure = analysis['failure']
        strategy = analysis['suggested_strategy']

        if strategy == HealingStrategy.FIX_IMPORT:
            if failure.missing_import:
                return f"Add import: {failure.missing_import}"
            return "Fix missing import"
        elif strategy == HealingStrategy.UPDATE_EXPECTED:
            if failure.expected_value and failure.actual_value:
                return f"Update expected value from {failure.expected_value} to {failure.actual_value}"
            return "Update expected value to match actual"
        elif strategy == HealingStrategy.UPDATE_MOCK:
            return "Update mock configuration to match current API"
        elif strategy == HealingStrategy.ADJUST_ASSERTION:
            return "Adjust assertion logic"
        elif strategy == HealingStrategy.FIX_CODE:
            return "Fix implementation code (requires manual intervention)"
        return None

    async def apply_fix(self, analysis: Dict[str, Any]) -> bool:
        """Apply the suggested fix to the test file."""
        failure = analysis['failure']
        strategy = analysis['suggested_strategy']

        try:
            if strategy == HealingStrategy.FIX_IMPORT:
                if failure.missing_import:
                    if failure.framework == TestFramework.PYTEST:
                        return self.fixer.fix_python_import(
                            failure.test_file, failure.missing_import
                        )
                    elif failure.framework == TestFramework.JEST:
                        return self.fixer.fix_typescript_import(
                            failure.test_file, failure.missing_import
                        )
            elif strategy == HealingStrategy.UPDATE_EXPECTED:
                if failure.line_number and failure.expected_value and failure.actual_value:
                    if failure.framework == TestFramework.PYTEST:
                        return self.fixer.update_python_assertion(
                            failure.test_file,
                            failure.line_number,
                            str(failure.expected_value),
                            str(failure.actual_value)
                        )
                    elif failure.framework == TestFramework.JEST:
                        return self.fixer.update_typescript_expectation(
                            failure.test_file,
                            failure.line_number,
                            str(failure.expected_value),
                            str(failure.actual_value)
                        )
            logger.info(f"Strategy {strategy} requires manual intervention")
            return False
        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            return False

    async def verify_fix(self, test_file: Path) -> Tuple[bool, str]:
        """Re-run tests to verify that the fix worked."""
        return await self.run_tests(test_file)

    async def heal_test_failure(
        self,
        test_file: Path,
        initial_output: Optional[str] = None
    ) -> HealingResult:
        """Main entry point for healing a test failure."""
        logger.info(f"Starting auto-healing for {test_file}")

        if not initial_output:
            success, initial_output = await self.run_tests(test_file)
            if success:
                result = HealingResult(
                    success=True,
                    strategy=HealingStrategy.SKIP,
                    failure=TestFailure(
                        test_file=test_file,
                        test_name="all",
                        failure_type=FailureType.UNKNOWN,
                        error_message="Tests already passing",
                        traceback="",
                        framework=self.detect_test_framework(test_file)
                    ),
                    verification_passed=True,
                    report="Tests are already passing - no healing needed"
                )
                self.healing_history.append(result)
                return result

        failures = self.parse_failures(initial_output, test_file)
        if not failures:
            result = HealingResult(
                success=False,
                strategy=HealingStrategy.MANUAL_REVIEW,
                failure=TestFailure(
                    test_file=test_file,
                    test_name="unknown",
                    failure_type=FailureType.UNKNOWN,
                    error_message="Could not parse test failures",
                    traceback=initial_output,
                    framework=self.detect_test_framework(test_file)
                ),
                error="Could not parse test output",
                report="Failed to identify specific test failures from output"
            )
            self.healing_history.append(result)
            return result

        healed_count = 0
        failed_count = 0
        reports = []

        for failure in failures:
            logger.info(f"Analyzing failure: {failure.test_name}")
            analysis = self.analyze_failure(failure)
            suggested_fix = self.suggest_fix(analysis)

            reports.append(f"\n{'='*60}")
            reports.append(f"Test: {failure.test_name}")
            reports.append(f"Type: {failure.failure_type.value}")
            reports.append(f"Strategy: {analysis['suggested_strategy'].value}")
            reports.append(f"Confidence: {analysis['confidence']:.2f}")
            reports.append(f"Reasoning: {analysis['reasoning']}")
            if suggested_fix:
                reports.append(f"Suggested Fix: {suggested_fix}")

            if analysis['confidence'] >= 0.7:
                logger.info(f"Attempting to apply fix with confidence {analysis['confidence']}")
                for attempt in range(self.max_healing_attempts):
                    fix_applied = await self.apply_fix(analysis)
                    if not fix_applied:
                        reports.append(f"Attempt {attempt + 1}: Failed to apply fix")
                        continue

                    reports.append(f"Attempt {attempt + 1}: Fix applied successfully")
                    success, verify_output = await self.verify_fix(test_file)

                    if success:
                        reports.append(f"Verification: PASSED")
                        healed_count += 1
                        break
                    else:
                        reports.append(f"Verification: FAILED")
                        new_failures = self.parse_failures(verify_output, test_file)
                        if new_failures:
                            reports.append(f"New failures detected: {len(new_failures)}")
                        if attempt < self.max_healing_attempts - 1:
                            reports.append("Retrying with updated analysis...")
                            analysis = self.analyze_failure(new_failures[0] if new_failures else failure)
                        else:
                            failed_count += 1
            else:
                reports.append("Confidence too low for automatic fixing - manual review required")
                failed_count += 1

        report_header = [
            f"\n{'='*60}",
            f"AUTO-HEALING REPORT",
            f"{'='*60}",
            f"Test File: {test_file}",
            f"Total Failures: {len(failures)}",
            f"Successfully Healed: {healed_count}",
            f"Failed to Heal: {failed_count}",
            f"Timestamp: {datetime.now().isoformat()}",
            ""
        ]

        final_report = '\n'.join(report_header + reports)

        overall_result = HealingResult(
            success=healed_count > 0,
            strategy=HealingStrategy.FIX_TEST if healed_count > 0 else HealingStrategy.MANUAL_REVIEW,
            failure=failures[0] if failures else None,
            applied_fix=f"Healed {healed_count}/{len(failures)} failures",
            verification_passed=healed_count == len(failures),
            report=final_report
        )

        self.healing_history.append(overall_result)
        logger.info(f"Auto-healing complete: {healed_count}/{len(failures)} healed")
        return overall_result

    def get_healing_report(self) -> str:
        """Get a summary report of all healing attempts."""
        if not self.healing_history:
            return "No healing attempts recorded"

        total_attempts = len(self.healing_history)
        successful = sum(1 for r in self.healing_history if r.success)

        report = [
            f"\n{'='*60}",
            f"AUTO-HEALING SUMMARY",
            f"{'='*60}",
            f"Total Healing Attempts: {total_attempts}",
            f"Successful: {successful}",
            f"Failed: {total_attempts - successful}",
            f"Success Rate: {(successful/total_attempts*100):.1f}%",
            ""
        ]

        for i, result in enumerate(self.healing_history, 1):
            report.append(f"\n{i}. {result.failure.test_file.name}")
            report.append(f"   Strategy: {result.strategy.value}")
            report.append(f"   Success: {result.success}")
            if result.applied_fix:
                report.append(f"   Fix: {result.applied_fix}")

        return '\n'.join(report)

    def export_results(self, output_file: Path) -> None:
        """Export healing results to JSON file."""
        try:
            results_data = [result.to_dict() for result in self.healing_history]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2)
            logger.info(f"Exported healing results to {output_file}")
        except Exception as e:
            logger.error(f"Failed to export results: {e}")


async def main():
    """Example usage of the AutoHealer system."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python auto_healer.py <test_file_path>")
        sys.exit(1)

    test_file = Path(sys.argv[1])
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)

    healer = AutoHealer()
    result = await healer.heal_test_failure(test_file)
    print(result.report)

    output_file = test_file.parent / f"healing_report_{test_file.stem}.json"
    healer.export_results(output_file)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
