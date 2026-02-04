"""
Dependency Scanner Service

Comprehensive dependency analysis and vulnerability scanning for multi-language projects.
Supports Python (requirements.txt, pyproject.toml), JavaScript/Node.js (package.json),
Rust (Cargo.toml), and Go (go.mod).

Features:
- CVE vulnerability detection via OSV and NVD databases
- Outdated package detection
- License compliance checking
- Unused dependency identification
- Dependency tree visualization
- Security recommendations

Usage:
    from api.services.deps import DependencyScanner, ScanResult

    scanner = DependencyScanner()
    result = await scanner.scan_project("/path/to/project")

    print(f"Found {len(result.vulnerabilities)} vulnerabilities")
    print(result.generate_report())
"""

from .scanner import (
    Dependency,
    DependencyScanner,
    LicenseIssue,
    ScanResult,
    Vulnerability,
    VulnerabilityDatabase,
)

__all__ = [
    "Dependency",
    "DependencyScanner",
    "LicenseIssue",
    "ScanResult",
    "Vulnerability",
    "VulnerabilityDatabase",
]
