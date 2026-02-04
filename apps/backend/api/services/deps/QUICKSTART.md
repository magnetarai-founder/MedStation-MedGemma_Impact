# Dependency Scanner - Quick Start Guide

Get started with the MagnetarCode Dependency Scanner in 5 minutes.

## Installation

The scanner is already integrated into MagnetarCode. No additional installation needed!

Required dependencies (already in `requirements.txt`):
- `httpx>=0.27.0`

## Basic Usage

### 1. Scan Your Project (CLI)

```bash
# Scan current directory
cd /path/to/your/project
python -m api.services.deps.cli scan .

# Scan specific project
python -m api.services.deps.cli scan /path/to/project

# Show only critical vulnerabilities
python -m api.services.deps.cli scan . --severity critical

# Include dependency tree
python -m api.services.deps.cli scan . --tree
```

### 2. Use in Python Code

```python
import asyncio
from api.services.deps import quick_scan

# Quick scan
async def main():
    result = await quick_scan("/path/to/project")

    print(f"Dependencies: {len(result.dependencies)}")
    print(f"Vulnerabilities: {result.total_vulnerabilities}")
    print(f"Critical: {result.critical_count}")
    print(f"High: {result.high_count}")

asyncio.run(main())
```

### 3. Full Control

```python
from api.services.deps import DependencyScanner

async def detailed_scan():
    scanner = DependencyScanner()

    try:
        # Scan project
        result = await scanner.scan_project("/path/to/project")

        # Generate report
        report = scanner.generate_report(result)
        print(report)

        # Generate tree
        tree = scanner.generate_tree_visualization(result.dependencies)
        print(tree)

        # Export to JSON
        import json
        with open("scan_results.json", "w") as f:
            json.dump(result.to_dict(), f, indent=2)

    finally:
        await scanner.close()

asyncio.run(detailed_scan())
```

## Common Commands

### Check Specific Package

```bash
python -m api.services.deps.cli check-vuln \
    --package requests \
    --version 2.25.0 \
    --ecosystem pypi
```

### Export Results

```bash
# JSON export
python -m api.services.deps.cli export . --format json --output results.json

# Text report
python -m api.services.deps.cli export . --format text --output report.txt

# Dependency tree
python -m api.services.deps.cli export . --format tree --output tree.txt
```

### List Dependencies

```bash
# List all
python -m api.services.deps.cli list .

# List Python only
python -m api.services.deps.cli list . --ecosystem pypi

# List npm only
python -m api.services.deps.cli list . --ecosystem npm
```

### Show Statistics

```bash
python -m api.services.deps.cli stats .
```

## Examples

### Check MagnetarCode Backend

```bash
cd /Users/indiedevhipps/Documents/MagnetarCode

# Quick scan
python -m api.services.deps.cli scan apps/backend

# Show outdated packages
python -m api.services.deps.cli scan apps/backend --show-outdated

# Show license issues
python -m api.services.deps.cli scan apps/backend --show-licenses

# Full report with tree
python -m api.services.deps.cli scan apps/backend --show-outdated --show-unused --tree
```

### Filter by Severity

```bash
# Only critical
python -m api.services.deps.cli scan . --severity critical

# High and above
python -m api.services.deps.cli scan . --severity high

# Medium and above
python -m api.services.deps.cli scan . --severity medium
```

## Understanding Output

### Scan Results

```
================================================================================
SCAN RESULTS
================================================================================
Dependencies found: 49
Ecosystems: pypi, npm
Total vulnerabilities: 5
  Critical: 1    ← Fix immediately!
  High: 2        ← Fix soon
  Medium: 2      ← Plan to fix
  Low: 0

Outdated packages: 12
Potentially unused: 3
License issues: 2
```

### Vulnerability Details

```
requests@2.25.0
  [CRITICAL] CVE-2023-32681
  Proxy-Authorization header leak...
  Fix: Upgrade to 2.31.0
  CVSS: 9.1
```

### Exit Codes

- `0` - Success, no critical/high vulnerabilities
- `1` - High severity vulnerabilities found
- `2` - Critical vulnerabilities found
- `130` - Interrupted by user (Ctrl+C)

## Common Use Cases

