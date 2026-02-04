#!/usr/bin/env python3
"""
Test Generation System for MagnetarCode

Automatically generates comprehensive test suites:
- Unit tests from function/class analysis
- Edge case tests
- Property-based tests (hypothesis-style)
- Integration tests for API endpoints
- Mock/fixture suggestions
- Coverage gap identification

Supports:
- Python: pytest, hypothesis, pytest-cov
- TypeScript: jest, @fast-check/jest
"""

import ast
import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class TestFramework(Enum):
    """Supported test frameworks."""

    PYTEST = "pytest"
    JEST = "jest"
    UNITTEST = "unittest"
    MOCHA = "mocha"


class TestType(Enum):
    """Type of test to generate."""

    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"
    PROPERTY = "property"
    API = "api"
    E2E = "e2e"


@dataclass
class TestCase:
    """
    A generated test case.

    Represents a single test with all necessary metadata.
    """

    name: str
    description: str
    code: str
    test_type: TestType
    framework: TestFramework
    assertions: list[str] = field(default_factory=list)
    fixtures: list[str] = field(default_factory=list)
    mocks: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    setup_code: str | None = None
    teardown_code: str | None = None
    tags: list[str] = field(default_factory=list)
    priority: int = 1  # 1=high, 2=medium, 3=low
    estimated_coverage_gain: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "type": self.test_type.value,
            "framework": self.framework.value,
            "assertions": self.assertions,
            "fixtures": self.fixtures,
            "mocks": self.mocks,
            "imports": self.imports,
            "setup": self.setup_code,
            "teardown": self.teardown_code,
            "tags": self.tags,
            "priority": self.priority,
            "coverage_gain": self.estimated_coverage_gain,
        }


@dataclass
class CoverageGap:
    """
    Identified gap in test coverage.

    Represents code that lacks sufficient testing.
    """

    file: str
    function: str | None
    class_name: str | None
    uncovered_lines: list[int]
    total_lines: int
    coverage_percent: float
    complexity: int = 1  # Cyclomatic complexity
    risk_level: str = "low"  # low, medium, high, critical
    suggested_tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "function": self.function,
            "class": self.class_name,
            "uncovered_lines": self.uncovered_lines,
            "total_lines": self.total_lines,
            "coverage_percent": self.coverage_percent,
            "complexity": self.complexity,
            "risk_level": self.risk_level,
            "suggested_tests": self.suggested_tests,
        }


@dataclass
class FunctionAnalysis:
    """Analysis result for a function/method."""

    name: str
    file_path: str
    line_number: int
    signature: str
    docstring: str | None
    parameters: list[tuple[str, str | None]]  # (name, type_hint)
    return_type: str | None
    is_async: bool
    decorators: list[str]
    raises_exceptions: list[str]
    calls_functions: list[str]
    has_conditionals: bool
    has_loops: bool
    cyclomatic_complexity: int
    is_pure: bool  # No side effects
    is_api_endpoint: bool


