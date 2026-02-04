# Code Health Dashboard - Quick Start Guide

## Installation

No additional installation required! The system uses only dependencies already in MagnetarCode's `requirements.txt`.

Optional tools for enhanced functionality:
```bash
# For vulnerability scanning
pip install pip-audit

# Test coverage (already installed)
pip install pytest pytest-cov
```

## 5-Minute Quick Start

### 1. Run Your First Analysis (CLI)

```bash
cd /Users/indiedevhipps/Documents/MagnetarCode/apps/backend

# Analyze the entire backend
python -m api.services.health.cli analyze

# Or analyze with JSON output
python -m api.services.health.cli analyze --format json > health_report.json
```

### 2. Check Technical Debt

```bash
# Show top 10 technical debt items
python -m api.services.health.cli debt --top 10
```

### 3. Analyze a Specific File

```bash
# Analyze a single file
python -m api.services.health.cli file api/services/agent_executor.py
```

### 4. Find Code Duplicates

```bash
# Find duplicate code blocks
python -m api.services.health.cli duplicates --top 10
```

### 5. Track Trends Over Time

```bash
# After running analysis a few times, check trends
python -m api.services.health.cli trends --days 30
```

## Python API Quick Start

### Basic Analysis

```python
import asyncio
from api.services.health import HealthDashboard

async def main():
    # Initialize dashboard
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    # Run analysis
    print("Analyzing project...")
    health = await dashboard.analyze_project()

    # Print report
    print(dashboard.generate_report(health, format='text'))

asyncio.run(main())
```

### Analyze Single File

```python
from pathlib import Path
from api.services.health import HealthDashboard

dashboard = HealthDashboard(
    project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
)

file_path = Path("api/services/agent_executor.py")
health = dashboard.analyze_file(file_path)

print(f"Status: {health.status.value}")
print(f"Complexity: {health.avg_complexity:.2f}")
print(f"Maintainability: {health.maintainability_index:.2f}")
```

### Get Technical Debt Items

```python
import asyncio
from api.services.health import HealthDashboard

async def show_debt():
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    health = await dashboard.analyze_project()

    # Sort by estimated hours
    top_debt = sorted(
        health.tech_debt_items,
        key=lambda x: x.estimated_hours,
        reverse=True
    )[:5]

    print("Top 5 Technical Debt Items:")
    for i, item in enumerate(top_debt, 1):
        print(f"{i}. {item.description}")
        print(f"   Hours: {item.estimated_hours:.1f}")

asyncio.run(show_debt())
```

## Understanding the Output

### Health Status Levels

- **GOOD** (✓) - Meets or exceeds quality thresholds
- **WARNING** (⚠) - Below recommended thresholds, needs attention
- **CRITICAL** (✗) - Significantly below thresholds, requires immediate action

### Metrics Explained

| Metric | Description | Good | Warning | Critical |
|--------|-------------|------|---------|----------|
| **Cyclomatic Complexity** | Number of independent paths through code | ≤10 | 10-15 | >15 |
| **Maintainability Index** | Overall maintainability score (0-100) | ≥70 | 50-70 | <50 |
| **Test Coverage** | Percentage of code covered by tests | ≥80% | 60-80% | <60% |
| **Documentation Coverage** | Percentage of functions with docstrings | ≥75% | 50-75% | <50% |
| **Code Duplication** | Percentage of duplicated code | ≤3% | 3-5% | >5% |

### Trend Indicators

- **IMPROVING** - Metric is getting better over time
- **STABLE** - Metric is relatively unchanged
- **DEGRADING** - Metric is getting worse over time
- **UNKNOWN** - Not enough historical data

## Sample Report

```
================================================================================
                           CODE HEALTH REPORT
================================================================================
Generated: 2024-12-20 15:30:00
Overall Status: WARNING

SUMMARY
--------------------------------------------------------------------------------
Total Files:      45
Total Lines:      15,234
Code Lines:       10,892
Total Functions:  234
High Complexity:  12

QUALITY METRICS
--------------------------------------------------------------------------------
Avg Complexity:         8.5 (stable)
Maintainability Index:  68.3 (improving)
Test Coverage:          62.5% (stable)
Documentation Coverage: 71.2%
Code Duplication:       4.3%

TECHNICAL DEBT
--------------------------------------------------------------------------------
Total Estimated Hours: 45.5 (degrading)
Total Issues:          28

Top 5 Issues:
  1. [CRITICAL] High complexity in function 'process_request' (CC: 28)
     api/services/agent_executor.py:145 (12.5h)
  2. [WARNING] Low test coverage (45.0%)
     api/services/cache_service.py:1 (8.2h)
  3. [WARNING] Missing documentation for 15 functions
     api/services/file_operations.py:1 (3.8h)
```

## Common Use Cases

### 1. Pre-commit Check
```bash
# Add to .git/hooks/pre-commit
python -m api.services.health.cli analyze --format json | \
  python -c "import sys, json; sys.exit(1 if json.load(sys.stdin)['overall_status'] == 'critical' else 0)"
```

### 2. Daily Health Check
```bash
# Add to crontab
0 9 * * * cd /path/to/MagnetarCode/apps/backend && \
  python -m api.services.health.cli analyze > /tmp/health_$(date +\%Y\%m\%d).txt
```

### 3. PR Comment
```bash
# In CI/CD pipeline
python -m api.services.health.cli analyze --format markdown > health_report.md
# Post health_report.md as PR comment
```

### 4. Find Refactoring Targets
```bash
# Find files with highest complexity
python -m api.services.health.cli analyze --format json | \
  python -c "
import json, sys
data = json.load(sys.stdin)
print('Files needing refactoring:')
# Parse and display high-complexity files
"
```

## Next Steps

1. **Read the full documentation:** `README.md`
2. **See integration examples:** `INTEGRATION.md`
3. **Review code examples:** `example_usage.py`
4. **Run the tests:** `pytest test_health.py -v`
5. **Customize thresholds:** See `HealthThresholds` in `metrics.py`

## Troubleshooting

### "No test coverage data"
```bash
# Run tests with coverage first
cd /Users/indiedevhipps/Documents/MagnetarCode/apps/backend
pytest --cov=api --cov-report=json
```

### "Database locked"
```bash
# Remove lock file
rm /Users/indiedevhipps/Documents/MagnetarCode/apps/backend/.health_metrics.db-journal
```

### "Analysis too slow"
```python
# Exclude more directories
dashboard = HealthDashboard(
    project_root="...",
    exclude_patterns=['*/venv/*', '*/tests/*', '*/migrations/*']
)
```

## Tips

1. **Start with low thresholds** and gradually increase them
2. **Focus on high-hour debt items** for maximum impact
3. **Track trends over weeks** for meaningful insights
4. **Run analysis regularly** (daily or weekly)
5. **Integrate with CI/CD** to prevent quality regression

## Support

- **Issues?** Check the logs for detailed error messages
- **Questions?** See `README.md` for comprehensive documentation
- **Examples?** Review `example_usage.py` for patterns
- **Integration?** See `INTEGRATION.md` for guides

## Summary

The Code Health Dashboard helps you:
- 📊 **Track** code quality metrics
- 🔍 **Identify** technical debt
- 📈 **Monitor** trends over time
- 🎯 **Prioritize** refactoring efforts
- ✅ **Maintain** high code quality

Start with `python -m api.services.health.cli analyze` and explore from there!
