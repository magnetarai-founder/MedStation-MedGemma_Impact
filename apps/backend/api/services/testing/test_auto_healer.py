"""
Test suite for the Auto-Healing Test System.

Tests the auto-healer's ability to detect, analyze, and fix test failures.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from .auto_healer import (
    AutoHealer,
    TestOutputParser,
    CodeAnalyzer,
    TestFixer,
    TestRunner,
    TestFailure,
    HealingResult,
    FailureType,
    HealingStrategy,
    TestFramework
)


class TestTestOutputParser:
    """Test the TestOutputParser class."""

    def test_parse_pytest_assertion_error(self):
        """Test parsing pytest assertion error."""
        output = """
        FAILED tests/test_example.py::test_calculate
        E       AssertionError: assert 7 == 6
        E        +  where 7 = calculate_total([1, 2, 3])
        """
        test_file = Path("tests/test_example.py")

        parser = TestOutputParser()
        failures = parser.parse_pytest_output(output, test_file)

        assert len(failures) == 1
        assert failures[0].test_name == "test_calculate"
        assert failures[0].failure_type == FailureType.ASSERTION_ERROR

    def test_parse_pytest_import_error(self):
        """Test parsing pytest import error."""
        output = """
        FAILED tests/test_example.py::test_user
        E       ImportError: No module named 'datetime'
        """
        test_file = Path("tests/test_example.py")

        parser = TestOutputParser()
        failures = parser.parse_pytest_output(output, test_file)

        assert len(failures) == 1
        assert failures[0].failure_type == FailureType.IMPORT_ERROR

    def test_parse_jest_expectation_error(self):
        """Test parsing jest expectation error."""
        output = """
        ● calculateTotal › should calculate total

          expect(received).toBe(expected)

          Expected: 6
          Received: 7

            at test.ts:10:5
        """
        test_file = Path("test.ts")

        parser = TestOutputParser()
        failures = parser.parse_jest_output(output, test_file)

        assert len(failures) == 1
        assert failures[0].failure_type == FailureType.ASSERTION_ERROR
        assert failures[0].expected_value == "6"
        assert failures[0].actual_value == "7"

    def test_parse_multiple_failures(self):
        """Test parsing multiple failures."""
        output = """
        FAILED tests/test_example.py::test_one
        E       AssertionError: assert 1 == 2

        FAILED tests/test_example.py::test_two
        E       ImportError: No module named 'foo'

        FAILED tests/test_example.py::test_three
        E       TypeError: expected int, got str
        """
        test_file = Path("tests/test_example.py")

        parser = TestOutputParser()
        failures = parser.parse_pytest_output(output, test_file)

        assert len(failures) == 3
        assert failures[0].failure_type == FailureType.ASSERTION_ERROR
        assert failures[1].failure_type == FailureType.IMPORT_ERROR
        assert failures[2].failure_type == FailureType.TYPE_ERROR


class TestCodeAnalyzer:
    """Test the CodeAnalyzer class."""

    def test_analyze_python_test_basic(self, tmp_path):
        """Test basic Python test analysis."""
        test_code = '''
import pytest
from mymodule import calculate

def test_calculate():
    assert calculate(1, 2) == 3
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        analyzer = CodeAnalyzer()
        failure = TestFailure(
            test_file=test_file,
            test_name="test_calculate",
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="assert 3 == 4",
            traceback="",
            framework=TestFramework.PYTEST
        )

        analysis = analyzer.analyze_python_test(test_file, failure)

        assert 'imports' in analysis
        assert 'test_functions' in analysis
        assert 'assertions' in analysis
        assert 'pytest' in analysis['imports']
        assert 'test_calculate' in analysis['test_functions']

    def test_analyze_typescript_test_basic(self, tmp_path):
        """Test basic TypeScript test analysis."""
        test_code = '''
import { calculate } from './calculator';

describe('calculate', () => {
  it('should add numbers', () => {
    expect(calculate(1, 2)).toBe(3);
  });
});
'''
        test_file = tmp_path / "test_example.test.ts"
        test_file.write_text(test_code)

        analyzer = CodeAnalyzer()
        failure = TestFailure(
            test_file=test_file,
            test_name="should add numbers",
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="Expected 3, received 4",
            traceback="",
            framework=TestFramework.JEST
        )

        analysis = analyzer.analyze_typescript_test(test_file, failure)

        assert 'imports' in analysis
        assert 'test_blocks' in analysis
        assert 'calculate' in analysis['imports']
        assert 'should add numbers' in analysis['test_blocks']


class TestTestFixer:
    """Test the TestFixer class."""

    def test_fix_python_import(self, tmp_path):
        """Test fixing Python import."""
        test_code = '''import pytest

def test_example():
    assert True
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        fixer = TestFixer()
        success = fixer.fix_python_import(test_file, "datetime")

        assert success

        # Verify import was added
        content = test_file.read_text()
        assert "import datetime" in content

    def test_update_python_assertion(self, tmp_path):
        """Test updating Python assertion."""
        test_code = '''def test_example():
    result = 5
    assert result == 6
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        fixer = TestFixer()
        success = fixer.update_python_assertion(test_file, 3, "6", "5")

        assert success

        # Verify assertion was updated
        content = test_file.read_text()
        assert "assert result == 5" in content

    def test_fix_typescript_import(self, tmp_path):
        """Test fixing TypeScript import."""
        test_code = '''describe('test', () => {
  it('works', () => {
    expect(true).toBe(true);
  });
});
'''
        test_file = tmp_path / "test_example.test.ts"
        test_file.write_text(test_code)

        fixer = TestFixer()
        success = fixer.fix_typescript_import(test_file, "Calculator")

        assert success

        # Verify import was added
        content = test_file.read_text()
        assert "import { Calculator }" in content


class TestAutoHealer:
    """Test the AutoHealer class."""

    def test_detect_test_framework_python(self):
        """Test framework detection for Python."""
        healer = AutoHealer()
        framework = healer.detect_test_framework(Path("test_example.py"))
        assert framework == TestFramework.PYTEST

    def test_detect_test_framework_typescript(self):
        """Test framework detection for TypeScript."""
        healer = AutoHealer()
        framework = healer.detect_test_framework(Path("test_example.test.ts"))
        assert framework == TestFramework.JEST

    def test_analyze_failure_import_error(self):
        """Test analyzing import error failure."""
        healer = AutoHealer()
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.IMPORT_ERROR,
            error_message="No module named 'foo'",
            traceback="",
            framework=TestFramework.PYTEST,
            missing_import="foo"
        )

        analysis = healer.analyze_failure(failure)

        assert analysis['suggested_strategy'] == HealingStrategy.FIX_IMPORT
        assert analysis['confidence'] >= 0.9

    def test_analyze_failure_assertion_error(self):
        """Test analyzing assertion error failure."""
        healer = AutoHealer()
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="assert 7 == 6",
            traceback="",
            framework=TestFramework.PYTEST,
            expected_value="6",
            actual_value="7"
        )

        analysis = healer.analyze_failure(failure)

        # Should suggest either UPDATE_EXPECTED or FIX_CODE
        assert analysis['suggested_strategy'] in [
            HealingStrategy.UPDATE_EXPECTED,
            HealingStrategy.FIX_CODE
        ]

    def test_suggest_fix_import_error(self):
        """Test fix suggestion for import error."""
        healer = AutoHealer()
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.IMPORT_ERROR,
            error_message="No module named 'datetime'",
            traceback="",
            framework=TestFramework.PYTEST,
            missing_import="datetime"
        )

        analysis = healer.analyze_failure(failure)
        fix = healer.suggest_fix(analysis)

        assert fix is not None
        assert "datetime" in fix

    def test_suggest_fix_update_expected(self):
        """Test fix suggestion for updating expected value."""
        healer = AutoHealer()
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="assert 7 == 6",
            traceback="",
            framework=TestFramework.PYTEST,
            expected_value="6",
            actual_value="7"
        )

        analysis = healer.analyze_failure(failure)
        fix = healer.suggest_fix(analysis)

        assert fix is not None

    @pytest.mark.asyncio
    async def test_apply_fix_import_error(self, tmp_path):
        """Test applying fix for import error."""
        test_code = '''def test_example():
    assert True
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        healer = AutoHealer()
        failure = TestFailure(
            test_file=test_file,
            test_name="test_example",
            failure_type=FailureType.IMPORT_ERROR,
            error_message="No module named 'os'",
            traceback="",
            framework=TestFramework.PYTEST,
            missing_import="os"
        )

        analysis = healer.analyze_failure(failure)
        success = await healer.apply_fix(analysis)

        assert success
        assert "import os" in test_file.read_text()

    @pytest.mark.asyncio
    async def test_apply_fix_update_expected(self, tmp_path):
        """Test applying fix for updating expected value."""
        test_code = '''def test_example():
    result = 7
    assert result == 6
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        healer = AutoHealer()
        failure = TestFailure(
            test_file=test_file,
            test_name="test_example",
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="assert 7 == 6",
            traceback="",
            framework=TestFramework.PYTEST,
            line_number=3,
            expected_value="6",
            actual_value="7"
        )

        analysis = healer.analyze_failure(failure)
        analysis['suggested_strategy'] = HealingStrategy.UPDATE_EXPECTED
        success = await healer.apply_fix(analysis)

        assert success
        assert "assert result == 7" in test_file.read_text()

    def test_get_healing_report_empty(self):
        """Test getting healing report with no history."""
        healer = AutoHealer()
        report = healer.get_healing_report()

        assert "No healing attempts" in report

    def test_get_healing_report_with_history(self):
        """Test getting healing report with healing history."""
        healer = AutoHealer()

        # Add some mock healing results
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.IMPORT_ERROR,
            error_message="Import error",
            traceback="",
            framework=TestFramework.PYTEST
        )

        result = HealingResult(
            success=True,
            strategy=HealingStrategy.FIX_IMPORT,
            failure=failure,
            applied_fix="Added import datetime",
            verification_passed=True,
            report="Test healed successfully"
        )

        healer.healing_history.append(result)

        report = healer.get_healing_report()

        assert "Total Healing Attempts: 1" in report
        assert "Successful: 1" in report
        assert "test.py" in report

    def test_export_results(self, tmp_path):
        """Test exporting healing results to JSON."""
        healer = AutoHealer()

        # Add mock result
        failure = TestFailure(
            test_file=Path("test.py"),
            test_name="test_example",
            failure_type=FailureType.IMPORT_ERROR,
            error_message="Import error",
            traceback="",
            framework=TestFramework.PYTEST
        )

        result = HealingResult(
            success=True,
            strategy=HealingStrategy.FIX_IMPORT,
            failure=failure,
            applied_fix="Added import",
            verification_passed=True,
            report="Success"
        )

        healer.healing_history.append(result)

        # Export
        output_file = tmp_path / "results.json"
        healer.export_results(output_file)

        assert output_file.exists()

        # Verify content
        import json
        with open(output_file) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]['success'] is True
        assert data[0]['strategy'] == 'fix_import'


class TestTestRunner:
    """Test the TestRunner class."""

    @pytest.mark.asyncio
    async def test_run_pytest_mock(self):
        """Test running pytest (mocked)."""
        runner = TestRunner()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            # Mock the process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Tests passed", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            success, output = await runner.run_pytest(Path("test.py"))

            assert success
            assert "Tests passed" in output

    @pytest.mark.asyncio
    async def test_run_pytest_failure_mock(self):
        """Test running pytest with failure (mocked)."""
        runner = TestRunner()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            # Mock the process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Tests failed", b"")
            )
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            success, output = await runner.run_pytest(Path("test.py"))

            assert not success
            assert "Tests failed" in output

    @pytest.mark.asyncio
    async def test_run_pytest_timeout_mock(self):
        """Test pytest timeout handling (mocked)."""
        runner = TestRunner()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            # Mock the process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_process.kill = Mock()
            mock_exec.return_value = mock_process

            success, output = await runner.run_pytest(Path("test.py"), timeout=1)

            assert not success
            assert "timed out" in output.lower()


class TestIntegration:
    """Integration tests for the complete auto-healing flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_import_fix(self, tmp_path):
        """Test complete flow for fixing an import error."""
        # Create a test file with import error
        test_code = '''def test_example():
    now = datetime.now()  # datetime not imported
    assert now is not None
'''
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_code)

        # Mock the test runner to simulate failure then success
        healer = AutoHealer()

        # First run: failure
        failure_output = "ImportError: name 'datetime' is not defined"

        with patch.object(healer.runner, 'run_pytest') as mock_run:
            # First call fails, second call succeeds
            mock_run.side_effect = [
                (False, f"FAILED {test_file}::test_example\nE       {failure_output}"),
                (True, "1 passed in 0.01s")
            ]

            # This should detect the error, fix it, and verify
            # Note: In reality, it won't work without actual pytest,
            # but we're testing the logic flow
            result = await healer.heal_test_failure(test_file, initial_output=failure_output)

            # Verify healer attempted to work with the failure
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
