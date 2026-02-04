# Dependency Scanner Service

Production-grade dependency scanner with comprehensive vulnerability detection, license checking, and security analysis for multi-language projects.

## Features

- **Multi-Language Support**: Python, JavaScript/Node.js, Rust, Go
- **Vulnerability Detection**: Integration with OSV and NVD databases
- **Outdated Package Detection**: Automatic checking against latest versions
- **License Compliance**: Classification and validation of dependency licenses
- **Unused Dependency Detection**: Heuristic analysis to find unused packages
- **Dependency Tree Visualization**: Visual representation of project dependencies
- **Caching System**: 24-hour cache for vulnerability data to minimize API calls
- **Batch Processing**: Concurrent scanning with rate limiting
- **Security Recommendations**: Actionable advice for fixing vulnerabilities

## Supported Formats

### Python
- `requirements.txt` - Standard Python requirements format
- `pyproject.toml` - Poetry and PEP 621 formats

### JavaScript/Node.js
- `package.json` - npm/yarn dependencies

### Rust
- `Cargo.toml` - Cargo dependencies

### Go
- `go.mod` - Go module dependencies

## Installation

The scanner requires the following dependencies (already in requirements.txt):

```bash
pip install httpx>=0.27.0
```

For TOML parsing (Python, Rust, Go):
```bash
# Python 3.11+
# Built-in tomllib is used

# Python <3.11
pip install tomli
```

## Quick Start

```python
from api.services.deps import DependencyScanner, quick_scan

# Quick scan using convenience function
result = await quick_scan("/path/to/project")

print(f"Found {result.total_vulnerabilities} vulnerabilities")
print(f"Critical: {result.critical_count}")
print(f"High: {result.high_count}")
```

## Usage Examples

### Full Project Scan

```python
from api.services.deps import DependencyScanner
from pathlib import Path

scanner = DependencyScanner()

try:
    # Scan project
    result = await scanner.scan_project("/path/to/project")

    # Print statistics
    print(f"Dependencies: {len(result.dependencies)}")
    print(f"Vulnerabilities: {result.total_vulnerabilities}")
    print(f"Outdated: {result.outdated_count}")
    print(f"License Issues: {len(result.license_issues)}")

    # Generate report
    report = scanner.generate_report(result)
    print(report)

finally:
    await scanner.close()
```

### Check Specific Dependencies

```python
from api.services.deps import DependencyScanner, Dependency

scanner = DependencyScanner()

try:
    # Create dependency objects
    deps = [
        Dependency(name="requests", version="2.25.0", ecosystem="pypi"),
        Dependency(name="express", version="4.17.0", ecosystem="npm"),
    ]

    # Check for vulnerabilities
    await scanner.check_vulnerabilities(deps)

    # Check for updates
    await scanner.check_outdated(deps)

    # Check licenses
    issues = await scanner.check_licenses(deps)

    # Print results
    for dep in deps:
        print(f"{dep.name}@{dep.version}")
        print(f"  Vulnerabilities: {len(dep.vulnerabilities)}")
        print(f"  Latest: {dep.latest_version}")
        print(f"  License: {dep.license}")

finally:
    await scanner.close()
```

### Export Results

```python
import json

# Scan project
result = await scanner.scan_project("/path/to/project")

# Export to JSON
with open("scan_results.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)

# Generate human-readable report
report = scanner.generate_report(result)
with open("scan_report.txt", "w") as f:
    f.write(report)

# Generate dependency tree
tree = scanner.generate_tree_visualization(result.dependencies)
with open("dependency_tree.txt", "w") as f:
    f.write(tree)
```

### Filter by Severity

```python
from api.services.deps import Severity

result = await scanner.scan_project("/path/to/project")

# Get critical vulnerabilities
critical = [
    dep for dep in result.dependencies
    if dep.highest_severity == Severity.CRITICAL
]

# Get all high and critical
high_priority = [
    dep for dep in result.dependencies
    if dep.highest_severity in (Severity.CRITICAL, Severity.HIGH)
]

print(f"Critical: {len(critical)} packages")
print(f"High Priority: {len(high_priority)} packages")
```

## API Reference

### DependencyScanner

Main scanner class for dependency analysis.

#### Methods

- `__init__(cache_dir: Path | None = None)`: Initialize scanner with optional cache directory
- `async scan_project(project_path: str | Path) -> ScanResult`: Scan entire project
- `async scan_python_deps(project_path: Path) -> list[Dependency]`: Scan Python dependencies
- `async scan_npm_deps(project_path: Path) -> list[Dependency]`: Scan npm dependencies
- `async scan_rust_deps(project_path: Path) -> list[Dependency]`: Scan Rust dependencies
- `async scan_go_deps(project_path: Path) -> list[Dependency]`: Scan Go dependencies
- `async check_vulnerabilities(dependencies: list[Dependency])`: Check for CVEs
- `async check_outdated(dependencies: list[Dependency])`: Check for updates
- `async check_licenses(dependencies: list[Dependency]) -> list[LicenseIssue]`: Check licenses
- `async find_unused(project_path: Path, dependencies: list[Dependency])`: Find unused deps
- `generate_report(result: ScanResult) -> str`: Generate text report
- `generate_tree_visualization(dependencies: list[Dependency]) -> str`: Generate tree
- `async close()`: Clean up resources

### Dependency

Represents a project dependency.

#### Properties

- `name: str`: Package name
- `version: str`: Package version
- `ecosystem: str`: Package ecosystem (pypi, npm, cargo, go)
- `latest_version: str | None`: Latest available version
- `is_outdated: bool`: Whether package is outdated
- `is_unused: bool`: Whether package appears unused
- `license: str | None`: License name
- `license_type: LicenseType`: License classification
- `vulnerabilities: list[Vulnerability]`: Known vulnerabilities
- `dependencies: list[str]`: Child dependencies
- `source_file: str | None`: Source file path
- `has_vulnerabilities: bool`: Property - has any vulnerabilities
- `highest_severity: Severity`: Property - highest vulnerability severity

