# Code Health Dashboard

A comprehensive code health monitoring system for MagnetarCode that tracks code quality metrics, technical debt, and trends over time.

## Features

### 1. Cyclomatic Complexity Analysis
- **Per-function complexity calculation** using AST analysis
- **Cognitive complexity** measurement for better readability assessment
- **Halstead metrics** (volume, difficulty) for code complexity
- Automatic detection of high-complexity functions

### 2. Maintainability Index
- Industry-standard maintainability calculation
- Combines complexity, lines of code, and comment ratio
- Normalized to 0-100 scale (higher is better)
- File-level and project-level aggregation

### 3. Technical Debt Estimation
- Automatic debt detection across categories:
  - **Complexity**: High cyclomatic complexity functions
  - **Documentation**: Missing docstrings
  - **Testing**: Low test coverage
  - **Duplication**: Repeated code blocks
- Hours-based estimation for prioritization
- Severity levels (GOOD, WARNING, CRITICAL)

### 4. Code Duplication Detection
- Hash-based exact duplicate detection
- Configurable minimum block size
- Cross-file duplicate tracking
- Refactoring time estimation

### 5. Test Coverage
- Integration with pytest-cov
- Project-level and file-level tracking
- Historical trend analysis

### 6. Documentation Coverage
- Docstring presence analysis
- Function-level and file-level metrics
- Missing documentation identification

### 7. Dependency Health
- Outdated package detection
- Vulnerability scanning (with pip-audit)
- Severity-based classification

### 8. Historical Trend Tracking
- SQLite-based persistence
- Trend analysis (improving/stable/degrading)
- Configurable lookback periods
- Metric comparison over time

## Installation

No additional dependencies beyond MagnetarCode's existing requirements. Optional tools for enhanced functionality:

```bash
# For vulnerability scanning
pip install pip-audit

# For test coverage (already in requirements.txt)
pip install pytest-cov
```

## Quick Start

```python
from api.services.health import HealthDashboard

# Initialize dashboard
dashboard = HealthDashboard(
    project_root="/path/to/your/project"
)

# Run analysis
health = await dashboard.analyze_project()

# Generate report
report = dashboard.generate_report(health, format='text')
print(report)
```

## Usage Examples

### Basic Analysis

```python
import asyncio
from api.services.health import HealthDashboard

async def analyze():
    dashboard = HealthDashboard(
        project_root="/Users/indiedevhipps/Documents/MagnetarCode/apps/backend"
    )

    health = await dashboard.analyze_project()
    print(dashboard.generate_report(health))

asyncio.run(analyze())
```

### Custom Thresholds

```python
from api.services.health import HealthDashboard, HealthThresholds

# Define stricter quality standards
thresholds = HealthThresholds(
    complexity_good=8,
    complexity_warning=12,
    complexity_critical=20,
    maintainability_good=80.0,
    coverage_good=90.0,
)

dashboard = HealthDashboard(
    project_root="/path/to/project",
    thresholds=thresholds
)
```

### Single File Analysis

```python
from pathlib import Path

file_health = dashboard.analyze_file(
    Path("/path/to/file.py")
)

print(f"Status: {file_health.status.value}")
print(f"Complexity: {file_health.avg_complexity:.2f}")
print(f"Maintainability: {file_health.maintainability_index:.2f}")
```

### Track Trends

```python
# Run analysis multiple times over days/weeks
health = await dashboard.analyze_project()  # Saves to database

# Get trends
trends = dashboard.get_trends(lookback_days=30)
print(f"Complexity trend: {trends['complexity'].value}")
print(f"Coverage trend: {trends['coverage'].value}")
```

### Identify Technical Debt

```python
health = await dashboard.analyze_project()

# Sort by estimated hours
top_debt = sorted(
    health.tech_debt_items,
    key=lambda x: x.estimated_hours,
    reverse=True
)[:10]

for item in top_debt:
    print(f"{item.category}: {item.description}")
    print(f"  Estimated: {item.estimated_hours:.1f} hours")
```

### CI/CD Integration

