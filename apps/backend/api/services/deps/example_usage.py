"""
Example usage of the Dependency Scanner

This file demonstrates how to use the dependency scanner service
to analyze project dependencies for vulnerabilities, outdated packages,
license issues, and unused dependencies.
"""

import asyncio
from pathlib import Path

from .scanner import DependencyScanner, quick_scan


async def example_full_scan():
    """Example: Full project scan with all features"""
    print("=" * 80)
    print("EXAMPLE: Full Project Scan")
    print("=" * 80)

    # Initialize scanner
    scanner = DependencyScanner()

    try:
        # Scan the MagnetarCode backend
        project_path = Path(__file__).parent.parent.parent.parent.parent
        print(f"\nScanning project: {project_path}")

        result = await scanner.scan_project(project_path)

        # Print summary
        print(f"\nFound {len(result.dependencies)} dependencies")
        print(f"Ecosystems scanned: {', '.join(result.ecosystems_scanned)}")
        print(f"Total vulnerabilities: {result.total_vulnerabilities}")
        print(f"  - Critical: {result.critical_count}")
        print(f"  - High: {result.high_count}")
        print(f"  - Medium: {result.medium_count}")
        print(f"  - Low: {result.low_count}")
        print(f"Outdated packages: {result.outdated_count}")
        print(f"License issues: {len(result.license_issues)}")

        # Generate and print report
        print("\n" + scanner.generate_report(result))

        # Generate tree visualization
        print("\n" + scanner.generate_tree_visualization(result.dependencies))

        # Export to JSON
        import json

        output_file = project_path / "dependency_scan_results.json"
        with open(output_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nFull results exported to: {output_file}")

    finally:
        await scanner.close()


async def example_quick_scan():
    """Example: Quick scan using convenience function"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Quick Scan")
    print("=" * 80)

    project_path = Path(__file__).parent.parent.parent.parent.parent
    result = await quick_scan(project_path)

    print(f"\nQuick scan complete!")
    print(f"Dependencies: {len(result.dependencies)}")
    print(f"Vulnerabilities: {result.total_vulnerabilities}")


async def example_vulnerability_check():
    """Example: Check specific dependencies for vulnerabilities"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Vulnerability Check for Specific Dependencies")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        from .scanner import Dependency

        # Create test dependencies
        test_deps = [
            Dependency(name="requests", version="2.25.0", ecosystem="pypi"),
            Dependency(name="django", version="3.1.0", ecosystem="pypi"),
            Dependency(name="express", version="4.17.0", ecosystem="npm"),
        ]

        print("\nChecking vulnerabilities for:")
        for dep in test_deps:
            print(f"  - {dep.name}@{dep.version}")

        await scanner.check_vulnerabilities(test_deps)

        print("\nResults:")
        for dep in test_deps:
            if dep.has_vulnerabilities:
                print(f"\n{dep.name}@{dep.version}: {len(dep.vulnerabilities)} vulnerabilities")
                for vuln in dep.vulnerabilities:
                    print(f"  [{vuln.severity.value}] {vuln.cve_id}")
                    print(f"  {vuln.description[:100]}...")
                    if vuln.fix_version:
                        print(f"  Fix: Upgrade to {vuln.fix_version}")
            else:
                print(f"\n{dep.name}@{dep.version}: No vulnerabilities found")

    finally:
        await scanner.close()


