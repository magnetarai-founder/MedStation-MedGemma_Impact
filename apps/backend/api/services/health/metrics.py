"""
Code Health Metrics System

Provides comprehensive code health analysis including:
- Cyclomatic complexity analysis
- Maintainability index calculation
- Technical debt estimation
- Code duplication detection
- Test coverage tracking
- Documentation coverage analysis
- Dependency health monitoring
- Historical trend analysis
"""

import ast
import hashlib
import re
import sqlite3
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend direction over time"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"


@dataclass
class HealthThresholds:
    """Configurable thresholds for health metrics"""

    # Complexity thresholds
    complexity_good: int = 10
    complexity_warning: int = 15
    complexity_critical: int = 25

    # Maintainability thresholds (0-100 scale)
    maintainability_good: float = 70.0
    maintainability_warning: float = 50.0
    maintainability_critical: float = 25.0

    # Duplication thresholds (percentage)
    duplication_good: float = 3.0
    duplication_warning: float = 5.0
    duplication_critical: float = 10.0

    # Coverage thresholds (percentage)
    coverage_good: float = 80.0
    coverage_warning: float = 60.0
    coverage_critical: float = 40.0

    # Documentation thresholds (percentage)
    docs_good: float = 75.0
    docs_warning: float = 50.0
    docs_critical: float = 25.0

    # Lines of code per function
    loc_per_function_good: int = 50
    loc_per_function_warning: int = 100
    loc_per_function_critical: int = 200


@dataclass
class CodeMetrics:
    """Metrics for a single function or method"""

    name: str
    file_path: str
    line_start: int
    line_end: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int
    num_parameters: int
    num_returns: int
    has_docstring: bool
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0

    @property
    def status(self) -> HealthStatus:
        """Determine health status based on complexity"""
        if self.cyclomatic_complexity >= 25:
            return HealthStatus.CRITICAL
        elif self.cyclomatic_complexity >= 15:
            return HealthStatus.WARNING
        return HealthStatus.GOOD


@dataclass
class DuplicateBlock:
    """Represents a block of duplicated code"""

    hash_value: str
    lines: List[str]
    occurrences: List[Tuple[str, int]]  # (file_path, line_number)

    @property
    def duplication_count(self) -> int:
        return len(self.occurrences)

    @property
    def estimated_hours(self) -> float:
        """Estimate hours to refactor duplicates"""
        # Base: 0.5 hours per duplicate location, plus complexity factor
        complexity_factor = min(len(self.lines) / 20, 2.0)
        return (self.duplication_count - 1) * 0.5 * complexity_factor


@dataclass
class TechDebtItem:
    """Single technical debt item"""

    category: str  # 'complexity', 'duplication', 'documentation', 'testing'
    severity: HealthStatus
    file_path: str
    line_number: int
    description: str
    estimated_hours: float
    current_value: float
    threshold_value: float

    def to_dict(self) -> dict:
        return {
            'category': self.category,
            'severity': self.severity.value,
            'file_path': str(self.file_path),
            'line_number': self.line_number,
            'description': self.description,
            'estimated_hours': self.estimated_hours,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
        }


@dataclass
class DependencyIssue:
    """Dependency health issue"""

    package_name: str
    current_version: str
    latest_version: Optional[str] = None
    is_outdated: bool = False
    has_vulnerabilities: bool = False
    vulnerability_count: int = 0
    severity: HealthStatus = HealthStatus.GOOD


@dataclass
class FileHealth:
    """Health metrics for a single file"""

    file_path: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: List[CodeMetrics]
    avg_complexity: float
    max_complexity: int
    maintainability_index: float
    has_tests: bool
    test_coverage: float
    documentation_coverage: float
    duplicate_lines: int
    status: HealthStatus

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def comment_ratio(self) -> float:
        """Ratio of comment lines to code lines"""
        return self.comment_lines / max(self.code_lines, 1)