```python
# Generate JSON report for automated checks
json_report = dashboard.generate_report(health, format='json')

# Parse and fail build if critical
import json
data = json.loads(json_report)

if data['overall_status'] == 'critical':
    print("Build failed: Critical health issues detected")
    exit(1)
```

## Data Models

### CodeMetrics
Per-function metrics including:
- Cyclomatic complexity
- Cognitive complexity
- Lines of code
- Halstead metrics
- Documentation status

### FileHealth
Per-file metrics including:
- Line counts (total, code, comments, blank)
- Function metrics aggregation
- Maintainability index
- Test coverage
- Status (GOOD/WARNING/CRITICAL)

### ProjectHealth
Project-level metrics including:
- Aggregated statistics
- File health list
- Technical debt items
- Duplicate blocks
- Dependency issues
- Trend directions
- Overall status

### TechDebtItem
Individual debt items with:
- Category (complexity, testing, documentation, duplication)
- Severity level
- Location (file, line)
- Estimated hours to fix
- Current vs. threshold values

## Health Thresholds

Default thresholds (configurable):

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Cyclomatic Complexity | ≤10 | ≤15 | >15 |
| Maintainability Index | ≥70 | ≥50 | <50 |
| Test Coverage | ≥80% | ≥60% | <60% |
| Documentation Coverage | ≥75% | ≥50% | <50% |
| Code Duplication | ≤3% | ≤5% | >5% |
| Lines per Function | ≤50 | ≤100 | >100 |

## Database Schema

Health metrics are stored in SQLite (`.health_metrics.db`) with tables:

- **health_snapshots**: Project-level snapshots over time
- **file_metrics**: File-level metrics per snapshot
- **function_metrics**: Function-level metrics per file
- **tech_debt**: Technical debt items per snapshot

Indexed for fast queries and trend analysis.

## Report Formats

### Text Format
Human-readable console output with sections:
- Summary statistics
- Quality metrics with trends
- Technical debt breakdown
- File health summary

### Markdown Format
Documentation-friendly format with:
- Tables for metrics
- Trend indicators
- Top issues list
- Dependency warnings

### JSON Format
Machine-readable for CI/CD:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "overall_status": "warning",
  "metrics": {
    "avg_complexity": 12.5,
    "avg_maintainability": 65.3,
    "test_coverage": 73.2
  },
  "trends": {
    "complexity": "improving",
    "coverage": "stable"
  }
}
```

## Exclusion Patterns

By default, excludes:
- `*/venv/*`, `*/.venv/*`
- `*/node_modules/*`
- `*/__pycache__/*`
- `*/build/*`, `*/dist/*`
- `*/migrations/*`
- `*/.git/*`

Customize via `exclude_patterns` parameter.

## Best Practices

1. **Run regularly**: Schedule daily or weekly analyses to track trends
2. **Set team thresholds**: Adjust thresholds to match your quality standards
3. **Prioritize by hours**: Focus on high-hour technical debt items first
4. **Monitor trends**: Pay attention to degrading metrics
5. **Integrate with CI/CD**: Block PRs that introduce critical issues
6. **Review duplicates**: Regular refactoring of duplicated code
7. **Track dependencies**: Keep packages updated and secure

## Performance

- Typical analysis time: 5-30 seconds for medium projects (500-2000 files)
- Database size: ~1-5 MB per year of daily snapshots
- Memory usage: ~50-200 MB during analysis

## Limitations

1. **Python-only**: Currently analyzes Python files only
2. **Test coverage**: Requires pytest and pytest-cov
3. **Exact duplicates**: Only detects exact matches (not semantic duplicates)
4. **Single-threaded**: Analysis runs sequentially (could be parallelized)

## Future Enhancements

- [ ] Multi-language support (JavaScript, TypeScript, etc.)
- [ ] Semantic duplicate detection using embeddings
- [ ] Parallel file analysis for better performance
- [ ] Web dashboard with charts and visualizations
- [ ] GitHub Actions integration
- [ ] Slack/Discord notifications for trend changes
- [ ] Code smell detection (long parameter lists, god classes, etc.)
- [ ] Refactoring suggestions using LLM

## API Reference

See `example_usage.py` for comprehensive examples of all features.

## License

Part of MagnetarCode - see project root for license information.