async def example_outdated_check():
    """Example: Check for outdated packages"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Outdated Package Check")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        from .scanner import Dependency

        # Create test dependencies
        test_deps = [
            Dependency(name="fastapi", version="0.100.0", ecosystem="pypi"),
            Dependency(name="uvicorn", version="0.20.0", ecosystem="pypi"),
            Dependency(name="react", version="17.0.0", ecosystem="npm"),
        ]

        print("\nChecking latest versions for:")
        for dep in test_deps:
            print(f"  - {dep.name}@{dep.version}")

        await scanner.check_outdated(test_deps)

        print("\nResults:")
        for dep in test_deps:
            if dep.is_outdated:
                print(f"{dep.name}: {dep.version} -> {dep.latest_version} (OUTDATED)")
            else:
                status = f"up-to-date ({dep.latest_version})" if dep.latest_version else "version check failed"
                print(f"{dep.name}: {dep.version} ({status})")

    finally:
        await scanner.close()


async def example_license_check():
    """Example: Check license compliance"""
    print("\n" + "=" * 80)
    print("EXAMPLE: License Compliance Check")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        from .scanner import Dependency

        # Create test dependencies
        test_deps = [
            Dependency(name="requests", version="2.31.0", ecosystem="pypi"),
            Dependency(name="pyjwt", version="2.8.0", ecosystem="pypi"),
            Dependency(name="numpy", version="1.24.0", ecosystem="pypi"),
        ]

        print("\nChecking licenses for:")
        for dep in test_deps:
            print(f"  - {dep.name}@{dep.version}")

        license_issues = await scanner.check_licenses(test_deps)

        print("\nLicense Information:")
        for dep in test_deps:
            print(f"{dep.name}: {dep.license or 'UNKNOWN'} ({dep.license_type.value})")

        if license_issues:
            print("\nLicense Issues:")
            for issue in license_issues:
                print(f"[{issue.severity.upper()}] {issue.dependency_name}: {issue.details}")
        else:
            print("\nNo license issues found!")

    finally:
        await scanner.close()


async def example_python_only_scan():
    """Example: Scan only Python dependencies"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Python-Only Scan")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        project_path = Path(__file__).parent.parent.parent.parent.parent
        print(f"\nScanning Python dependencies in: {project_path}")

        # Scan only Python dependencies
        python_deps = await scanner.scan_python_deps(project_path)

        print(f"\nFound {len(python_deps)} Python dependencies")

        # Check for vulnerabilities
        await scanner.check_vulnerabilities(python_deps)

        # Print vulnerable packages
        vulnerable = [dep for dep in python_deps if dep.has_vulnerabilities]
        if vulnerable:
            print(f"\nVulnerable packages ({len(vulnerable)}):")
            for dep in vulnerable:
                print(f"  {dep.name}@{dep.version}: {len(dep.vulnerabilities)} vulnerabilities")
        else:
            print("\nNo vulnerabilities found!")

    finally:
        await scanner.close()


async def example_export_formats():
    """Example: Export scan results in different formats"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Export Scan Results")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        project_path = Path(__file__).parent.parent.parent.parent.parent
        result = await scanner.scan_project(project_path)

        # Export as JSON
        import json

        json_output = result.to_dict()
        print("\nJSON Export (sample):")
        print(json.dumps(json_output["statistics"], indent=2))

        # Export as human-readable report
        report = scanner.generate_report(result)
        print("\nHuman-Readable Report:")
        print(report[:500] + "...\n")

        # Export as tree visualization
        tree = scanner.generate_tree_visualization(result.dependencies)
        print("\nTree Visualization (sample):")
        print("\n".join(tree.split("\n")[:20]) + "\n...")

        # Save to files
        output_dir = project_path / "scan_reports"
        output_dir.mkdir(exist_ok=True)

        with open(output_dir / "scan_results.json", "w") as f:
            json.dump(json_output, f, indent=2)

        with open(output_dir / "scan_report.txt", "w") as f:
            f.write(report)

        with open(output_dir / "dependency_tree.txt", "w") as f:
            f.write(tree)

        print(f"\nResults saved to: {output_dir}")

    finally:
        await scanner.close()


async def example_vulnerability_filtering():
    """Example: Filter and analyze vulnerabilities by severity"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Vulnerability Filtering and Analysis")
    print("=" * 80)

    scanner = DependencyScanner()

    try:
        project_path = Path(__file__).parent.parent.parent.parent.parent
        result = await scanner.scan_project(project_path)

        from .scanner import Severity

        # Filter by severity
        critical_deps = [dep for dep in result.dependencies if dep.highest_severity == Severity.CRITICAL]

        high_deps = [dep for dep in result.dependencies if dep.highest_severity == Severity.HIGH]

        medium_deps = [dep for dep in result.dependencies if dep.highest_severity == Severity.MEDIUM]

        print(f"\nVulnerability Distribution:")
        print(f"  Critical: {len(critical_deps)} packages")
        print(f"  High: {len(high_deps)} packages")
        print(f"  Medium: {len(medium_deps)} packages")

        # Show critical vulnerabilities with remediation
        if critical_deps:
            print("\nCRITICAL VULNERABILITIES - IMMEDIATE ACTION REQUIRED:")
            for dep in critical_deps:
                print(f"\n{dep.name}@{dep.version}")
                for vuln in dep.vulnerabilities:
                    if vuln.severity == Severity.CRITICAL:
                        print(f"  CVE: {vuln.cve_id}")
                        print(f"  CVSS: {vuln.cvss_score or 'N/A'}")
                        print(f"  Fix: {vuln.fix_version or 'No fix available yet'}")
                        if vuln.references:
                            print(f"  Reference: {vuln.references[0]}")

    finally:
        await scanner.close()


async def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("DEPENDENCY SCANNER - USAGE EXAMPLES")
    print("=" * 80)

    # Run examples
    await example_quick_scan()
    await example_vulnerability_check()
    await example_outdated_check()
    await example_license_check()
    await example_python_only_scan()

    # Uncomment to run full scan (takes longer)
    # await example_full_scan()
    # await example_export_formats()
    # await example_vulnerability_filtering()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
