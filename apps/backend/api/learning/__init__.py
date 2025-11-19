"""
Learning System Package

Modular adaptive learning system for ElohimOS.

Main Components:
- LearningSystem: Main orchestrator class
- Data Models: UserPreference, CodingStyle, ProjectContext, Recommendation
- Storage: Database setup and connection management
- Pattern Detection: Workflow and tool preference detection
- Success Tracking: Command execution success/failure tracking
- Preference Learning: User preference inference
- Style Detection: Coding style analysis
- Context Management: Project context detection
- Recommendations: Learning-based recommendation engine

Created during Phase 6.3c modularization.
"""

# Main system class
try:
    from .system import LearningSystem
except ImportError:
    from system import LearningSystem

# Data models
try:
    from .models import UserPreference, CodingStyle, ProjectContext, Recommendation
except ImportError:
    from models import UserPreference, CodingStyle, ProjectContext, Recommendation

# Storage utilities (for advanced usage)
try:
    from .storage import get_default_db_path, create_connection, setup_database
except ImportError:
    from storage import get_default_db_path, create_connection, setup_database


__all__ = [
    # Main system
    'LearningSystem',

    # Data models
    'UserPreference',
    'CodingStyle',
    'ProjectContext',
    'Recommendation',

    # Storage utilities
    'get_default_db_path',
    'create_connection',
    'setup_database',
]