### 1. Pre-Commit Check

```bash
#!/bin/bash
# .git/hooks/pre-commit

python -m api.services.deps.cli scan . --severity critical
exit_code=$?

if [ $exit_code -eq 2 ]; then
    echo "❌ Critical vulnerabilities found! Commit blocked."
    exit 1
fi
```

### 2. CI/CD Integration

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Scan dependencies
        run: |
          python -m api.services.deps.cli scan . --severity high
          python -m api.services.deps.cli export . --format json --output results.json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: scan-results
          path: results.json
```

### 3. Weekly Report

```bash
#!/bin/bash
# weekly-scan.sh

DATE=$(date +%Y-%m-%d)
REPORT_DIR="security-reports/$DATE"
mkdir -p "$REPORT_DIR"

# Run scan
python -m api.services.deps.cli export . \
    --format text \
    --output "$REPORT_DIR/report.txt"

python -m api.services.deps.cli export . \
    --format json \
    --output "$REPORT_DIR/data.json"

echo "Report saved to $REPORT_DIR"
```

### 4. Python Script

```python
import asyncio
from api.services.deps import DependencyScanner, Severity

async def security_check():
    scanner = DependencyScanner()

    try:
        result = await scanner.scan_project(".")

        # Check for critical issues
        critical_deps = [
            dep for dep in result.dependencies
            if dep.highest_severity == Severity.CRITICAL
        ]

        if critical_deps:
            print("🚨 CRITICAL SECURITY ISSUES FOUND!")
            for dep in critical_deps:
                print(f"\n{dep.name}@{dep.version}")
                for vuln in dep.vulnerabilities:
                    if vuln.severity == Severity.CRITICAL:
                        print(f"  {vuln.cve_id}: {vuln.description[:100]}")
                        print(f"  Fix: Upgrade to {vuln.fix_version}")
            return False
        else:
            print("✓ No critical vulnerabilities found")
            return True

    finally:
        await scanner.close()

# Run
if asyncio.run(security_check()):
    print("Security check passed!")
else:
    print("Security check failed!")
    exit(1)
```

## Tips & Tricks

### 1. Speed Up Scans

The scanner uses a 24-hour cache. First scan is slower, subsequent scans are fast:

```bash
# First scan: ~60 seconds
python -m api.services.deps.cli scan .

# Second scan: ~10 seconds (cached)
python -m api.services.deps.cli scan .
```

### 2. Clear Cache

```bash
rm -rf ~/.magnetar/vuln_cache/
```

### 3. Focus on What Matters

```bash
# Only show packages with issues
python -m api.services.deps.cli scan . --severity critical --show-outdated
```

### 4. Export for Analysis

```bash
# Export JSON for custom analysis
python -m api.services.deps.cli export . --format json | jq '.statistics'
```

### 5. Check Before Upgrade

```bash
# Before upgrading dependencies
python -m api.services.deps.cli scan . --show-outdated
```

## Troubleshooting

### No vulnerabilities found (but expected)

1. Check internet connection
2. Verify package names are correct
3. Try clearing cache: `rm -rf ~/.magnetar/vuln_cache/`

### Scan is slow

1. First scan is always slower (building cache)
2. Use `--no-cache` to disable if needed
3. Check internet connection speed

### False positives for unused

The unused detection is heuristic-based. Verify manually:

```bash
# Check if package is really used
grep -r "import package_name" .
```

## Next Steps

- Read the [full README](README.md) for detailed API documentation
- Check [examples](example_usage.py) for more use cases
- Run [tests](test_scanner.py) to verify installation
- See [implementation summary](IMPLEMENTATION_SUMMARY.md) for architecture

## Support

For issues or questions:
1. Check the [README](README.md)
2. Review [example_usage.py](example_usage.py)
3. Run with `--help`: `python -m api.services.deps.cli --help`

## Quick Reference

```bash
# Essential commands
python -m api.services.deps.cli scan .
python -m api.services.deps.cli scan . --severity critical
python -m api.services.deps.cli export . --format json
python -m api.services.deps.cli stats .

# Get help
python -m api.services.deps.cli --help
python -m api.services.deps.cli scan --help
```

Happy scanning! 🔍
