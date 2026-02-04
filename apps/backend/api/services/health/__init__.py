"""
Code Health Dashboard Package

Comprehensive code health monitoring system that tracks:
- Cyclomatic complexity
- Maintainability index
- Technical debt
- Code duplication
- Test coverage
- Documentation coverage
- Dependency health
- Historical trends

Usage:
    from api.services.health import HealthDashboard, ProjectHealth

    dashboard = HealthDashboard(project_root="/path/to/project")
    health = await dashboard.analyze_project()
    report = dashboard.generate_report(health)
"""

from .metrics import (
    CodeMetrics,
    FileHealth,
    ProjectHealth,
    TechDebtItem,
    HealthDashboard,
    HealthThresholds,
    TrendDirection,
    HealthStatus,
    DependencyIssue,
    DuplicateBlock,
    get_health_dashboard,
)

__all__ = [
    # Core Models
    "CodeMetrics",
    "FileHealth",
    "ProjectHealth",
    "TechDebtItem",
    "DependencyIssue",
    "DuplicateBlock",
    # Main Service
    "HealthDashboard",
    "get_health_dashboard",
    # Configuration
    "HealthThresholds",
    # Enums
    "TrendDirection",
    "HealthStatus",
]
