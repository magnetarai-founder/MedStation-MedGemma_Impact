"""
Learning System Package

Modular adaptive learning system for MedStation.

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
from .system import LearningSystem

# Data models
from .models import UserPreference, CodingStyle, ProjectContext, Recommendation

# Storage utilities (for advanced usage)
from .storage import get_default_db_path, create_connection, setup_database

# Learning engine (model usage tracking)
from .engine import LearningEngine, get_learning_engine


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

    # Learning engine
    'LearningEngine',
    'get_learning_engine',
]