@dataclass
class ProjectHealth:
    """Overall project health metrics"""

    timestamp: datetime
    project_root: str
    total_files: int
    total_lines: int
    total_code_lines: int
    file_health: List[FileHealth]

    # Aggregated metrics
    avg_complexity: float
    avg_maintainability: float
    total_functions: int
    high_complexity_functions: int

    # Coverage metrics
    test_coverage: float
    documentation_coverage: float

    # Duplication metrics
    duplicate_blocks: List[DuplicateBlock]
    duplication_percentage: float

    # Technical debt
    tech_debt_items: List[TechDebtItem] = field(default_factory=list)
    total_tech_debt_hours: float = 0.0

    # Dependency health
    dependency_issues: List[DependencyIssue] = field(default_factory=list)

    # Trends
    complexity_trend: TrendDirection = TrendDirection.UNKNOWN
    maintainability_trend: TrendDirection = TrendDirection.UNKNOWN
    coverage_trend: TrendDirection = TrendDirection.UNKNOWN
    tech_debt_trend: TrendDirection = TrendDirection.UNKNOWN

    # Overall status
    overall_status: HealthStatus = HealthStatus.GOOD

    def get_status_summary(self) -> Dict[str, int]:
        """Count files by health status"""
        summary = {status.value: 0 for status in HealthStatus}
        for file in self.file_health:
            summary[file.status.value] += 1
        return summary


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic and cognitive complexity"""

    def __init__(self):
        self.complexity = 1  # Base complexity
        self.cognitive = 0
        self.nesting_depth = 0
        self.operators = defaultdict(int)
        self.operands = defaultdict(int)

    def visit_If(self, node):
        self.complexity += 1
        self.cognitive += 1 + self.nesting_depth
        self.nesting_depth += 1
        self.generic_visit(node)
        self.nesting_depth -= 1

    def visit_For(self, node):
        self.complexity += 1
        self.cognitive += 1 + self.nesting_depth
        self.nesting_depth += 1
        self.generic_visit(node)
        self.nesting_depth -= 1

    def visit_While(self, node):
        self.complexity += 1
        self.cognitive += 1 + self.nesting_depth
        self.nesting_depth += 1
        self.generic_visit(node)
        self.nesting_depth -= 1

    def visit_And(self, node):
        self.complexity += 1
        self.cognitive += 1
        self.generic_visit(node)

    def visit_Or(self, node):
        self.complexity += 1
        self.cognitive += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.cognitive += 1 + self.nesting_depth
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.nesting_depth += 1
        self.generic_visit(node)
        self.nesting_depth -= 1

    def visit_Try(self, node):
        # Try itself doesn't add complexity, but handlers do
        self.generic_visit(node)

    def visit_Return(self, node):
        self.generic_visit(node)

    def visit_BinOp(self, node):
        op_name = node.op.__class__.__name__
        self.operators[op_name] += 1
        self.generic_visit(node)

    def visit_Name(self, node):
        self.operands[node.id] += 1
        self.generic_visit(node)


class HealthDashboard:
    """Main code health dashboard service"""

    def __init__(
        self,
        project_root: str,
        db_path: Optional[str] = None,
        thresholds: Optional[HealthThresholds] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        self.project_root = Path(project_root)
        self.thresholds = thresholds or HealthThresholds()
        self.exclude_patterns = exclude_patterns or [
            '*/venv/*', '*/.venv/*', '*/node_modules/*',
            '*/__pycache__/*', '*/build/*', '*/dist/*',
            '*/migrations/*', '*/.git/*'
        ]

        # Database for historical tracking
        if db_path is None:
            db_path = self.project_root / '.health_metrics.db'
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for historical tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Project snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                project_root TEXT NOT NULL,
                total_files INTEGER,
                total_lines INTEGER,
                avg_complexity REAL,
                avg_maintainability REAL,
                test_coverage REAL,
                documentation_coverage REAL,
                duplication_percentage REAL,
                total_tech_debt_hours REAL,
                overall_status TEXT,
                metrics_json TEXT
            )
        ''')

        # File metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                file_path TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_lines INTEGER,
                code_lines INTEGER,
                avg_complexity REAL,
                max_complexity INTEGER,
                maintainability_index REAL,
                test_coverage REAL,
                status TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES health_snapshots(id)
            )
        ''')

        # Function metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS function_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_metric_id INTEGER,
                function_name TEXT NOT NULL,
                cyclomatic_complexity INTEGER,
                cognitive_complexity INTEGER,
                lines_of_code INTEGER,
                num_parameters INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (file_metric_id) REFERENCES file_metrics(id)
            )
        ''')

        # Technical debt table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tech_debt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                description TEXT,
                estimated_hours REAL,
                timestamp TEXT NOT NULL,
                resolved BOOLEAN DEFAULT 0,
                FOREIGN KEY (snapshot_id) REFERENCES health_snapshots(id)
            )
        ''')

        # Create indices for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
            ON health_snapshots(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_metrics_path
            ON file_metrics(file_path, timestamp)
        ''')

        conn.commit()
        conn.close()

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from analysis"""
        # Extract excluded directory names from patterns
        # Patterns are like '*/venv/*', '*/.venv/*', etc.
        excluded_dirs = set()
        for pattern in self.exclude_patterns:
            # Strip wildcards and slashes to get the directory name
            parts = pattern.replace('*', '').strip('/').split('/')
            for part in parts:
                if part:
                    excluded_dirs.add(part)

        # Check if any path component is in the excluded set
        return any(part in excluded_dirs for part in file_path.parts)

    def calculate_complexity(self, file_path: Path) -> List[CodeMetrics]:
        """Calculate cyclomatic complexity for all functions in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            metrics = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    analyzer = ComplexityAnalyzer()
                    analyzer.visit(node)

                    # Count lines
                    lines = content.split('\n')[node.lineno - 1:node.end_lineno]
                    loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

                    # Calculate Halstead metrics
                    n1 = len(analyzer.operators)  # Unique operators
                    n2 = len(analyzer.operands)   # Unique operands
                    N1 = sum(analyzer.operators.values())  # Total operators
                    N2 = sum(analyzer.operands.values())   # Total operands

                    halstead_volume = 0.0
                    halstead_difficulty = 0.0
                    if n1 > 0 and n2 > 0:
                        vocabulary = n1 + n2
                        length = N1 + N2
                        if vocabulary > 0 and length > 0:
                            import math
                            halstead_volume = length * math.log2(vocabulary)
                            halstead_difficulty = (n1 / 2) * (N2 / max(n2, 1))

                    metrics.append(CodeMetrics(
                        name=node.name,
                        file_path=str(file_path),
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        cyclomatic_complexity=analyzer.complexity,
                        cognitive_complexity=analyzer.cognitive,
                        lines_of_code=loc,
                        num_parameters=len(node.args.args),
                        num_returns=sum(1 for n in ast.walk(node) if isinstance(n, ast.Return)),
                        has_docstring=ast.get_docstring(node) is not None,
                        halstead_volume=halstead_volume,
                        halstead_difficulty=halstead_difficulty,
                    ))

            return metrics

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            return []

    def calculate_maintainability(self, file_path: Path, metrics: List[CodeMetrics]) -> float:
        """
        Calculate maintainability index for a file.

        MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC) + 50 * sin(sqrt(2.4 * CM))
        Where:
        - HV = Halstead Volume
        - CC = Cyclomatic Complexity
        - LOC = Lines of Code
        - CM = Comment ratio (0-100)

        Simplified version for Python:
        MI = max(0, (171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)) * 100 / 171)
        """
        if not metrics:
            return 100.0

        try:
            import math

            # Aggregate metrics
            total_volume = sum(m.halstead_volume for m in metrics) or 1.0
            avg_complexity = sum(m.cyclomatic_complexity for m in metrics) / len(metrics)
            total_loc = sum(m.lines_of_code for m in metrics)

            # Calculate comment ratio
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            comment_ratio = (comment_lines / max(code_lines, 1)) * 100

            # Calculate MI (normalized to 0-100 scale)
            if total_loc > 0 and total_volume > 0:
                mi = (
                    171
                    - 5.2 * math.log(total_volume)
                    - 0.23 * avg_complexity
                    - 16.2 * math.log(total_loc)
                    + 50 * math.sin(math.sqrt(2.4 * comment_ratio / 100))
                )
                # Normalize to 0-100 scale
                mi = max(0, min(100, (mi / 171) * 100))
            else:
                mi = 100.0

            return round(mi, 2)

        except Exception as e:
            logger.warning(f"Failed to calculate maintainability for {file_path}: {e}")
            return 50.0

    def estimate_tech_debt(
        self,
        file_health: FileHealth,
        thresholds: HealthThresholds
    ) -> List[TechDebtItem]:
        """Estimate technical debt items for a file"""
        debt_items = []

        # High complexity functions
        for func in file_health.functions:
            if func.cyclomatic_complexity > thresholds.complexity_warning:
                severity = (
                    HealthStatus.CRITICAL
                    if func.cyclomatic_complexity > thresholds.complexity_critical
                    else HealthStatus.WARNING
                )
                # Estimate: 0.5 hours per complexity point above threshold
                excess = func.cyclomatic_complexity - thresholds.complexity_warning
                hours = excess * 0.5

                debt_items.append(TechDebtItem(
                    category='complexity',
                    severity=severity,
                    file_path=file_health.file_path,
                    line_number=func.line_start,
                    description=f"High complexity in function '{func.name}' (CC: {func.cyclomatic_complexity})",
                    estimated_hours=hours,
                    current_value=func.cyclomatic_complexity,
                    threshold_value=thresholds.complexity_warning,
                ))

        # Missing documentation
        undocumented = [f for f in file_health.functions if not f.has_docstring]
        if undocumented and file_health.documentation_coverage < thresholds.docs_warning:
            severity = (
                HealthStatus.CRITICAL
                if file_health.documentation_coverage < thresholds.docs_critical
                else HealthStatus.WARNING
            )
            hours = len(undocumented) * 0.25  # 15 minutes per docstring

            debt_items.append(TechDebtItem(
                category='documentation',
                severity=severity,
                file_path=file_health.file_path,
                line_number=1,
                description=f"Missing documentation for {len(undocumented)} functions",
                estimated_hours=hours,
                current_value=file_health.documentation_coverage,
                threshold_value=thresholds.docs_warning,
            ))

        # Low test coverage
        if not file_health.has_tests or file_health.test_coverage < thresholds.coverage_warning:
            severity = (
                HealthStatus.CRITICAL
                if file_health.test_coverage < thresholds.coverage_critical
                else HealthStatus.WARNING
            )
            # Estimate: 1 hour per 100 lines of untested code
            untested_lines = file_health.code_lines * (1 - file_health.test_coverage / 100)
            hours = untested_lines / 100

            debt_items.append(TechDebtItem(
                category='testing',
                severity=severity,
                file_path=file_health.file_path,
                line_number=1,
                description=f"Low test coverage ({file_health.test_coverage:.1f}%)",
                estimated_hours=hours,
                current_value=file_health.test_coverage,
                threshold_value=thresholds.coverage_warning,
            ))

        # Long functions
        long_funcs = [f for f in file_health.functions if f.lines_of_code > thresholds.loc_per_function_warning]
        if long_funcs:
            for func in long_funcs:
                severity = (
                    HealthStatus.CRITICAL
                    if func.lines_of_code > thresholds.loc_per_function_critical
                    else HealthStatus.WARNING
                )
                hours = (func.lines_of_code - thresholds.loc_per_function_warning) / 100

                debt_items.append(TechDebtItem(
                    category='complexity',
                    severity=severity,
                    file_path=file_health.file_path,
                    line_number=func.line_start,
                    description=f"Long function '{func.name}' ({func.lines_of_code} LOC)",
                    estimated_hours=hours,
                    current_value=func.lines_of_code,
                    threshold_value=thresholds.loc_per_function_warning,
                ))

        return debt_items

    def find_duplicates(
        self,
        files: List[Path],
        min_lines: int = 6
    ) -> List[DuplicateBlock]:
        """
        Find duplicate code blocks across files.
        Uses hash-based detection for exact matches.
        """
        duplicates = {}

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Slide a window over the lines
                for i in range(len(lines) - min_lines + 1):
                    block = lines[i:i + min_lines]
                    # Normalize: strip whitespace for comparison
                    normalized = ''.join(line.strip() for line in block)

                    # Skip blocks that are mostly empty or comments
                    if not normalized or normalized.startswith('#' * min_lines):
                        continue

                    # Hash the block
                    block_hash = hashlib.md5(normalized.encode()).hexdigest()

                    if block_hash not in duplicates:
                        duplicates[block_hash] = {
                            'lines': block,
                            'occurrences': []
                        }

                    duplicates[block_hash]['occurrences'].append(
                        (str(file_path), i + 1)
                    )

            except Exception as e:
                logger.warning(f"Failed to check duplicates in {file_path}: {e}")

        # Filter to only actual duplicates (2+ occurrences)
        duplicate_blocks = [
            DuplicateBlock(
                hash_value=hash_val,
                lines=data['lines'],
                occurrences=data['occurrences']
            )
            for hash_val, data in duplicates.items()
            if len(data['occurrences']) >= 2
        ]

        return duplicate_blocks

    def get_coverage(self, project_root: Path) -> Tuple[float, float]:
        """
        Get test coverage and documentation coverage.
        Returns (test_coverage, doc_coverage)
        """
        test_coverage = 0.0
        doc_coverage = 0.0

        # Try to get test coverage from pytest-cov
        try:
            result = subprocess.run(
                ['pytest', '--cov', '--cov-report=json', '--quiet'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            coverage_file = project_root / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    data = json.load(f)
                    test_coverage = data.get('totals', {}).get('percent_covered', 0.0)
        except Exception as e:
            logger.warning(f"Failed to get test coverage: {e}")

        # Calculate documentation coverage manually
        try:
            total_functions = 0
            documented_functions = 0

            for py_file in project_root.rglob('*.py'):
                if self._should_exclude(py_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                            if ast.get_docstring(node):
                                documented_functions += 1
                except Exception:
                    continue

            if total_functions > 0:
                doc_coverage = (documented_functions / total_functions) * 100

        except Exception as e:
            logger.warning(f"Failed to calculate documentation coverage: {e}")

        return round(test_coverage, 2), round(doc_coverage, 2)

    def check_dependencies(self, project_root: Path) -> List[DependencyIssue]:
        """Check for outdated and vulnerable dependencies"""
        issues = []

        # Check requirements.txt
        req_file = project_root / 'requirements.txt'
        if not req_file.exists():
            return issues

        try:
            # Use pip list --outdated
            result = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                outdated = json.loads(result.stdout)
                for pkg in outdated:
                    issues.append(DependencyIssue(
                        package_name=pkg['name'],
                        current_version=pkg['version'],
                        latest_version=pkg['latest_version'],
                        is_outdated=True,
                        severity=HealthStatus.WARNING
                    ))

        except Exception as e:
            logger.warning(f"Failed to check dependencies: {e}")

        # Try to check for vulnerabilities with pip-audit (if available)
        try:
            result = subprocess.run(
                ['pip-audit', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                vulns = json.loads(result.stdout)
                for vuln in vulns.get('vulnerabilities', []):
                    pkg_name = vuln.get('name', 'unknown')
                    existing = next((i for i in issues if i.package_name == pkg_name), None)

                    if existing:
                        existing.has_vulnerabilities = True
                        existing.vulnerability_count += 1
                        existing.severity = HealthStatus.CRITICAL
                    else:
                        issues.append(DependencyIssue(
                            package_name=pkg_name,
                            current_version=vuln.get('version', 'unknown'),
                            has_vulnerabilities=True,
                            vulnerability_count=1,
                            severity=HealthStatus.CRITICAL
                        ))

        except (subprocess.CalledProcessError, FileNotFoundError):
            # pip-audit not installed, skip vulnerability check
            pass
        except Exception as e:
            logger.warning(f"Failed to check vulnerabilities: {e}")

        return issues

    def get_trends(self, lookback_days: int = 30) -> Dict[str, TrendDirection]:
        """
        Analyze trends over time by comparing current metrics with historical data.
        Returns trend direction for key metrics.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        trends = {
            'complexity': TrendDirection.UNKNOWN,
            'maintainability': TrendDirection.UNKNOWN,
            'coverage': TrendDirection.UNKNOWN,
            'tech_debt': TrendDirection.UNKNOWN,
        }

        try:
            # Get historical snapshots
            cursor.execute('''
                SELECT avg_complexity, avg_maintainability, test_coverage, total_tech_debt_hours
                FROM health_snapshots
                WHERE timestamp >= ? AND project_root = ?
                ORDER BY timestamp ASC
            ''', (cutoff_date, str(self.project_root)))

            snapshots = cursor.fetchall()

            if len(snapshots) >= 2:
                # Compare first third vs last third
                third = len(snapshots) // 3
                old_metrics = snapshots[:third]
                new_metrics = snapshots[-third:]

                # Average old vs new
                old_avg = {
                    'complexity': sum(s[0] for s in old_metrics) / len(old_metrics),
                    'maintainability': sum(s[1] for s in old_metrics) / len(old_metrics),
                    'coverage': sum(s[2] for s in old_metrics) / len(old_metrics),
                    'tech_debt': sum(s[3] for s in old_metrics) / len(old_metrics),
                }

                new_avg = {
                    'complexity': sum(s[0] for s in new_metrics) / len(new_metrics),
                    'maintainability': sum(s[1] for s in new_metrics) / len(new_metrics),
                    'coverage': sum(s[2] for s in new_metrics) / len(new_metrics),
                    'tech_debt': sum(s[3] for s in new_metrics) / len(new_metrics),
                }

                # Determine trends (5% threshold for "stable")
                # Lower complexity is better
                complexity_change = (new_avg['complexity'] - old_avg['complexity']) / max(old_avg['complexity'], 1)
                if complexity_change < -0.05:
                    trends['complexity'] = TrendDirection.IMPROVING
                elif complexity_change > 0.05:
                    trends['complexity'] = TrendDirection.DEGRADING
                else:
                    trends['complexity'] = TrendDirection.STABLE

                # Higher maintainability is better
                maint_change = (new_avg['maintainability'] - old_avg['maintainability']) / max(old_avg['maintainability'], 1)
                if maint_change > 0.05:
                    trends['maintainability'] = TrendDirection.IMPROVING
                elif maint_change < -0.05:
                    trends['maintainability'] = TrendDirection.DEGRADING
                else:
                    trends['maintainability'] = TrendDirection.STABLE

                # Higher coverage is better
                cov_change = (new_avg['coverage'] - old_avg['coverage']) / max(old_avg['coverage'], 1)
                if cov_change > 0.05:
                    trends['coverage'] = TrendDirection.IMPROVING
                elif cov_change < -0.05:
                    trends['coverage'] = TrendDirection.DEGRADING
                else:
                    trends['coverage'] = TrendDirection.STABLE

                # Lower tech debt is better
                debt_change = (new_avg['tech_debt'] - old_avg['tech_debt']) / max(old_avg['tech_debt'], 1)
                if debt_change < -0.05:
                    trends['tech_debt'] = TrendDirection.IMPROVING
                elif debt_change > 0.05:
                    trends['tech_debt'] = TrendDirection.DEGRADING
                else:
                    trends['tech_debt'] = TrendDirection.STABLE

        except Exception as e:
            logger.warning(f"Failed to calculate trends: {e}")

        finally:
            conn.close()

        return trends

    def analyze_file(self, file_path: Path) -> Optional[FileHealth]:
        """Analyze health metrics for a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)
            blank_lines = sum(1 for line in lines if not line.strip())
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            code_lines = total_lines - blank_lines - comment_lines

            # Calculate complexity
            functions = self.calculate_complexity(file_path)

            if functions:
                avg_complexity = sum(f.cyclomatic_complexity for f in functions) / len(functions)
                max_complexity = max(f.cyclomatic_complexity for f in functions)
            else:
                avg_complexity = 0.0
                max_complexity = 0

            # Calculate maintainability
            maintainability = self.calculate_maintainability(file_path, functions)

            # Check for tests
            file_name = file_path.name
            has_tests = file_name.startswith('test_') or file_name.endswith('_test.py')

            # Documentation coverage for this file
            if functions:
                documented = sum(1 for f in functions if f.has_docstring)
                doc_coverage = (documented / len(functions)) * 100
            else:
                doc_coverage = 100.0

            # Determine status
            if (max_complexity > self.thresholds.complexity_critical or
                maintainability < self.thresholds.maintainability_critical):
                status = HealthStatus.CRITICAL
            elif (max_complexity > self.thresholds.complexity_warning or
                  maintainability < self.thresholds.maintainability_warning):
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.GOOD

            return FileHealth(
                file_path=str(file_path.relative_to(self.project_root)),
                total_lines=total_lines,
                code_lines=code_lines,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                functions=functions,
                avg_complexity=round(avg_complexity, 2),
                max_complexity=max_complexity,
                maintainability_index=maintainability,
                has_tests=has_tests,
                test_coverage=0.0,  # Set by project-level analysis
                documentation_coverage=round(doc_coverage, 2),
                duplicate_lines=0,  # Set by duplication analysis
                status=status,
            )

        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return None

    async def analyze_project(self) -> ProjectHealth:
        """Perform comprehensive project health analysis"""
        timestamp = datetime.now()

        # Find all Python files
        py_files = [
            f for f in self.project_root.rglob('*.py')
            if not self._should_exclude(f)
        ]

        logger.info(f"Analyzing {len(py_files)} Python files...")

        # Analyze each file
        file_health_list = []
        for file_path in py_files:
            health = self.analyze_file(file_path)
            if health:
                file_health_list.append(health)

        # Calculate aggregates
        total_files = len(file_health_list)
        total_lines = sum(f.total_lines for f in file_health_list)
        total_code_lines = sum(f.code_lines for f in file_health_list)
        total_functions = sum(f.function_count for f in file_health_list)

        if file_health_list:
            avg_complexity = sum(f.avg_complexity for f in file_health_list) / total_files
            avg_maintainability = sum(f.maintainability_index for f in file_health_list) / total_files
        else:
            avg_complexity = 0.0
            avg_maintainability = 100.0

        # Count high complexity functions
        high_complexity_funcs = sum(
            1 for f in file_health_list
            for func in f.functions
            if func.cyclomatic_complexity > self.thresholds.complexity_warning
        )

        # Get coverage
        test_coverage, doc_coverage = self.get_coverage(self.project_root)

        # Update file health with project-level coverage
        for file_health in file_health_list:
            file_health.test_coverage = test_coverage

        # Find duplicates
        logger.info("Scanning for code duplicates...")
        duplicate_blocks = self.find_duplicates(py_files)

        # Calculate duplication percentage
        total_duplicate_lines = sum(
            len(block.lines) * (block.duplication_count - 1)
            for block in duplicate_blocks
        )
        duplication_pct = (total_duplicate_lines / max(total_code_lines, 1)) * 100

        # Estimate technical debt
        logger.info("Estimating technical debt...")
        all_debt_items = []
        for file_health in file_health_list:
            debt_items = self.estimate_tech_debt(file_health, self.thresholds)
            all_debt_items.extend(debt_items)

        # Add duplicate-related debt
        for block in duplicate_blocks:
            all_debt_items.append(TechDebtItem(
                category='duplication',
                severity=HealthStatus.WARNING if block.duplication_count < 5 else HealthStatus.CRITICAL,
                file_path=block.occurrences[0][0],
                line_number=block.occurrences[0][1],
                description=f"Code duplicated {block.duplication_count} times ({len(block.lines)} lines)",
                estimated_hours=block.estimated_hours,
                current_value=block.duplication_count,
                threshold_value=2.0,
            ))

        total_tech_debt_hours = sum(item.estimated_hours for item in all_debt_items)

        # Check dependencies
        logger.info("Checking dependency health...")
        dependency_issues = self.check_dependencies(self.project_root)

        # Get trends
        trends = self.get_trends()

        # Determine overall status
        critical_count = sum(1 for f in file_health_list if f.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for f in file_health_list if f.status == HealthStatus.WARNING)

        if critical_count > total_files * 0.1:  # >10% critical
            overall_status = HealthStatus.CRITICAL
        elif warning_count > total_files * 0.25:  # >25% warning
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.GOOD

        # Create project health
        project_health = ProjectHealth(
            timestamp=timestamp,
            project_root=str(self.project_root),
            total_files=total_files,
            total_lines=total_lines,
            total_code_lines=total_code_lines,
            file_health=file_health_list,
            avg_complexity=round(avg_complexity, 2),
            avg_maintainability=round(avg_maintainability, 2),
            total_functions=total_functions,
            high_complexity_functions=high_complexity_funcs,
            test_coverage=test_coverage,
            documentation_coverage=doc_coverage,
            duplicate_blocks=duplicate_blocks,
            duplication_percentage=round(duplication_pct, 2),
            tech_debt_items=all_debt_items,
            total_tech_debt_hours=round(total_tech_debt_hours, 2),
            dependency_issues=dependency_issues,
            complexity_trend=trends['complexity'],
            maintainability_trend=trends['maintainability'],
            coverage_trend=trends['coverage'],
            tech_debt_trend=trends['tech_debt'],
            overall_status=overall_status,
        )

        # Save to database
        self._save_snapshot(project_health)

        return project_health

    def _save_snapshot(self, health: ProjectHealth):
        """Save health snapshot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert snapshot
            cursor.execute('''
                INSERT INTO health_snapshots (
                    timestamp, project_root, total_files, total_lines,
                    avg_complexity, avg_maintainability, test_coverage,
                    documentation_coverage, duplication_percentage,
                    total_tech_debt_hours, overall_status, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                health.timestamp.isoformat(),
                health.project_root,
                health.total_files,
                health.total_lines,
                health.avg_complexity,
                health.avg_maintainability,
                health.test_coverage,
                health.documentation_coverage,
                health.duplication_percentage,
                health.total_tech_debt_hours,
                health.overall_status.value,
                json.dumps({
                    'total_functions': health.total_functions,
                    'high_complexity_functions': health.high_complexity_functions,
                })
            ))

            snapshot_id = cursor.lastrowid

            # Insert file metrics
            for file_health in health.file_health:
                cursor.execute('''
                    INSERT INTO file_metrics (
                        snapshot_id, file_path, timestamp, total_lines, code_lines,
                        avg_complexity, max_complexity, maintainability_index,
                        test_coverage, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    file_health.file_path,
                    health.timestamp.isoformat(),
                    file_health.total_lines,
                    file_health.code_lines,
                    file_health.avg_complexity,
                    file_health.max_complexity,
                    file_health.maintainability_index,
                    file_health.test_coverage,
                    file_health.status.value,
                ))

                file_metric_id = cursor.lastrowid

                # Insert function metrics
                for func in file_health.functions:
                    cursor.execute('''
                        INSERT INTO function_metrics (
                            file_metric_id, function_name, cyclomatic_complexity,
                            cognitive_complexity, lines_of_code, num_parameters, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_metric_id,
                        func.name,
                        func.cyclomatic_complexity,
                        func.cognitive_complexity,
                        func.lines_of_code,
                        func.num_parameters,
                        health.timestamp.isoformat(),
                    ))

            # Insert tech debt items
            for debt in health.tech_debt_items:
                cursor.execute('''
                    INSERT INTO tech_debt (
                        snapshot_id, category, severity, file_path, line_number,
                        description, estimated_hours, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    debt.category,
                    debt.severity.value,
                    debt.file_path,
                    debt.line_number,
                    debt.description,
                    debt.estimated_hours,
                    health.timestamp.isoformat(),
                ))

            conn.commit()
            logger.info(f"Saved health snapshot with ID {snapshot_id}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save snapshot: {e}")

        finally:
            conn.close()

    def generate_report(self, health: ProjectHealth, format: str = 'text') -> str:
        """
        Generate human-readable health report.

        Args:
            health: ProjectHealth instance
            format: 'text', 'markdown', or 'json'
        """
        if format == 'json':
            return json.dumps({
                'timestamp': health.timestamp.isoformat(),
                'overall_status': health.overall_status.value,
                'metrics': {
                    'total_files': health.total_files,
                    'total_lines': health.total_lines,
                    'total_functions': health.total_functions,
                    'avg_complexity': health.avg_complexity,
                    'avg_maintainability': health.avg_maintainability,
                    'test_coverage': health.test_coverage,
                    'documentation_coverage': health.documentation_coverage,
                    'duplication_percentage': health.duplication_percentage,
                    'total_tech_debt_hours': health.total_tech_debt_hours,
                },
                'trends': {
                    'complexity': health.complexity_trend.value,
                    'maintainability': health.maintainability_trend.value,
                    'coverage': health.coverage_trend.value,
                    'tech_debt': health.tech_debt_trend.value,
                },
                'status_summary': health.get_status_summary(),
                'tech_debt_items': [item.to_dict() for item in health.tech_debt_items[:10]],
                'dependency_issues': len(health.dependency_issues),
            }, indent=2)

        # Markdown format
        if format == 'markdown':
            lines = [
                f"# Code Health Report",
                f"",
                f"**Generated:** {health.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Overall Status:** {health.overall_status.value.upper()}",
                f"",
                f"## Summary",
                f"",
                f"- **Total Files:** {health.total_files}",
                f"- **Total Lines:** {health.total_lines:,}",
                f"- **Code Lines:** {health.total_code_lines:,}",
                f"- **Total Functions:** {health.total_functions}",
                f"",
                f"## Code Quality Metrics",
                f"",
                f"| Metric | Value | Trend | Status |",
                f"|--------|-------|-------|--------|",
                f"| Avg Complexity | {health.avg_complexity:.2f} | {health.complexity_trend.value} | {self._get_status_icon(health.avg_complexity, self.thresholds.complexity_warning, self.thresholds.complexity_critical, inverse=False)} |",
                f"| Maintainability Index | {health.avg_maintainability:.2f} | {health.maintainability_trend.value} | {self._get_status_icon(health.avg_maintainability, self.thresholds.maintainability_warning, self.thresholds.maintainability_critical, inverse=True)} |",
                f"| Test Coverage | {health.test_coverage:.1f}% | {health.coverage_trend.value} | {self._get_status_icon(health.test_coverage, self.thresholds.coverage_warning, self.thresholds.coverage_critical, inverse=True)} |",
                f"| Documentation Coverage | {health.documentation_coverage:.1f}% | - | {self._get_status_icon(health.documentation_coverage, self.thresholds.docs_warning, self.thresholds.docs_critical, inverse=True)} |",
                f"| Code Duplication | {health.duplication_percentage:.1f}% | - | {self._get_status_icon(health.duplication_percentage, self.thresholds.duplication_warning, self.thresholds.duplication_critical, inverse=False)} |",
                f"",
                f"## Technical Debt",
                f"",
                f"**Total Estimated Hours:** {health.total_tech_debt_hours:.1f} hours",
                f"**Trend:** {health.tech_debt_trend.value}",
                f"",
                f"### Top Issues",
                f"",
            ]

            # Add top 10 debt items
            sorted_debt = sorted(health.tech_debt_items, key=lambda x: x.estimated_hours, reverse=True)[:10]
            for i, item in enumerate(sorted_debt, 1):
                lines.append(f"{i}. **{item.category.title()}** ({item.severity.value}) - {item.description}")
                lines.append(f"   - File: `{item.file_path}:{item.line_number}`")
                lines.append(f"   - Estimated hours: {item.estimated_hours:.1f}")
                lines.append("")

            # File status summary
            summary = health.get_status_summary()
            lines.extend([
                f"## File Health Summary",
                f"",
                f"- Good: {summary['good']} files",
                f"- Warning: {summary['warning']} files",
                f"- Critical: {summary['critical']} files",
                f"",
            ])

            # Dependencies
            if health.dependency_issues:
                lines.extend([
                    f"## Dependency Issues",
                    f"",
                    f"**Total Issues:** {len(health.dependency_issues)}",
                    f"",
                ])

                critical_deps = [d for d in health.dependency_issues if d.severity == HealthStatus.CRITICAL]
                if critical_deps:
                    lines.append("### Critical (Vulnerabilities)")
                    lines.append("")
                    for dep in critical_deps[:5]:
                        lines.append(f"- **{dep.package_name}** {dep.current_version} - {dep.vulnerability_count} vulnerabilities")
                    lines.append("")

            return '\n'.join(lines)

        # Text format (default)
        lines = [
            "=" * 80,
            "CODE HEALTH REPORT".center(80),
            "=" * 80,
            f"Generated: {health.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Overall Status: {health.overall_status.value.upper()}",
            "",
            "SUMMARY",
            "-" * 80,
            f"Total Files:      {health.total_files}",
            f"Total Lines:      {health.total_lines:,}",
            f"Code Lines:       {health.total_code_lines:,}",
            f"Total Functions:  {health.total_functions}",
            f"High Complexity:  {health.high_complexity_functions}",
            "",
            "QUALITY METRICS",
            "-" * 80,
            f"Avg Complexity:         {health.avg_complexity:.2f} ({health.complexity_trend.value})",
            f"Maintainability Index:  {health.avg_maintainability:.2f} ({health.maintainability_trend.value})",
            f"Test Coverage:          {health.test_coverage:.1f}% ({health.coverage_trend.value})",
            f"Documentation Coverage: {health.documentation_coverage:.1f}%",
            f"Code Duplication:       {health.duplication_percentage:.1f}%",
            "",
            "TECHNICAL DEBT",
            "-" * 80,
            f"Total Estimated Hours: {health.total_tech_debt_hours:.1f} ({health.tech_debt_trend.value})",
            f"Total Issues:          {len(health.tech_debt_items)}",
            "",
            "Top 5 Issues:",
        ]

        sorted_debt = sorted(health.tech_debt_items, key=lambda x: x.estimated_hours, reverse=True)[:5]
        for i, item in enumerate(sorted_debt, 1):
            lines.append(f"  {i}. [{item.severity.value.upper()}] {item.description}")
            lines.append(f"     {item.file_path}:{item.line_number} ({item.estimated_hours:.1f}h)")

        # Status summary
        summary = health.get_status_summary()
        lines.extend([
            "",
            "FILE HEALTH SUMMARY",
            "-" * 80,
            f"Good:     {summary['good']} files",
            f"Warning:  {summary['warning']} files",
            f"Critical: {summary['critical']} files",
            "=" * 80,
        ])

        return '\n'.join(lines)

    def _get_status_icon(self, value: float, warning: float, critical: float, inverse: bool = False) -> str:
        """Get status icon based on thresholds"""
        if inverse:
            # Higher is better (coverage, maintainability)
            if value >= warning:
                return "✓"
            elif value >= critical:
                return "⚠"
            else:
                return "✗"
        else:
            # Lower is better (complexity, duplication)
            if value <= warning:
                return "✓"
            elif value <= critical:
                return "⚠"
            else:
                return "✗"


# Singleton instance
_dashboard_instance: Optional[HealthDashboard] = None


def get_health_dashboard(
    project_root: Optional[str] = None,
    **kwargs
) -> HealthDashboard:
    """Get or create singleton HealthDashboard instance"""
    global _dashboard_instance

    if _dashboard_instance is None or project_root is not None:
        if project_root is None:
            raise ValueError("project_root required for first initialization")
        _dashboard_instance = HealthDashboard(project_root=project_root, **kwargs)

    return _dashboard_instance