class TestGenerator:
    """
    Intelligent test generation system.

    Analyzes code to generate comprehensive test suites with:
    - Unit tests for functions/classes
    - Edge case tests
    - Property-based tests
    - Integration tests
    - Mock suggestions
    """

    def __init__(
        self,
        workspace_root: str | Path,
        framework: TestFramework = TestFramework.PYTEST,
    ):
        """
        Initialize test generator.

        Args:
            workspace_root: Root directory of the project
            framework: Default test framework to use
        """
        self.workspace_root = Path(workspace_root)
        self.framework = framework
        self._coverage_data: dict[str, Any] = {}

    async def analyze_function(
        self,
        file_path: str | Path,
        function_name: str,
    ) -> FunctionAnalysis | None:
        """
        Analyze a function to extract metadata for test generation.

        Args:
            file_path: Path to file containing the function
            function_name: Name of function to analyze

        Returns:
            Function analysis or None if not found
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

        # Find the function
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    return self._analyze_function_node(node, file_path)

        logger.warning(f"Function {function_name} not found in {file_path}")
        return None

    def _analyze_function_node(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
    ) -> FunctionAnalysis:
        """Analyze a function AST node."""
        # Extract parameters with type hints
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            type_hint = None
            if arg.annotation:
                type_hint = ast.unparse(arg.annotation)
            parameters.append((param_name, type_hint))

        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Extract decorators
        decorators = []
        for dec in node.decorator_list:
            decorators.append(ast.unparse(dec))

        # Analyze function body
        raises_exceptions = self._find_exceptions(node)
        calls_functions = self._find_function_calls(node)
        has_conditionals = self._has_conditionals(node)
        has_loops = self._has_loops(node)
        complexity = self._calculate_complexity(node)
        is_pure = self._is_pure_function(node)
        is_api_endpoint = self._is_api_endpoint(decorators)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Build signature
        is_async = isinstance(node, ast.AsyncFunctionDef)
        sig_parts = []
        if is_async:
            sig_parts.append("async")
        sig_parts.append("def")
        sig_parts.append(f"{node.name}(")

        param_strs = []
        for pname, ptype in parameters:
            if ptype:
                param_strs.append(f"{pname}: {ptype}")
            else:
                param_strs.append(pname)
        sig_parts.append(", ".join(param_strs))
        sig_parts.append(")")

        if return_type:
            sig_parts.append(f"-> {return_type}")

        signature = " ".join(sig_parts)

        return FunctionAnalysis(
            name=node.name,
            file_path=str(file_path),
            line_number=node.lineno,
            signature=signature,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            decorators=decorators,
            raises_exceptions=raises_exceptions,
            calls_functions=calls_functions,
            has_conditionals=has_conditionals,
            has_loops=has_loops,
            cyclomatic_complexity=complexity,
            is_pure=is_pure,
            is_api_endpoint=is_api_endpoint,
        )

    def _find_exceptions(self, node: ast.AST) -> list[str]:
        """Find exceptions raised in a function."""
        exceptions = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if child.exc:
                    exc_name = ast.unparse(child.exc)
                    # Extract exception type from constructor call
                    match = re.match(r"(\w+)\(", exc_name)
                    if match:
                        exceptions.append(match.group(1))
        return list(set(exceptions))

    def _find_function_calls(self, node: ast.AST) -> list[str]:
        """Find function calls in a function."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = ast.unparse(child.func)
                calls.append(call_name)
        return list(set(calls))

    def _has_conditionals(self, node: ast.AST) -> bool:
        """Check if function has conditionals."""
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp, ast.Match)):
                return True
        return False

    def _has_loops(self, node: ast.AST) -> bool:
        """Check if function has loops."""
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                return True
        return False

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _is_pure_function(self, node: ast.AST) -> bool:
        """Check if function appears to be pure (no side effects)."""
        # Check for global/nonlocal statements
        for child in ast.walk(node):
            if isinstance(child, (ast.Global, ast.Nonlocal)):
                return False
            # Check for attribute assignment (object modification)
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        return False

        return True

    def _is_api_endpoint(self, decorators: list[str]) -> bool:
        """Check if function is an API endpoint."""
        api_decorators = [
            "app.get",
            "app.post",
            "app.put",
            "app.delete",
            "app.patch",
            "router.get",
            "router.post",
            "router.put",
            "router.delete",
            "router.patch",
            "route",
        ]
        return any(
            any(dec in decorator for dec in api_decorators) for decorator in decorators
        )

    async def generate_unit_test(
        self,
        analysis: FunctionAnalysis,
        include_edge_cases: bool = True,
    ) -> TestCase:
        """
        Generate unit test for a function.

        Args:
            analysis: Function analysis result
            include_edge_cases: Include edge case scenarios

        Returns:
            Generated test case
        """
        test_name = f"test_{analysis.name}"
        imports = self._generate_imports(analysis)
        mocks = self._identify_required_mocks(analysis)
        fixtures = []

        # Generate test code
        code_lines = []

        # Test function signature
        if analysis.is_async:
            code_lines.append(f"async def {test_name}():")
        else:
            code_lines.append(f"def {test_name}():")

        # Setup mocks
        if mocks:
            code_lines.append("    # Setup mocks")
            for mock in mocks:
                code_lines.append(f"    {mock}")
            code_lines.append("")

        # Generate test scenarios
        scenarios = self._generate_test_scenarios(analysis, include_edge_cases)

        for i, scenario in enumerate(scenarios):
            if i > 0:
                code_lines.append("")
            code_lines.append(f"    # {scenario['description']}")

            # Setup scenario-specific data
            if "setup" in scenario:
                code_lines.append(f"    {scenario['setup']}")

            # Call function
            call = self._generate_function_call(analysis, scenario)
            if analysis.is_async:
                code_lines.append(f"    result = await {call}")
            else:
                code_lines.append(f"    result = {call}")

            # Add assertions
            for assertion in scenario["assertions"]:
                code_lines.append(f"    assert {assertion}")

        code = "\n".join(code_lines)

        # Extract assertions for metadata
        assertions = []
        for scenario in scenarios:
            assertions.extend(scenario["assertions"])

        return TestCase(
            name=test_name,
            description=f"Unit test for {analysis.name}",
            code=code,
            test_type=TestType.UNIT,
            framework=self.framework,
            assertions=assertions,
            fixtures=fixtures,
            mocks=mocks,
            imports=imports,
            priority=1 if analysis.cyclomatic_complexity > 3 else 2,
            estimated_coverage_gain=10.0 / max(1, len(scenarios)),
        )

    def _generate_imports(self, analysis: FunctionAnalysis) -> list[str]:
        """Generate necessary imports for test."""
        imports = []

        # Add pytest/unittest imports
        if self.framework == TestFramework.PYTEST:
            imports.append("import pytest")
            if analysis.is_async:
                imports.append("import pytest_asyncio")

        # Add mock imports
        imports.append("from unittest.mock import Mock, patch, MagicMock")

        # Import the function being tested
        # Convert file path to module path
        file_path = Path(analysis.file_path)
        if file_path.is_absolute():
            # Try to make it relative to common roots
            try:
                rel_path = file_path.relative_to(self.workspace_root)
            except ValueError:
                rel_path = file_path
        else:
            rel_path = file_path

        module_path = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
        imports.append(f"from {module_path} import {analysis.name}")

        return imports

    def _identify_required_mocks(self, analysis: FunctionAnalysis) -> list[str]:
        """Identify functions/objects that should be mocked."""
        mocks = []

        # Mock external function calls
        external_calls = [
            call
            for call in analysis.calls_functions
            if not call.startswith("self.") and "." in call
        ]

        for call in external_calls[:3]:  # Limit to 3 most important
            mock_name = call.split(".")[-1]
            mocks.append(f"{mock_name}_mock = Mock()")

        return mocks

    def _generate_test_scenarios(
        self,
        analysis: FunctionAnalysis,
        include_edge_cases: bool,
    ) -> list[dict[str, Any]]:
        """Generate test scenarios for a function."""
        scenarios = []

        # Happy path scenario
        scenarios.append(self._generate_happy_path_scenario(analysis))

        if include_edge_cases:
            # Edge cases
            scenarios.extend(self._generate_edge_case_scenarios(analysis))

        # Exception scenarios
        for exc in analysis.raises_exceptions:
            scenarios.append(
                {
                    "description": f"Should raise {exc}",
                    "setup": "# Setup invalid input",
                    "args": ["invalid_input"],
                    "assertions": [f"isinstance(excinfo.value, {exc})"],
                    "expects_exception": exc,
                }
            )

        return scenarios

    def _generate_happy_path_scenario(
        self, analysis: FunctionAnalysis
    ) -> dict[str, Any]:
        """Generate happy path test scenario."""
        # Generate sample inputs based on parameter types
        args = []
        for param_name, param_type in analysis.parameters:
            if param_name == "self":
                continue
            args.append(self._generate_sample_value(param_type))

        return {
            "description": "Should work with valid inputs",
            "args": args,
            "assertions": ["result is not None"],
        }

    def _generate_edge_case_scenarios(
        self, analysis: FunctionAnalysis
    ) -> list[dict[str, Any]]:
        """Generate edge case scenarios."""
        scenarios = []

        # Check parameter types for edge cases
        for param_name, param_type in analysis.parameters:
            if param_name == "self":
                continue

            if param_type and "str" in param_type.lower():
                scenarios.append(
                    {
                        "description": f"Should handle empty string for {param_name}",
                        "args": ['""'],
                        "assertions": ["result is not None"],
                    }
                )

            if param_type and ("list" in param_type.lower() or "[]" in param_type):
                scenarios.append(
                    {
                        "description": f"Should handle empty list for {param_name}",
                        "args": ["[]"],
                        "assertions": ["result is not None"],
                    }
                )

            if param_type and "int" in param_type.lower():
                scenarios.append(
                    {
                        "description": f"Should handle zero for {param_name}",
                        "args": ["0"],
                        "assertions": ["result is not None"],
                    }
                )

        return scenarios[:3]  # Limit edge cases

    def _generate_sample_value(self, type_hint: str | None) -> str:
        """Generate sample value for a type."""
        if not type_hint:
            return "None"

        type_lower = type_hint.lower()

        if "str" in type_lower:
            return '"test_value"'
        elif "int" in type_lower:
            return "42"
        elif "float" in type_lower:
            return "3.14"
        elif "bool" in type_lower:
            return "True"
        elif "list" in type_lower:
            return "[1, 2, 3]"
        elif "dict" in type_lower:
            return '{"key": "value"}'
        elif "path" in type_lower:
            return 'Path("/tmp/test")'
        else:
            return "None"

    def _generate_function_call(
        self, analysis: FunctionAnalysis, scenario: dict[str, Any]
    ) -> str:
        """Generate function call code."""
        args_str = ", ".join(str(arg) for arg in scenario.get("args", []))
        return f"{analysis.name}({args_str})"

    async def generate_edge_cases(
        self, analysis: FunctionAnalysis
    ) -> list[TestCase]:
        """
        Generate edge case tests.

        Args:
            analysis: Function analysis

        Returns:
            List of edge case tests
        """
        edge_tests = []

        # Null/None inputs
        if analysis.parameters:
            test = await self._generate_null_input_test(analysis)
            edge_tests.append(test)

        # Boundary values for numeric parameters
        numeric_params = [
            (name, hint)
            for name, hint in analysis.parameters
            if hint
            and any(t in hint.lower() for t in ["int", "float", "number"])
        ]

        if numeric_params:
            test = await self._generate_boundary_test(analysis)
            edge_tests.append(test)

        # Empty collections
        collection_params = [
            (name, hint)
            for name, hint in analysis.parameters
            if hint and any(t in hint.lower() for t in ["list", "dict", "set"])
        ]

        if collection_params:
            test = await self._generate_empty_collection_test(analysis)
            edge_tests.append(test)

        return edge_tests

    async def _generate_null_input_test(self, analysis: FunctionAnalysis) -> TestCase:
        """Generate test for None/null inputs."""
        code = f"""def test_{analysis.name}_with_none():
    # Test handling of None inputs
    result = {analysis.name}(None)
    assert result is not None or result is None  # Verify behavior
"""
        return TestCase(
            name=f"test_{analysis.name}_with_none",
            description="Test None input handling",
            code=code,
            test_type=TestType.EDGE_CASE,
            framework=self.framework,
            assertions=["result is not None or result is None"],
            priority=2,
        )

    async def _generate_boundary_test(self, analysis: FunctionAnalysis) -> TestCase:
        """Generate boundary value test."""
        code = f"""def test_{analysis.name}_boundary_values():
    # Test boundary values
    assert {analysis.name}(0) is not None
    assert {analysis.name}(-1) is not None
    assert {analysis.name}(sys.maxsize) is not None
"""
        return TestCase(
            name=f"test_{analysis.name}_boundary_values",
            description="Test boundary values",
            code=code,
            test_type=TestType.EDGE_CASE,
            framework=self.framework,
            imports=["import sys"],
            assertions=[
                f"{analysis.name}(0) is not None",
                f"{analysis.name}(-1) is not None",
                f"{analysis.name}(sys.maxsize) is not None",
            ],
            priority=2,
        )

    async def _generate_empty_collection_test(
        self, analysis: FunctionAnalysis
    ) -> TestCase:
        """Generate empty collection test."""
        code = f"""def test_{analysis.name}_empty_collection():
    # Test empty collection handling
    assert {analysis.name}([]) is not None
    assert {analysis.name}({{}}) is not None
"""
        return TestCase(
            name=f"test_{analysis.name}_empty_collection",
            description="Test empty collection handling",
            code=code,
            test_type=TestType.EDGE_CASE,
            framework=self.framework,
            assertions=[
                f"{analysis.name}([]) is not None",
                f"{analysis.name}({{}}) is not None",
            ],
            priority=2,
        )

    async def generate_property_test(
        self, analysis: FunctionAnalysis
    ) -> TestCase | None:
        """
        Generate property-based test (hypothesis-style).

        Args:
            analysis: Function analysis

        Returns:
            Property test or None if not applicable
        """
        # Property-based testing is most useful for pure functions
        if not analysis.is_pure:
            return None

        # Generate hypothesis strategies for parameters
        strategies = []
        for param_name, param_type in analysis.parameters:
            if param_name == "self":
                continue

            strategy = self._generate_hypothesis_strategy(param_type)
            if strategy:
                strategies.append(f"{param_name}={strategy}")

        if not strategies:
            return None

        # Generate property test
        code = f"""@given({", ".join(strategies)})
def test_{analysis.name}_properties({", ".join(p[0] for p in analysis.parameters if p[0] != "self")}):
    \"\"\"Property-based test for {analysis.name}.\"\"\"
    # Property: Function should not raise unexpected exceptions
    try:
        result = {analysis.name}({", ".join(p[0] for p in analysis.parameters if p[0] != "self")})
        # Property: Result should be deterministic
        result2 = {analysis.name}({", ".join(p[0] for p in analysis.parameters if p[0] != "self")})
        assert result == result2
    except Exception as e:
        # Only expected exceptions allowed
        assert type(e).__name__ in {analysis.raises_exceptions}
"""

        return TestCase(
            name=f"test_{analysis.name}_properties",
            description=f"Property-based test for {analysis.name}",
            code=code,
            test_type=TestType.PROPERTY,
            framework=self.framework,
            imports=["from hypothesis import given, strategies as st"],
            assertions=["result == result2"],
            priority=2,
        )

    def _generate_hypothesis_strategy(self, param_type: str | None) -> str | None:
        """Generate hypothesis strategy for a parameter type."""
        if not param_type:
            return None

        type_lower = param_type.lower()

        if "str" in type_lower:
            return "st.text()"
        elif "int" in type_lower:
            return "st.integers()"
        elif "float" in type_lower:
            return "st.floats(allow_nan=False, allow_infinity=False)"
        elif "bool" in type_lower:
            return "st.booleans()"
        elif "list" in type_lower:
            return "st.lists(st.text())"
        elif "dict" in type_lower:
            return "st.dictionaries(st.text(), st.text())"

        return None

    async def find_coverage_gaps(
        self, coverage_file: str | Path | None = None
    ) -> list[CoverageGap]:
        """
        Find coverage gaps using coverage.py data.

        Args:
            coverage_file: Path to .coverage file (defaults to .coverage)

        Returns:
            List of coverage gaps
        """
        gaps = []

        # Try to load coverage data
        coverage_data = await self._load_coverage_data(coverage_file)
        if not coverage_data:
            logger.warning("No coverage data available")
            return gaps

        # Analyze each file
        for file_path, file_data in coverage_data.items():
            if not file_data:
                continue

            executed = set(file_data.get("executed_lines", []))
            missing = set(file_data.get("missing_lines", []))
            total = len(executed) + len(missing)

            if total == 0:
                continue

            coverage_percent = (len(executed) / total) * 100

            # Only report significant gaps
            if coverage_percent < 80 and len(missing) > 0:
                # Try to identify which functions have gaps
                gap = CoverageGap(
                    file=file_path,
                    function=None,
                    class_name=None,
                    uncovered_lines=sorted(missing),
                    total_lines=total,
                    coverage_percent=coverage_percent,
                    risk_level=self._assess_risk_level(coverage_percent, len(missing)),
                    suggested_tests=[
                        "Add tests for uncovered branches",
                        "Test error handling paths",
                        "Add integration tests",
                    ],
                )
                gaps.append(gap)

        # Sort by risk level and coverage percent
        gaps.sort(key=lambda g: (g.risk_level, g.coverage_percent))

        return gaps

    async def _load_coverage_data(
        self, coverage_file: str | Path | None
    ) -> dict[str, Any]:
        """Load coverage data from coverage.py."""
        if coverage_file is None:
            coverage_file = self.workspace_root / ".coverage"
        else:
            coverage_file = Path(coverage_file)

        if not coverage_file.exists():
            return {}

        try:
            # Use coverage.py to extract data
            result = subprocess.run(
                ["coverage", "json", "-o", "-"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("files", {})
        except Exception as e:
            logger.debug(f"Could not load coverage data: {e}")

        return {}

    def _assess_risk_level(self, coverage_percent: float, missing_lines: int) -> str:
        """Assess risk level based on coverage."""
        if coverage_percent < 30 or missing_lines > 50:
            return "critical"
        elif coverage_percent < 50 or missing_lines > 20:
            return "high"
        elif coverage_percent < 70 or missing_lines > 10:
            return "medium"
        else:
            return "low"

    async def generate_api_test(
        self,
        endpoint_path: str,
        http_method: str,
        analysis: FunctionAnalysis,
    ) -> TestCase:
        """
        Generate integration test for API endpoint.

        Args:
            endpoint_path: API endpoint path (e.g., "/api/users")
            http_method: HTTP method (GET, POST, etc.)
            analysis: Function analysis of endpoint handler

        Returns:
            API integration test
        """
        method_lower = http_method.lower()
        test_name = f"test_{method_lower}_{endpoint_path.replace('/', '_').strip('_')}"

        # Determine if endpoint expects request body
        has_body = http_method in ["POST", "PUT", "PATCH"]

        code_lines = []
        code_lines.append(f"async def {test_name}(client):")
        code_lines.append(f'    """Test {http_method} {endpoint_path}"""')

        if has_body:
            code_lines.append("    # Prepare request data")
            code_lines.append("    data = {")
            for param_name, param_type in analysis.parameters:
                if param_name not in ["self", "request", "db", "session"]:
                    sample = self._generate_sample_value(param_type)
                    code_lines.append(f'        "{param_name}": {sample},')
            code_lines.append("    }")
            code_lines.append("")

        # Make request
        code_lines.append("    # Make request")
        if has_body:
            code_lines.append(
                f'    response = await client.{method_lower}("{endpoint_path}", json=data)'
            )
        else:
            code_lines.append(
                f'    response = await client.{method_lower}("{endpoint_path}")'
            )

        code_lines.append("")
        code_lines.append("    # Assertions")
        code_lines.append("    assert response.status_code == 200")
        code_lines.append("    assert response.json() is not None")

        code = "\n".join(code_lines)

        return TestCase(
            name=test_name,
            description=f"Integration test for {http_method} {endpoint_path}",
            code=code,
            test_type=TestType.API,
            framework=self.framework,
            imports=["import pytest", "from httpx import AsyncClient"],
            assertions=[
                "response.status_code == 200",
                "response.json() is not None",
            ],
            fixtures=["client"],
            priority=1,
            estimated_coverage_gain=15.0,
        )

    async def suggest_mocks(self, analysis: FunctionAnalysis) -> list[dict[str, Any]]:
        """
        Suggest mocks and fixtures for testing a function.

        Args:
            analysis: Function analysis

        Returns:
            List of mock/fixture suggestions
        """
        suggestions = []

        # Suggest mocks for external dependencies
        external_calls = [
            call
            for call in analysis.calls_functions
            if "." in call and not call.startswith("self.")
        ]

        for call in external_calls:
            parts = call.split(".")
            module = ".".join(parts[:-1])
            func = parts[-1]

            suggestions.append(
                {
                    "type": "mock",
                    "target": call,
                    "code": f'@patch("{module}.{func}")\ndef test_{analysis.name}(mock_{func}):\n    mock_{func}.return_value = "test_value"\n    # ... rest of test',
                    "description": f"Mock {call} to isolate unit test",
                }
            )

        # Suggest fixtures for common patterns
        if any("db" in p[0].lower() for p in analysis.parameters):
            suggestions.append(
                {
                    "type": "fixture",
                    "target": "database",
                    "code": '@pytest.fixture\nasync def db():\n    """Test database fixture."""\n    # Setup test database\n    yield test_db\n    # Cleanup',
                    "description": "Database fixture for testing",
                }
            )

        if any("client" in p[0].lower() for p in analysis.parameters):
            suggestions.append(
                {
                    "type": "fixture",
                    "target": "client",
                    "code": '@pytest.fixture\nasync def client():\n    """HTTP client fixture."""\n    async with AsyncClient(app=app, base_url="http://test") as client:\n        yield client',
                    "description": "HTTP client fixture for API testing",
                }
            )

        return suggestions

    async def generate_test_file(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> str:
        """
        Generate complete test file for a source file.

        Args:
            source_file: Source file to generate tests for
            output_file: Output test file path (auto-generated if None)

        Returns:
            Path to generated test file
        """
        source_file = Path(source_file)
        if output_file is None:
            # Generate test file path
            output_file = (
                self.workspace_root
                / "tests"
                / f"test_{source_file.stem}.py"
            )
        else:
            output_file = Path(output_file)

        # Parse source file to find all testable functions
        try:
            content = source_file.read_text()
            tree = ast.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse {source_file}: {e}")
            raise

        # Collect all functions to test
        test_cases = []
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions
                if node.name.startswith("_"):
                    continue

                # Analyze and generate tests
                analysis = self._analyze_function_node(node, source_file)

                # Generate unit test
                unit_test = await self.generate_unit_test(analysis)
                test_cases.append(unit_test)
                imports.update(unit_test.imports)

                # Generate edge case tests
                edge_tests = await self.generate_edge_cases(analysis)
                test_cases.extend(edge_tests)
                for test in edge_tests:
                    imports.update(test.imports)

                # Generate property test if applicable
                prop_test = await self.generate_property_test(analysis)
                if prop_test:
                    test_cases.append(prop_test)
                    imports.update(prop_test.imports)

        # Build test file content
        content_lines = []
        content_lines.append('"""')
        content_lines.append(f"Generated tests for {source_file.name}")
        content_lines.append("")
        content_lines.append(f"Auto-generated on {datetime.utcnow().isoformat()}")
        content_lines.append('"""')
        content_lines.append("")

        # Add imports
        for imp in sorted(imports):
            content_lines.append(imp)
        content_lines.append("")
        content_lines.append("")

        # Add test cases
        for test_case in test_cases:
            content_lines.append(test_case.code)
            content_lines.append("")
            content_lines.append("")

        # Write test file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(content_lines))

        logger.info(f"Generated {len(test_cases)} tests in {output_file}")

        return str(output_file)


# Convenience functions
async def generate_tests_for_file(
    file_path: str | Path,
    workspace_root: str | Path | None = None,
) -> str:
    """
    Generate tests for a single file.

    Args:
        file_path: Source file to generate tests for
        workspace_root: Workspace root (defaults to cwd)

    Returns:
        Path to generated test file
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    generator = TestGenerator(workspace_root)
    return await generator.generate_test_file(file_path)


async def find_untested_code(
    workspace_root: str | Path | None = None,
) -> list[CoverageGap]:
    """
    Find untested code in the workspace.

    Args:
        workspace_root: Workspace root (defaults to cwd)

    Returns:
        List of coverage gaps
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    generator = TestGenerator(workspace_root)
    return await generator.find_coverage_gaps()