### Vulnerability

Represents a security vulnerability.

#### Properties

- `cve_id: str`: CVE identifier
- `severity: Severity`: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- `description: str`: Vulnerability description
- `fix_version: str | None`: Version with fix
- `cvss_score: float | None`: CVSS score
- `published_date: str | None`: Publication date
- `references: list[str]`: Reference URLs
- `affected_versions: list[str]`: Affected version ranges
- `source: str`: Data source (OSV, NVD)

### ScanResult

Results from a dependency scan.

#### Properties

- `dependencies: list[Dependency]`: All scanned dependencies
- `license_issues: list[LicenseIssue]`: License compliance issues
- `scan_timestamp: str`: Scan timestamp
- `project_path: str | None`: Project path
- `ecosystems_scanned: list[str]`: Scanned ecosystems
- `total_vulnerabilities: int`: Total vulnerability count
- `critical_count: int`: Critical vulnerabilities
- `high_count: int`: High severity vulnerabilities
- `medium_count: int`: Medium severity vulnerabilities
- `low_count: int`: Low severity vulnerabilities
- `outdated_count: int`: Outdated packages
- `unused_count: int`: Unused packages

### VulnerabilityDatabase

Client for vulnerability databases (OSV, NVD).

#### Methods

- `__init__(cache_dir: Path | None = None)`: Initialize with cache
- `async query_osv(ecosystem: str, package: str, version: str) -> list[Vulnerability]`: Query OSV API
- `async close()`: Close HTTP client

## Caching

The scanner implements a 24-hour cache for vulnerability data to minimize API calls and improve performance.

Cache location: `~/.magnetar/vuln_cache/`

Cache files are named using MD5 hashes of `ecosystem:package:version`.

To clear cache:
```bash
rm -rf ~/.magnetar/vuln_cache/
```

## Performance Considerations

- **Concurrent Scanning**: Uses asyncio for parallel vulnerability checks
- **Rate Limiting**: Batches requests to avoid API rate limits
- **Caching**: 24-hour cache reduces API calls by ~90%
- **File Size Limits**: Skips files >1MB during unused dependency detection
- **Directory Exclusions**: Skips common non-source directories (node_modules, venv, etc.)

## Security Features

- **Safe File Operations**: Uses pathlib and safe file reading
- **No Command Injection**: File-based parsing only, no shell commands
- **Size Limits**: Prevents reading of excessively large files
- **Error Handling**: Graceful degradation on API failures
- **Input Validation**: Regex-based requirement parsing

## License Classification

### Permissive Licenses
- MIT
- Apache-2.0
- BSD (all variants)
- ISC
- Unlicense
- CC0-1.0

### Copyleft Licenses
- GPL (all versions)
- AGPL
- LGPL
- MPL-2.0
- EPL-2.0

### Proprietary
- Detected via keywords: PROPRIETARY, COMMERCIAL, CLOSED

## Vulnerability Severity

Based on CVSS scores:

- **CRITICAL**: CVSS 9.0-10.0
- **HIGH**: CVSS 7.0-8.9
- **MEDIUM**: CVSS 4.0-6.9
- **LOW**: CVSS 0.1-3.9
- **UNKNOWN**: No score available

## Integration with MagnetarCode

### API Endpoint Example

```python
from fastapi import APIRouter, HTTPException
from api.services.deps import DependencyScanner
from pathlib import Path

router = APIRouter()

@router.post("/api/scan/dependencies")
async def scan_dependencies(project_path: str):
    """Scan project dependencies"""
    scanner = DependencyScanner()

    try:
        result = await scanner.scan_project(project_path)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await scanner.close()

@router.get("/api/scan/dependencies/report")
async def get_scan_report(project_path: str):
    """Get formatted dependency scan report"""
    scanner = DependencyScanner()

    try:
        result = await scanner.scan_project(project_path)
        report = scanner.generate_report(result)
        return {"report": report}
    finally:
        await scanner.close()
```

### Background Task Example

```python
from celery import shared_task
from api.services.deps import quick_scan
import asyncio

@shared_task
def scan_project_dependencies(project_path: str):
    """Background task for dependency scanning"""
    result = asyncio.run(quick_scan(project_path))

    # Send notifications for critical vulnerabilities
    if result.critical_count > 0:
        send_security_alert(result)

    return result.to_dict()
```

## Troubleshooting

### No vulnerabilities found

- Check internet connection
- Verify package names are correct
- Check OSV API status: https://api.osv.dev/
- Clear cache and retry

### Outdated detection not working

- Ensure package registries are accessible
- Check package names match registry exactly
- Verify versions are in semantic version format

### Unused detection false positives

- Heuristic-based, may have false positives
- Considers only import/require statements
- Manual verification recommended

### Cache issues

```python
# Use custom cache directory
scanner = DependencyScanner(cache_dir=Path("/tmp/vuln_cache"))

# Or disable caching by clearing after each scan
await scanner.scan_project(path)
scanner.vuln_db.cache_dir.rmdir()
```

## Contributing

To extend the scanner:

1. Add new ecosystem support in `scan_<ecosystem>_deps()`
2. Add parser for new file formats
3. Update ecosystem mapping in `VulnerabilityDatabase`
4. Add tests for new functionality

## License

Part of MagnetarCode - see main project LICENSE.

## References

- OSV Database: https://osv.dev/
- NVD Database: https://nvd.nist.gov/
- CVSS Scoring: https://www.first.org/cvss/
- SPDX Licenses: https://spdx.org/licenses/
