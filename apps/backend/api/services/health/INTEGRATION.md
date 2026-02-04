# Code Health Dashboard - Integration Guide

## Quick Start

The Code Health Dashboard is now available as a service in MagnetarCode. Here's how to use it:

### Basic Usage

```python
from api.services.health import HealthDashboard

# Initialize
dashboard = HealthDashboard(
    project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
)

# Run analysis
health = await dashboard.analyze_project()

# Generate report
print(dashboard.generate_report(health, format='text'))
```

### Command Line Interface

```bash
# From the backend directory
cd /Users/indiedevhipps/Documents/MagnetarCode/apps/backend

# Full analysis
python -m api.services.health.cli analyze

# Analyze with JSON output
python -m api.services.health.cli analyze --format json

# Show technical debt
python -m api.services.health.cli debt --top 20

# Show trends
python -m api.services.health.cli trends --days 30

# Analyze single file
python -m api.services.health.cli file api/services/agent_executor.py

# Find duplicates
python -m api.services.health.cli duplicates --top 10
```

## Integration with FastAPI

Add health endpoints to your FastAPI application:

```python
from fastapi import APIRouter
from api.services.health import HealthDashboard, ProjectHealth

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/analyze")
async def analyze_code_health():
    """Run code health analysis"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )
    health = await dashboard.analyze_project()

    return {
        "timestamp": health.timestamp.isoformat(),
        "overall_status": health.overall_status.value,
        "metrics": {
            "total_files": health.total_files,
            "avg_complexity": health.avg_complexity,
            "avg_maintainability": health.avg_maintainability,
            "test_coverage": health.test_coverage,
            "tech_debt_hours": health.total_tech_debt_hours,
        },
        "trends": {
            "complexity": health.complexity_trend.value,
            "maintainability": health.maintainability_trend.value,
            "coverage": health.coverage_trend.value,
        }
    }

@router.get("/debt")
async def get_technical_debt(limit: int = 10):
    """Get technical debt items"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )
    health = await dashboard.analyze_project()

    debt_items = sorted(
        health.tech_debt_items,
        key=lambda x: x.estimated_hours,
        reverse=True
    )[:limit]

    return {
        "total_debt_hours": health.total_tech_debt_hours,
        "items": [item.to_dict() for item in debt_items]
    }

@router.get("/file/{file_path:path}")
async def analyze_file(file_path: str):
    """Analyze a specific file"""
    from pathlib import Path

    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    full_path = Path("/Users/indiedevhipps/Documents/MagnetarCode/apps/backend") / file_path
    file_health = dashboard.analyze_file(full_path)

    if not file_health:
        return {"error": "Failed to analyze file"}

    return {
        "file_path": file_health.file_path,
        "status": file_health.status.value,
        "complexity": file_health.avg_complexity,
        "maintainability": file_health.maintainability_index,
        "documentation_coverage": file_health.documentation_coverage,
        "functions": [
            {
                "name": f.name,
                "complexity": f.cyclomatic_complexity,
                "loc": f.lines_of_code,
                "has_docstring": f.has_docstring,
            }
            for f in file_health.functions
        ]
    }
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Code Health Check

on: [push, pull_request]

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run health analysis
        run: |
          cd apps/backend
          python -m api.services.health.cli analyze --format json > health_report.json

      - name: Check health status
        run: |
          cd apps/backend
          # Fail if status is critical
          python -c "
          import json
          with open('health_report.json') as f:
              data = json.load(f)
          if data['overall_status'] == 'critical':
              print('❌ Code health is CRITICAL')
              exit(1)
          print('✅ Code health check passed')
          "

      - name: Upload health report
        uses: actions/upload-artifact@v3
        with:
          name: health-report
          path: apps/backend/health_report.json
```

## Scheduled Analysis

Run daily analysis and track trends:

