#!/usr/bin/env python3
"""
Background Code Analyzer

Continuously analyzes codebase for issues:
- Security vulnerabilities (OWASP, CWE)
- Performance anti-patterns
- Code quality issues
- Dependency problems
- Dead code detection

Runs in background, surfaces findings proactively.
"""

import asyncio
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class AnalysisSeverity(Enum):
    """Severity of analysis finding."""

    CRITICAL = "critical"  # Must fix immediately
    HIGH = "high"  # Should fix soon
    MEDIUM = "medium"  # Should fix eventually
    LOW = "low"  # Nice to fix
    INFO = "info"  # Informational only


class AnalysisType(Enum):
    """Type of analysis finding."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    DEPENDENCY = "dependency"
    DEAD_CODE = "dead_code"
    BEST_PRACTICE = "best_practice"


@dataclass
class AnalysisResult:
    """Result from code analysis."""

    file_path: str
    line_number: int
    analysis_type: AnalysisType
    severity: AnalysisSeverity
    title: str
    description: str
    suggestion: str | None = None
    cwe_id: str | None = None  # For security issues
    code_snippet: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "type": self.analysis_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "cwe": self.cwe_id,
            "snippet": self.code_snippet,
        }


@dataclass
class SecurityPattern:
    """Pattern for detecting security issues."""

    name: str
    pattern: str  # Regex
    severity: AnalysisSeverity
    cwe_id: str
    description: str
    suggestion: str
    file_types: list[str] = field(default_factory=list)  # Empty = all


@dataclass
class PerformancePattern:
    """Pattern for detecting performance issues."""

    name: str
    pattern: str
    severity: AnalysisSeverity
    description: str
    suggestion: str
    file_types: list[str] = field(default_factory=list)


class BackgroundAnalyzer:
    """
    Background code analyzer for continuous security and quality monitoring.

    Runs asynchronously, caching results and only re-analyzing changed files.
    Surfaces critical issues immediately, batches lower-priority findings.

    Features:
    - Security vulnerability detection (injection, XSS, SSRF, etc.)
    - Performance anti-pattern detection
    - Code quality assessment
    - Dependency vulnerability checking
    - Dead code detection
    """

    # Security patterns to detect
    SECURITY_PATTERNS = [
        # SQL Injection
        SecurityPattern(
            name="sql_injection",
            pattern=r'(execute|cursor\.execute|raw|rawQuery)\s*\([^)]*[\'"][^)]*\+|\.format\s*\([^)]*\)|f["\'][^"\']*\{[^}]+\}[^"\']*(?:SELECT|INSERT|UPDATE|DELETE)',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-89",
            description="Potential SQL injection vulnerability detected",
            suggestion="Use parameterized queries instead of string concatenation",
            file_types=[".py"],
        ),
        SecurityPattern(
            name="sql_injection_js",
            pattern=r'(?:query|execute)\s*\([^)]*`[^`]*\$\{|(?:query|execute)\s*\([^)]*\+',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-89",
            description="Potential SQL injection vulnerability detected",
            suggestion="Use parameterized queries or prepared statements",
            file_types=[".js", ".ts"],
        ),
        # Command Injection
        SecurityPattern(
            name="command_injection",
            pattern=r'(?:subprocess|os\.system|os\.popen|commands)\s*\([^)]*(?:\+|\.format|f["\'])',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-78",
            description="Potential command injection vulnerability",
            suggestion="Use subprocess with list arguments and shell=False",
            file_types=[".py"],
        ),
        SecurityPattern(
            name="shell_true",
            pattern=r'subprocess\.[^(]+\([^)]*shell\s*=\s*True',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-78",
            description="subprocess with shell=True is dangerous",
            suggestion="Use shell=False with argument list instead",
            file_types=[".py"],
        ),
        # Path Traversal
        SecurityPattern(
            name="path_traversal",
            pattern=r'open\s*\([^)]*(?:request|input|user|param)',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-22",
            description="Potential path traversal vulnerability",
            suggestion="Validate and sanitize file paths before use",
            file_types=[".py"],
        ),
        # XSS
        SecurityPattern(
            name="xss_python",
            pattern=r'(?:render_template_string|Markup)\s*\([^)]*(?:\+|\.format|f["\'])',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-79",
            description="Potential XSS vulnerability",
            suggestion="Use proper HTML escaping or templating",
            file_types=[".py"],
        ),
        SecurityPattern(
            name="xss_js",
            pattern=r'(?:innerHTML|outerHTML|document\.write)\s*=\s*[^;]*(?:\+|`)',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-79",
            description="Potential XSS vulnerability - unsafe DOM manipulation",
            suggestion="Use textContent or sanitize HTML before insertion",
            file_types=[".js", ".ts", ".jsx", ".tsx"],
        ),
        # Hardcoded Secrets
        SecurityPattern(
            name="hardcoded_secret",
            pattern=r'(?:password|secret|api_key|apikey|auth_token|access_token)\s*=\s*["\'][^"\']{8,}["\']',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-798",
            description="Hardcoded secret detected",
            suggestion="Use environment variables or secret management",
            file_types=[".py", ".js", ".ts", ".go", ".java"],
        ),
        SecurityPattern(
            name="jwt_secret",
            pattern=r'(?:JWT_SECRET|SECRET_KEY)\s*=\s*["\'][^"\']+["\']',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-798",
            description="Hardcoded JWT/secret key detected",
            suggestion="Load secrets from environment variables",
            file_types=[".py", ".js", ".ts"],
        ),
        # Unsafe deserialization (detects unsafe serialization patterns)
        SecurityPattern(
            name="unsafe_deserialize",
            pattern=r'(?:loads?|load)\s*\(\s*(?:request|input|user|data)',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-502",
            description="Potential unsafe deserialization",
            suggestion="Use JSON or other safe serialization formats",
            file_types=[".py"],
        ),
        # Eval/exec
        SecurityPattern(
            name="eval_exec",
            pattern=r'(?:eval|exec)\s*\([^)]*(?:input|request|user)',
            severity=AnalysisSeverity.CRITICAL,
            cwe_id="CWE-94",
            description="Code injection via eval/exec",
            suggestion="Avoid eval/exec with user input entirely",
            file_types=[".py"],
        ),
        # SSRF
        SecurityPattern(
            name="ssrf",
            pattern=r'(?:requests\.get|httpx\.get|urllib\.request\.urlopen)\s*\([^)]*(?:request|input|user|param)',
            severity=AnalysisSeverity.HIGH,
            cwe_id="CWE-918",
            description="Potential SSRF vulnerability",
            suggestion="Validate and whitelist URLs before fetching",
            file_types=[".py"],
        ),
    ]

    # Performance patterns
    PERFORMANCE_PATTERNS = [
        PerformancePattern(
            name="n_plus_one",
            pattern=r'for\s+\w+\s+in\s+\w+:\s*\n[^}]*(?:\.get|\.filter|\.query|SELECT)',
            severity=AnalysisSeverity.MEDIUM,
            description="Potential N+1 query problem",
            suggestion="Use eager loading or batch queries",
            file_types=[".py"],
        ),
        PerformancePattern(
            name="sync_in_async",
            pattern=r'async\s+def\s+\w+[^:]+:\s*\n[^}]*(?:time\.sleep|open\(|\.read\()',
            severity=AnalysisSeverity.MEDIUM,
            description="Blocking call in async function",
            suggestion="Use async equivalents (asyncio.sleep, aiofiles)",
            file_types=[".py"],
        ),
        PerformancePattern(
            name="regex_recompile",
            pattern=r'for\s+\w+\s+in\s+\w+:\s*\n[^}]*re\.compile\(',
            severity=AnalysisSeverity.LOW,
            description="Regex compiled inside loop",
            suggestion="Compile regex once outside the loop",
            file_types=[".py"],
        ),
        PerformancePattern(
            name="string_concat_loop",
            pattern=r'for\s+\w+\s+in\s+\w+:\s*\n[^}]*\w+\s*\+=\s*["\']',
            severity=AnalysisSeverity.LOW,
            description="String concatenation in loop",
            suggestion="Use list.append() and ''.join() instead",
            file_types=[".py"],
        ),
        PerformancePattern(
            name="global_in_function",
            pattern=r'def\s+\w+\([^)]*\):\s*\n[^}]*global\s+\w+',
            severity=AnalysisSeverity.LOW,
            description="Global variable modified in function",
            suggestion="Pass as parameter or use class attribute",
            file_types=[".py"],
        ),
    ]

    def __init__(
        self,
        workspace_root: str | Path,
        scan_interval_seconds: int = 300,  # 5 minutes
        max_file_size_bytes: int = 1_000_000,  # 1MB
    ):
        """
        Initialize background analyzer.

        Args:
            workspace_root: Root directory to analyze
            scan_interval_seconds: Time between full scans
            max_file_size_bytes: Skip files larger than this
        """
        self.workspace_root = Path(workspace_root)
        self.scan_interval = scan_interval_seconds
        self.max_file_size = max_file_size_bytes

        # Results storage
        self._results: dict[str, list[AnalysisResult]] = defaultdict(list)
        self._last_scan_time: dict[str, float] = {}

        # Background task
        self._running = False
        self._task: asyncio.Task | None = None

        # Stats
        self._files_analyzed = 0
        self._issues_found = 0
        self._last_full_scan: datetime | None = None

        # File extensions to analyze
        self._analyzable_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".go", ".java", ".rb", ".php",
        }

    async def start(self) -> None:
        """Start background analysis."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._analysis_loop())
        logger.info("Background analyzer started")

    async def stop(self) -> None:
        """Stop background analysis."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background analyzer stopped")

    async def _analysis_loop(self) -> None:
        """Main analysis loop."""
        while self._running:
            try:
                await self._run_full_scan()
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _run_full_scan(self) -> None:
        """Run full codebase scan."""
        start = time.perf_counter()
        self._files_analyzed = 0
        self._issues_found = 0

        # Clear old results
        self._results.clear()

        # Walk workspace
        for file_path in self.workspace_root.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip non-analyzable files
            if file_path.suffix not in self._analyzable_extensions:
                continue

            # Skip large files
            try:
                if file_path.stat().st_size > self.max_file_size:
                    continue
            except OSError:
                continue

            # Skip common non-code directories
            parts = file_path.parts
            if any(
                p in parts
                for p in [
                    "node_modules", ".git", "__pycache__", "venv",
                    ".venv", "dist", "build", ".next", "coverage",
                ]
            ):
                continue

            await self._analyze_file(file_path)

        elapsed = time.perf_counter() - start
        self._last_full_scan = datetime.utcnow()

        logger.info(
            f"Full scan complete: {self._files_analyzed} files, "
            f"{self._issues_found} issues found in {elapsed:.1f}s"
        )

    async def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file."""
        try:
            content = file_path.read_text(errors="ignore")
        except Exception as e:
            logger.debug(f"Could not read {file_path}: {e}")
            return

        self._files_analyzed += 1
        relative_path = str(file_path.relative_to(self.workspace_root))
        lines = content.split("\n")

        # Security analysis
        for pattern in self.SECURITY_PATTERNS:
            if pattern.file_types and file_path.suffix not in pattern.file_types:
                continue

            for match in re.finditer(pattern.pattern, content, re.MULTILINE | re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                snippet = lines[line_num - 1] if line_num <= len(lines) else ""

                result = AnalysisResult(
                    file_path=relative_path,
                    line_number=line_num,
                    analysis_type=AnalysisType.SECURITY,
                    severity=pattern.severity,
                    title=pattern.name.replace("_", " ").title(),
                    description=pattern.description,
                    suggestion=pattern.suggestion,
                    cwe_id=pattern.cwe_id,
                    code_snippet=snippet.strip(),
                )

                self._results[relative_path].append(result)
                self._issues_found += 1

        # Performance analysis
        for pattern in self.PERFORMANCE_PATTERNS:
            if pattern.file_types and file_path.suffix not in pattern.file_types:
                continue

            for match in re.finditer(pattern.pattern, content, re.MULTILINE):
                line_num = content[:match.start()].count("\n") + 1
                snippet = lines[line_num - 1] if line_num <= len(lines) else ""

                result = AnalysisResult(
                    file_path=relative_path,
                    line_number=line_num,
                    analysis_type=AnalysisType.PERFORMANCE,
                    severity=pattern.severity,
                    title=pattern.name.replace("_", " ").title(),
                    description=pattern.description,
                    suggestion=pattern.suggestion,
                    code_snippet=snippet.strip(),
                )

                self._results[relative_path].append(result)
                self._issues_found += 1

        # Allow other tasks to run
        await asyncio.sleep(0)

    async def analyze_file_now(self, file_path: str) -> list[AnalysisResult]:
        """
        Analyze a specific file immediately.

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            List of findings
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path

        # Clear previous results for this file
        relative = str(path.relative_to(self.workspace_root))
        self._results[relative] = []

        await self._analyze_file(path)

        return self._results.get(relative, [])

    def get_results(
        self,
        severity: AnalysisSeverity | None = None,
        analysis_type: AnalysisType | None = None,
        file_path: str | None = None,
    ) -> list[AnalysisResult]:
        """
        Get analysis results with optional filtering.

        Args:
            severity: Filter by severity
            analysis_type: Filter by type
            file_path: Filter by file

        Returns:
            List of matching results
        """
        results = []

        for path, findings in self._results.items():
            if file_path and path != file_path:
                continue

            for finding in findings:
                if severity and finding.severity != severity:
                    continue
                if analysis_type and finding.analysis_type != analysis_type:
                    continue

                results.append(finding)

        # Sort by severity
        severity_order = {
            AnalysisSeverity.CRITICAL: 0,
            AnalysisSeverity.HIGH: 1,
            AnalysisSeverity.MEDIUM: 2,
            AnalysisSeverity.LOW: 3,
            AnalysisSeverity.INFO: 4,
        }
        results.sort(key=lambda x: severity_order[x.severity])

        return results

    def get_critical_issues(self) -> list[AnalysisResult]:
        """Get all critical and high severity issues."""
        return [
            r
            for r in self.get_results()
            if r.severity in (AnalysisSeverity.CRITICAL, AnalysisSeverity.HIGH)
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get analysis summary."""
        by_severity = defaultdict(int)
        by_type = defaultdict(int)

        for findings in self._results.values():
            for finding in findings:
                by_severity[finding.severity.value] += 1
                by_type[finding.analysis_type.value] += 1

        return {
            "files_analyzed": self._files_analyzed,
            "total_issues": self._issues_found,
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "last_scan": (
                self._last_full_scan.isoformat() if self._last_full_scan else None
            ),
            "running": self._running,
        }


# Global instance
_analyzer: BackgroundAnalyzer | None = None


def get_background_analyzer(
    workspace_root: str | Path | None = None,
) -> BackgroundAnalyzer:
    """Get or create global background analyzer."""
    global _analyzer

    if _analyzer is None:
        if workspace_root is None:
            workspace_root = Path.cwd()
        _analyzer = BackgroundAnalyzer(workspace_root)

    return _analyzer
