"""
Example usage of the Code Health Dashboard

This demonstrates how to use the health monitoring system to:
1. Analyze project health
2. Track metrics over time
3. Generate reports
4. Monitor technical debt
"""

import asyncio
from pathlib import Path
from api.services.health import (
    HealthDashboard,
    HealthThresholds,
    get_health_dashboard,
)


async def basic_analysis():
    """Basic health analysis example"""
    # Initialize dashboard
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    # Run analysis
    print("Analyzing project health...")
    health = await dashboard.analyze_project()

    # Generate report
    print("\n" + "=" * 80)
    print(dashboard.generate_report(health, format='text'))
    print("\n" + "=" * 80)

    # Print key metrics
    print("\nKey Metrics:")
    print(f"  Overall Status: {health.overall_status.value}")
    print(f"  Average Complexity: {health.avg_complexity:.2f}")
    print(f"  Maintainability Index: {health.avg_maintainability:.2f}")
    print(f"  Test Coverage: {health.test_coverage:.1f}%")
    print(f"  Tech Debt: {health.total_tech_debt_hours:.1f} hours")


async def custom_thresholds():
    """Example with custom thresholds"""
    # Define stricter thresholds
    strict_thresholds = HealthThresholds(
        complexity_good=8,
        complexity_warning=12,
        complexity_critical=20,
        maintainability_good=80.0,
        coverage_good=90.0,
    )

    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend",
        thresholds=strict_thresholds,
    )

    health = await dashboard.analyze_project()
    print(dashboard.generate_report(health, format='markdown'))


async def monitor_specific_files():
    """Monitor health of specific files"""
    dashboard = get_health_dashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    # Analyze a single file
    file_path = Path("/Users/indiedevhipps/Documents/MagnetarCode/apps/backend/api/services/agent_executor.py")
    file_health = dashboard.analyze_file(file_path)

    if file_health:
        print(f"\nFile Health: {file_health.file_path}")
        print(f"  Status: {file_health.status.value}")
        print(f"  Average Complexity: {file_health.avg_complexity:.2f}")
        print(f"  Max Complexity: {file_health.max_complexity}")
        print(f"  Maintainability: {file_health.maintainability_index:.2f}")
        print(f"  Documentation Coverage: {file_health.documentation_coverage:.1f}%")
        print(f"\nFunctions:")
        for func in sorted(file_health.functions, key=lambda f: f.cyclomatic_complexity, reverse=True)[:5]:
            print(f"    {func.name}: CC={func.cyclomatic_complexity}, LOC={func.lines_of_code}")


async def track_trends():
    """Track health trends over time"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    # Run analysis (saves to database)
    health = await dashboard.analyze_project()

    # Get trends
    trends = dashboard.get_trends(lookback_days=30)

    print("\nHealth Trends (30 days):")
    print(f"  Complexity: {trends['complexity'].value}")
    print(f"  Maintainability: {trends['maintainability'].value}")
    print(f"  Coverage: {trends['coverage'].value}")
    print(f"  Technical Debt: {trends['tech_debt'].value}")


async def identify_tech_debt():
    """Identify and prioritize technical debt"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    health = await dashboard.analyze_project()

    # Sort by estimated hours (highest first)
    top_debt = sorted(
        health.tech_debt_items,
        key=lambda x: x.estimated_hours,
        reverse=True
    )[:10]

    print("\nTop 10 Technical Debt Items:")
    print("=" * 80)
    for i, item in enumerate(top_debt, 1):
        print(f"\n{i}. [{item.severity.value.upper()}] {item.category.upper()}")
        print(f"   {item.description}")
        print(f"   File: {item.file_path}:{item.line_number}")
        print(f"   Estimated hours: {item.estimated_hours:.1f}")

    # Group by category
    by_category = {}
    for item in health.tech_debt_items:
        by_category.setdefault(item.category, []).append(item)

    print("\n\nDebt by Category:")
    print("=" * 80)
    for category, items in sorted(by_category.items()):
        total_hours = sum(item.estimated_hours for item in items)
        print(f"{category.title()}: {len(items)} items, {total_hours:.1f} hours")


async def check_code_duplicates():
    """Find and analyze code duplicates"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    health = await dashboard.analyze_project()

    print(f"\nCode Duplication Analysis:")
    print(f"  Total duplicate blocks: {len(health.duplicate_blocks)}")
    print(f"  Duplication percentage: {health.duplication_percentage:.2f}%")

    # Show worst offenders
    worst_duplicates = sorted(
        health.duplicate_blocks,
        key=lambda b: b.duplication_count * len(b.lines),
        reverse=True
    )[:5]

    print("\nTop 5 Duplicate Blocks:")
    for i, block in enumerate(worst_duplicates, 1):
        print(f"\n{i}. Duplicated {block.duplication_count} times ({len(block.lines)} lines)")
        print(f"   Estimated refactoring time: {block.estimated_hours:.1f} hours")
        print(f"   Locations:")
        for file_path, line_num in block.occurrences[:3]:
            print(f"     - {file_path}:{line_num}")


async def generate_json_report():
    """Generate JSON report for CI/CD integration"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    health = await dashboard.analyze_project()

    # Generate JSON report
    json_report = dashboard.generate_report(health, format='json')

    # Save to file
    import json
    report_path = Path("/tmp/health_report.json")
    with open(report_path, 'w') as f:
        f.write(json_report)

    print(f"\nJSON report saved to: {report_path}")

    # Could be used in CI/CD to fail builds if health is critical
    data = json.loads(json_report)
    if data['overall_status'] == 'critical':
        print("WARNING: Project health is CRITICAL!")
        return False

    return True


async def main():
    """Run all examples"""
    print("1. Basic Analysis")
    print("-" * 80)
    await basic_analysis()

    print("\n\n2. Monitor Specific Files")
    print("-" * 80)
    await monitor_specific_files()

    print("\n\n3. Track Trends")
    print("-" * 80)
    await track_trends()

    print("\n\n4. Identify Technical Debt")
    print("-" * 80)
    await identify_tech_debt()

    print("\n\n5. Check Code Duplicates")
    print("-" * 80)
    await check_code_duplicates()


if __name__ == "__main__":
    # Run a single example
    asyncio.run(basic_analysis())

    # Or run all examples
    # asyncio.run(main())
