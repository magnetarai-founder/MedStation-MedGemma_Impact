#!/usr/bin/env python3
"""
Verification script for Code Health Dashboard installation

Run this to verify that the health dashboard is properly installed and working.
"""

import sys
import os
import tempfile
from pathlib import Path


def main():
    print("=" * 80)
    print("CODE HEALTH DASHBOARD - INSTALLATION VERIFICATION")
    print("=" * 80)
    print()

    # Test imports
    print("1. Testing imports...")
    try:
        from api.services.health import (
            HealthDashboard,
            HealthThresholds,
            CodeMetrics,
            FileHealth,
            ProjectHealth,
            TechDebtItem,
            DependencyIssue,
            DuplicateBlock,
            HealthStatus,
            TrendDirection,
            get_health_dashboard
        )
        print("   ✓ All imports successful")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False

    # Test dataclass creation
    print("\n2. Testing dataclass creation...")
    try:
        thresholds = HealthThresholds()
        print(f"   ✓ HealthThresholds: complexity_good={thresholds.complexity_good}")

        metrics = CodeMetrics(
            name="test_func",
            file_path="test.py",
            line_start=1,
            line_end=10,
            cyclomatic_complexity=5,
            cognitive_complexity=3,
            lines_of_code=10,
            num_parameters=2,
            num_returns=1,
            has_docstring=True
        )
        print(f"   ✓ CodeMetrics: {metrics.name}, CC={metrics.cyclomatic_complexity}")

    except Exception as e:
        print(f"   ✗ Dataclass creation failed: {e}")
        return False

    # Test dashboard initialization
    print("\n3. Testing dashboard initialization...")
    try:
        temp_dir = tempfile.mkdtemp()

        dashboard = HealthDashboard(
            project_root=temp_dir,
            thresholds=thresholds
        )
        print(f"   ✓ HealthDashboard initialized")
        print(f"   ✓ Database path: {dashboard.db_path}")
        print(f"   ✓ Database created: {dashboard.db_path.exists()}")

        # Cleanup
        db_path = dashboard.db_path
        if db_path.exists():
            os.remove(db_path)
        os.rmdir(temp_dir)

    except Exception as e:
        print(f"   ✗ Dashboard initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test enums
    print("\n4. Testing enums...")
    try:
        health_statuses = list(HealthStatus)
        trend_directions = list(TrendDirection)

        assert len(health_statuses) == 3, f"Expected 3 HealthStatus values, got {len(health_statuses)}"
        assert len(trend_directions) == 4, f"Expected 4 TrendDirection values, got {len(trend_directions)}"

        print(f"   ✓ HealthStatus: {[s.value for s in health_statuses]}")
        print(f"   ✓ TrendDirection: {[t.value for t in trend_directions]}")

    except Exception as e:
        print(f"   ✗ Enum validation failed: {e}")
        return False

    # Test basic analysis
    print("\n5. Testing basic analysis...")
    try:
        # Create a simple test file
        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text('''
def simple_function(x):
    """A simple function"""
    return x + 1

def complex_function(a, b, c):
    if a > 0:
        if b > 0:
            return a + b + c
    return 0
''')

        dashboard = HealthDashboard(project_root=temp_dir)

        # Analyze the file
        metrics = dashboard.calculate_complexity(test_file)
        print(f"   ✓ Analyzed test file: found {len(metrics)} functions")

        for m in metrics:
            print(f"     - {m.name}: CC={m.cyclomatic_complexity}, LOC={m.lines_of_code}")

        # Cleanup
        test_file.unlink()
        if dashboard.db_path.exists():
            os.remove(dashboard.db_path)
        os.rmdir(temp_dir)

    except Exception as e:
        print(f"   ✗ Basic analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test CLI availability
    print("\n6. Testing CLI availability...")
    try:
        cli_path = Path(__file__).parent / "cli.py"
        if cli_path.exists():
            print(f"   ✓ CLI script found: {cli_path}")
        else:
            print(f"   ✗ CLI script not found: {cli_path}")
            return False

    except Exception as e:
        print(f"   ✗ CLI check failed: {e}")
        return False

    # All tests passed
    print("\n" + "=" * 80)
    print("ALL VERIFICATION CHECKS PASSED!")
    print("=" * 80)
    print("\nThe Code Health Dashboard is properly installed and working.")
    print("\nQuick Start:")
    print("  1. Analyze your project:")
    print("     python -m api.services.health.cli analyze")
    print("\n  2. Check technical debt:")
    print("     python -m api.services.health.cli debt --top 10")
    print("\n  3. View trends:")
    print("     python -m api.services.health.cli trends")
    print("\nFor more information, see:")
    print("  - README.md for comprehensive documentation")
    print("  - QUICKSTART.md for quick start guide")
    print("  - INTEGRATION.md for integration examples")
    print("=" * 80)

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
