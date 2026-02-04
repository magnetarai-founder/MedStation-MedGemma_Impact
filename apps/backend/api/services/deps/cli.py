#!/usr/bin/env python3
"""
Dependency Scanner CLI

Command-line interface for the dependency scanner.

Usage:
    python -m api.services.deps.cli scan /path/to/project
    python -m api.services.deps.cli check-vuln --package requests --version 2.28.0 --ecosystem pypi
    python -m api.services.deps.cli export /path/to/project --format json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .scanner import Dependency, DependencyScanner, Severity, quick_scan


def setup_parser() -> argparse.ArgumentParser:
    """Set up CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Dependency Scanner - Multi-language vulnerability and compliance scanning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory
  %(prog)s scan .

  # Scan specific project
  %(prog)s scan /path/to/project

  # Export results as JSON
  %(prog)s export /path/to/project --format json --output results.json

  # Check specific package
  %(prog)s check-vuln --package requests --version 2.28.0 --ecosystem pypi

  # Show only critical vulnerabilities
  %(prog)s scan . --severity critical

  # Show outdated packages
  %(prog)s scan . --show-outdated
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan project for dependencies and vulnerabilities")
    scan_parser.add_argument("path", type=str, help="Path to project directory")
    scan_parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        help="Filter vulnerabilities by minimum severity",
    )
    scan_parser.add_argument("--show-outdated", action="store_true", help="Show outdated packages")
    scan_parser.add_argument("--show-unused", action="store_true", help="Show unused packages")
    scan_parser.add_argument("--show-licenses", action="store_true", help="Show license issues")
    scan_parser.add_argument("--tree", action="store_true", help="Show dependency tree")
    scan_parser.add_argument("--no-cache", action="store_true", help="Disable vulnerability cache")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export scan results")
    export_parser.add_argument("path", type=str, help="Path to project directory")
    export_parser.add_argument(
        "--format",
        choices=["json", "text", "tree"],
        default="json",
        help="Output format",
    )
    export_parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")

    # Check vulnerability command
    check_parser = subparsers.add_parser("check-vuln", help="Check specific package for vulnerabilities")
    check_parser.add_argument("--package", "-p", required=True, help="Package name")
    check_parser.add_argument("--version", "-v", required=True, help="Package version")
    check_parser.add_argument(
        "--ecosystem",
        "-e",
        required=True,
        choices=["pypi", "npm", "cargo", "go"],
        help="Package ecosystem",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List dependencies without vulnerability check")
    list_parser.add_argument("path", type=str, help="Path to project directory")
    list_parser.add_argument(
        "--ecosystem",
        choices=["pypi", "npm", "cargo", "go", "all"],
        default="all",
        help="Filter by ecosystem",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show project dependency statistics")
    stats_parser.add_argument("path", type=str, help="Path to project directory")

    return parser


async def cmd_scan(args):
    """Run scan command"""
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    print(f"Scanning project: {project_path}")
    print("This may take a few minutes...\n")

    # Create scanner
    cache_dir = None if args.no_cache else None  # Use default cache
    scanner = DependencyScanner(cache_dir=cache_dir)

    try:
        # Scan project
        result = await scanner.scan_project(project_path)

        # Filter by severity if specified
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }

        filtered_deps = result.dependencies
        if args.severity:
            min_severity = severity_map[args.severity]
            severity_order = {
                Severity.CRITICAL: 4,
                Severity.HIGH: 3,
                Severity.MEDIUM: 2,
                Severity.LOW: 1,
                Severity.UNKNOWN: 0,
            }
            min_level = severity_order[min_severity]
            filtered_deps = [dep for dep in result.dependencies if severity_order[dep.highest_severity] >= min_level]

        # Print results
        print("=" * 80)
        print("SCAN RESULTS")
        print("=" * 80)
        print(f"Dependencies found: {len(result.dependencies)}")
        print(f"Ecosystems: {', '.join(result.ecosystems_scanned)}")
        print(f"Total vulnerabilities: {result.total_vulnerabilities}")
        print(f"  Critical: {result.critical_count}")
        print(f"  High: {result.high_count}")
        print(f"  Medium: {result.medium_count}")
        print(f"  Low: {result.low_count}")

        if args.show_outdated:
            print(f"\nOutdated packages: {result.outdated_count}")

        if args.show_unused:
            print(f"Potentially unused: {result.unused_count}")

        if args.show_licenses:
            print(f"License issues: {len(result.license_issues)}")

        # Show vulnerabilities
        if filtered_deps and any(dep.has_vulnerabilities for dep in filtered_deps):
            print("\n" + "=" * 80)
            print("VULNERABILITIES")
            print("=" * 80)

            for dep in filtered_deps:
                if not dep.has_vulnerabilities:
                    continue

                print(f"\n{dep.name}@{dep.version}")
                for vuln in dep.vulnerabilities:
                    if args.severity and severity_order[vuln.severity] < min_level:
                        continue

                    print(f"  [{vuln.severity.value}] {vuln.cve_id}")
                    print(f"  {vuln.description[:100]}...")
                    if vuln.fix_version:
                        print(f"  Fix: Upgrade to {vuln.fix_version}")
                    if vuln.cvss_score:
                        print(f"  CVSS: {vuln.cvss_score}")

        # Show outdated
        if args.show_outdated:
            outdated = [dep for dep in result.dependencies if dep.is_outdated]
            if outdated:
                print("\n" + "=" * 80)
                print("OUTDATED PACKAGES")
                print("=" * 80)
                for dep in outdated[:20]:
                    print(f"{dep.name}: {dep.version} -> {dep.latest_version}")
                if len(outdated) > 20:
                    print(f"... and {len(outdated) - 20} more")

        # Show unused
        if args.show_unused:
            unused = [dep for dep in result.dependencies if dep.is_unused]
            if unused:
                print("\n" + "=" * 80)
                print("POTENTIALLY UNUSED PACKAGES")
                print("=" * 80)
                for dep in unused[:20]:
                    print(f"{dep.name}@{dep.version}")
                if len(unused) > 20:
                    print(f"... and {len(unused) - 20} more")

        # Show licenses
        if args.show_licenses and result.license_issues:
            print("\n" + "=" * 80)
            print("LICENSE ISSUES")
            print("=" * 80)
            for issue in result.license_issues[:20]:
                print(f"[{issue.severity.upper()}] {issue.dependency_name}: {issue.details}")

        # Show tree
        if args.tree:
            print("\n" + scanner.generate_tree_visualization(result.dependencies))

        # Return exit code based on vulnerabilities
        if result.critical_count > 0:
            return 2  # Critical vulnerabilities found
        elif result.high_count > 0:
            return 1  # High vulnerabilities found
        else:
            return 0  # No critical/high vulnerabilities

    finally:
        await scanner.close()


async def cmd_export(args):
    """Run export command"""
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    scanner = DependencyScanner()

    try:
        result = await scanner.scan_project(project_path)

        # Generate output based on format
        if args.format == "json":
            output = json.dumps(result.to_dict(), indent=2)
        elif args.format == "text":
            output = scanner.generate_report(result)
        elif args.format == "tree":
            output = scanner.generate_tree_visualization(result.dependencies)
        else:
            output = json.dumps(result.to_dict(), indent=2)

        # Write to file or stdout
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Results exported to: {args.output}")
        else:
            print(output)

        return 0

    finally:
        await scanner.close()


async def cmd_check_vuln(args):
    """Run check-vuln command"""
    print(f"Checking {args.package}@{args.version} ({args.ecosystem})...")

    scanner = DependencyScanner()

    try:
        dep = Dependency(name=args.package, version=args.version, ecosystem=args.ecosystem)

        await scanner.check_vulnerabilities([dep])

        if dep.has_vulnerabilities:
            print(f"\nFound {len(dep.vulnerabilities)} vulnerabilities:\n")
            for vuln in dep.vulnerabilities:
                print(f"[{vuln.severity.value}] {vuln.cve_id}")
                print(f"Description: {vuln.description}")
                if vuln.fix_version:
                    print(f"Fix: Upgrade to {vuln.fix_version}")
                if vuln.cvss_score:
                    print(f"CVSS: {vuln.cvss_score}")
                if vuln.references:
                    print(f"References: {vuln.references[0]}")
                print()

            # Return exit code based on severity
            if dep.highest_severity == Severity.CRITICAL:
                return 2
            elif dep.highest_severity == Severity.HIGH:
                return 1
            else:
                return 0
        else:
            print("No vulnerabilities found!")
            return 0

    finally:
        await scanner.close()


async def cmd_list(args):
    """Run list command"""
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    scanner = DependencyScanner()

    try:
        # Scan based on ecosystem
        all_deps = []

        if args.ecosystem in ("all", "pypi"):
            deps = await scanner.scan_python_deps(project_path)
            all_deps.extend(deps)

        if args.ecosystem in ("all", "npm"):
            deps = await scanner.scan_npm_deps(project_path)
            all_deps.extend(deps)

        if args.ecosystem in ("all", "cargo"):
            deps = await scanner.scan_rust_deps(project_path)
            all_deps.extend(deps)

        if args.ecosystem in ("all", "go"):
            deps = await scanner.scan_go_deps(project_path)
            all_deps.extend(deps)

        # Group by ecosystem
        by_ecosystem = {}
        for dep in all_deps:
            by_ecosystem.setdefault(dep.ecosystem, []).append(dep)

        # Print results
        print(f"Dependencies in {project_path}:\n")
        for ecosystem, deps in sorted(by_ecosystem.items()):
            print(f"{ecosystem.upper()} ({len(deps)} packages):")
            for dep in sorted(deps, key=lambda d: d.name):
                print(f"  {dep.name}@{dep.version}")
            print()

        return 0

    finally:
        await scanner.close()


async def cmd_stats(args):
    """Run stats command"""
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    print(f"Analyzing {project_path}...\n")

    scanner = DependencyScanner()

    try:
        result = await scanner.scan_project(project_path)

        # Calculate additional stats
        by_ecosystem = {}
        for dep in result.dependencies:
            by_ecosystem.setdefault(dep.ecosystem, []).append(dep)

        vuln_by_severity = {
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
        }

        # Print stats
        print("=" * 80)
        print("DEPENDENCY STATISTICS")
        print("=" * 80)
        print(f"\nTotal Dependencies: {len(result.dependencies)}")
        print(f"\nBy Ecosystem:")
        for ecosystem, deps in sorted(by_ecosystem.items()):
            print(f"  {ecosystem}: {len(deps)}")

        print(f"\nVulnerabilities: {result.total_vulnerabilities}")
        for severity, count in vuln_by_severity.items():
            if count > 0:
                print(f"  {severity.capitalize()}: {count}")

        print(f"\nOutdated: {result.outdated_count}")
        print(f"Unused: {result.unused_count}")
        print(f"License Issues: {len(result.license_issues)}")

        # License breakdown
        by_license = {}
        for dep in result.dependencies:
            if dep.license:
                by_license.setdefault(dep.license_type.value, []).append(dep)

        if by_license:
            print(f"\nLicenses:")
            for license_type, deps in sorted(by_license.items()):
                print(f"  {license_type}: {len(deps)}")

        return 0

    finally:
        await scanner.close()


def main():
    """Main CLI entry point"""
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run command
    try:
        if args.command == "scan":
            exit_code = asyncio.run(cmd_scan(args))
        elif args.command == "export":
            exit_code = asyncio.run(cmd_export(args))
        elif args.command == "check-vuln":
            exit_code = asyncio.run(cmd_check_vuln(args))
        elif args.command == "list":
            exit_code = asyncio.run(cmd_list(args))
        elif args.command == "stats":
            exit_code = asyncio.run(cmd_stats(args))
        else:
            parser.print_help()
            exit_code = 1

        return exit_code

    except KeyboardInterrupt:
        print("\n\nScan interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
