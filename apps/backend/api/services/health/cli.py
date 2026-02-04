#!/usr/bin/env python3
"""
Command-line interface for Code Health Dashboard

Usage:
    python cli.py analyze [--project-root PATH] [--format text|markdown|json]
    python cli.py trends [--days 30]
    python cli.py debt [--top 10]
    python cli.py file <file_path>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from api.services.health import HealthDashboard, HealthThresholds


async def analyze_command(args):
    """Run full project analysis"""
    project_root = args.project_root or Path.cwd()

    print(f"Analyzing project: {project_root}")
    print("This may take a few moments...\n")

    dashboard = HealthDashboard(project_root=str(project_root))
    health = await dashboard.analyze_project()

    report = dashboard.generate_report(health, format=args.format)
    print(report)

    # Exit with error code if critical
    if health.overall_status.value == 'critical':
        return 1
    return 0


async def trends_command(args):
    """Show health trends"""
    project_root = args.project_root or Path.cwd()

    dashboard = HealthDashboard(project_root=str(project_root))
    trends = dashboard.get_trends(lookback_days=args.days)

    print(f"Health Trends (last {args.days} days)")
    print("=" * 60)
    print(f"Complexity:      {trends['complexity'].value}")
    print(f"Maintainability: {trends['maintainability'].value}")
    print(f"Coverage:        {trends['coverage'].value}")
    print(f"Technical Debt:  {trends['tech_debt'].value}")

    return 0


async def debt_command(args):
    """Show technical debt items"""
    project_root = args.project_root or Path.cwd()

    print(f"Analyzing technical debt in: {project_root}\n")

    dashboard = HealthDashboard(project_root=str(project_root))
    health = await dashboard.analyze_project()

    # Sort by hours
    debt_items = sorted(
        health.tech_debt_items,
        key=lambda x: x.estimated_hours,
        reverse=True
    )[:args.top]

    print(f"Top {len(debt_items)} Technical Debt Items")
    print("=" * 80)
    print(f"Total debt: {health.total_tech_debt_hours:.1f} hours\n")

    for i, item in enumerate(debt_items, 1):
        print(f"{i}. [{item.severity.value.upper()}] {item.category.upper()}")
        print(f"   {item.description}")
        print(f"   Location: {item.file_path}:{item.line_number}")
        print(f"   Estimated: {item.estimated_hours:.1f} hours")
        print()

    # Summary by category
    by_category = {}
    for item in health.tech_debt_items:
        if item.category not in by_category:
            by_category[item.category] = {'count': 0, 'hours': 0.0}
        by_category[item.category]['count'] += 1
        by_category[item.category]['hours'] += item.estimated_hours

    print("Debt by Category:")
    print("-" * 80)
    for category in sorted(by_category.keys()):
        data = by_category[category]
        print(f"{category.title():15} {data['count']:3} items  {data['hours']:6.1f} hours")

    return 0


async def file_command(args):
    """Analyze a single file"""
    file_path = Path(args.file_path)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    # Determine project root (look for .git or use parent)
    project_root = file_path.parent
    while project_root.parent != project_root:
        if (project_root / '.git').exists():
            break
        project_root = project_root.parent

    dashboard = HealthDashboard(project_root=str(project_root))
    file_health = dashboard.analyze_file(file_path)

    if not file_health:
        print(f"Error: Failed to analyze file", file=sys.stderr)
        return 1

    print(f"File Health Report: {file_path.name}")
    print("=" * 80)
    print(f"Status:           {file_health.status.value.upper()}")
    print(f"Total Lines:      {file_health.total_lines}")
    print(f"Code Lines:       {file_health.code_lines}")
    print(f"Comment Lines:    {file_health.comment_lines}")
    print(f"Functions:        {file_health.function_count}")
    print()
    print(f"Avg Complexity:   {file_health.avg_complexity:.2f}")
    print(f"Max Complexity:   {file_health.max_complexity}")
    print(f"Maintainability:  {file_health.maintainability_index:.2f}")
    print(f"Documentation:    {file_health.documentation_coverage:.1f}%")
    print()

    if file_health.functions:
        print("Functions (sorted by complexity):")
        print("-" * 80)
        sorted_funcs = sorted(
            file_health.functions,
            key=lambda f: f.cyclomatic_complexity,
            reverse=True
        )

        for func in sorted_funcs[:10]:
            status_icon = "✓" if func.cyclomatic_complexity <= 10 else ("⚠" if func.cyclomatic_complexity <= 15 else "✗")
            doc_icon = "✓" if func.has_docstring else "✗"
            print(f"  {status_icon} {func.name:30} CC={func.cyclomatic_complexity:2}  LOC={func.lines_of_code:3}  DOC={doc_icon}")

    return 0


async def duplicates_command(args):
    """Find code duplicates"""
    project_root = args.project_root or Path.cwd()

    print(f"Scanning for duplicates in: {project_root}\n")

    dashboard = HealthDashboard(project_root=str(project_root))
    health = await dashboard.analyze_project()

    print(f"Duplication Analysis")
    print("=" * 80)
    print(f"Total duplicate blocks: {len(health.duplicate_blocks)}")
    print(f"Duplication percentage: {health.duplication_percentage:.2f}%")
    print()

    if health.duplicate_blocks:
        worst = sorted(
            health.duplicate_blocks,
            key=lambda b: b.duplication_count * len(b.lines),
            reverse=True
        )[:args.top]

        print(f"Top {len(worst)} Duplicate Blocks:")
        print("-" * 80)

        for i, block in enumerate(worst, 1):
            print(f"\n{i}. Duplicated {block.duplication_count} times ({len(block.lines)} lines)")
            print(f"   Estimated refactoring: {block.estimated_hours:.1f} hours")
            print(f"   Locations:")
            for file_path, line_num in block.occurrences[:5]:
                print(f"     - {file_path}:{line_num}")
            if len(block.occurrences) > 5:
                print(f"     ... and {len(block.occurrences) - 5} more")

    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Code Health Dashboard - Monitor code quality and technical debt',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Run full project analysis')
    analyze_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)',
    )
    analyze_parser.add_argument(
        '--format',
        choices=['text', 'markdown', 'json'],
        default='text',
        help='Report format (default: text)',
    )

    # Trends command
    trends_parser = subparsers.add_parser('trends', help='Show health trends')
    trends_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)',
    )
    trends_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)',
    )

    # Debt command
    debt_parser = subparsers.add_parser('debt', help='Show technical debt items')
    debt_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)',
    )
    debt_parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Number of top items to show (default: 10)',
    )

    # File command
    file_parser = subparsers.add_parser('file', help='Analyze a single file')
    file_parser.add_argument(
        'file_path',
        type=str,
        help='Path to file to analyze',
    )

    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find code duplicates')
    dup_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)',
    )
    dup_parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Number of top duplicates to show (default: 10)',
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run appropriate command
    commands = {
        'analyze': analyze_command,
        'trends': trends_command,
        'debt': debt_command,
        'file': file_command,
        'duplicates': duplicates_command,
    }

    try:
        exit_code = asyncio.run(commands[args.command](args))
        return exit_code
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