```python
# scheduled_health_check.py
import asyncio
from datetime import datetime
from api.services.health import HealthDashboard

async def daily_health_check():
    """Run daily health check and save to database"""
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    print(f"Running health check at {datetime.now()}")
    health = await dashboard.analyze_project()

    # Generate reports
    text_report = dashboard.generate_report(health, format='text')
    json_report = dashboard.generate_report(health, format='json')

    # Save reports
    with open(f"health_report_{datetime.now().strftime('%Y%m%d')}.txt", 'w') as f:
        f.write(text_report)

    with open(f"health_report_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
        f.write(json_report)

    # Check for degrading trends
    trends = dashboard.get_trends(lookback_days=7)
    degrading = [k for k, v in trends.items() if v.value == 'degrading']

    if degrading:
        print(f"⚠️  Warning: Degrading trends detected: {', '.join(degrading)}")

    if health.overall_status.value == 'critical':
        print("❌ CRITICAL: Code health requires immediate attention")
        # Could send notifications here
    else:
        print("✅ Health check complete")

if __name__ == '__main__':
    asyncio.run(daily_health_check())
```

Add to cron:
```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/MagnetarCode/apps/backend && python scheduled_health_check.py
```

## Integration with Agent System

Use health metrics to inform the AI agent about code quality:

```python
from api.services.health import get_health_dashboard

async def get_code_context_with_health(file_path: str):
    """Get code context enriched with health metrics"""
    dashboard = get_health_dashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    file_health = dashboard.analyze_file(Path(file_path))

    if file_health:
        context = f"""
File: {file_path}
Status: {file_health.status.value}
Complexity: {file_health.avg_complexity:.1f} (max: {file_health.max_complexity})
Maintainability: {file_health.maintainability_index:.1f}/100
Documentation: {file_health.documentation_coverage:.1f}%

High complexity functions:
"""
        for func in sorted(file_health.functions, key=lambda f: f.cyclomatic_complexity, reverse=True)[:3]:
            context += f"  - {func.name}: CC={func.cyclomatic_complexity}\n"

        return context

    return f"File: {file_path}\nNo health metrics available"
```

## Monitoring Dashboard (Future)

The system is designed to support a web dashboard. Here's the data structure:

```python
# Get historical data for charts
import sqlite3
from datetime import datetime, timedelta

def get_historical_metrics(days=30):
    """Get metrics for the last N days"""
    db_path = "/path/to/.health_metrics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute('''
        SELECT
            timestamp,
            avg_complexity,
            avg_maintainability,
            test_coverage,
            total_tech_debt_hours
        FROM health_snapshots
        WHERE timestamp >= ?
        ORDER BY timestamp ASC
    ''', (cutoff,))

    return [
        {
            'timestamp': row[0],
            'complexity': row[1],
            'maintainability': row[2],
            'coverage': row[3],
            'tech_debt': row[4]
        }
        for row in cursor.fetchall()
    ]
```

## Best Practices

### 1. Regular Analysis
- Run analysis daily or weekly
- Track trends over time
- Set up alerts for degrading metrics

### 2. Team Thresholds
- Adjust thresholds to match team standards
- Start lenient, gradually increase over time
- Document threshold decisions

### 3. Prioritize Tech Debt
- Sort by estimated hours
- Focus on high-impact, low-effort items first
- Track debt resolution over time

### 4. Use in Code Reviews
- Include health metrics in PR descriptions
- Flag files with critical status
- Require documentation for complex functions

### 5. Integrate with Development Workflow
- Add pre-commit hooks for critical issues
- Include health checks in CI/CD pipeline
- Review trends in sprint retrospectives

## Example Reports

### Text Report
```
================================================================================
                           CODE HEALTH REPORT
================================================================================
Generated: 2024-01-15 10:30:00
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
```

### Markdown Report
Perfect for GitHub wikis or documentation.

### JSON Report
Ideal for programmatic consumption and dashboards.

## Troubleshooting

### Coverage Not Detected
```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Run tests with coverage
pytest --cov=apps/backend/api --cov-report=json
```

### Database Locked
```python
# Clear lock by closing connections
import sqlite3
conn = sqlite3.connect('.health_metrics.db')
conn.close()
```

### Slow Analysis
- Reduce scope with custom `exclude_patterns`
- Analyze specific directories instead of entire project
- Run in background for large projects

## Support

For issues or questions:
1. Check the README.md for detailed documentation
2. Review example_usage.py for code examples
3. Run tests: `pytest test_health.py -v`
4. Check logs for detailed error messages
