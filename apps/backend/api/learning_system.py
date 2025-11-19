#!/usr/bin/env python3
"""
Jarvis Learning System - Compatibility Shim

BACKWARDS COMPATIBILITY LAYER
This module maintains backwards compatibility for existing imports.

Original monolithic implementation has been modularized into api/learning/ package:
- api/learning/models.py - Data models
- api/learning/storage.py - Database setup
- api/learning/patterns.py - Pattern detection
- api/learning/success.py - Success tracking
- api/learning/preferences.py - Preference learning
- api/learning/style.py - Coding style detection
- api/learning/context.py - Project context management
- api/learning/recommendations.py - Recommendation engine
- api/learning/system.py - Main LearningSystem orchestrator
- api/learning/__init__.py - Package exports

Refactored during Phase 6.3c modularization.

All existing imports from adaptive_router.py, jarvis_adaptive_router.py,
and chat services continue to work unchanged.
"""

# Re-export all public classes and functions from the new modular package
try:
    from api.learning import (
        LearningSystem,
        UserPreference,
        CodingStyle,
        ProjectContext,
        Recommendation,
        get_default_db_path,
        create_connection,
        setup_database,
    )
except ImportError:
    from learning import (
        LearningSystem,
        UserPreference,
        CodingStyle,
        ProjectContext,
        Recommendation,
        get_default_db_path,
        create_connection,
        setup_database,
    )

# Re-export JarvisMemory for test compatibility
try:
    from jarvis_memory import JarvisMemory
except ImportError:
    try:
        from api.jarvis_memory import JarvisMemory
    except ImportError:
        from api.jarvis_memory import JarvisMemory


# Test function preserved for backwards compatibility
def test_learning_system():
    """Test the learning system"""
    print("Testing Learning System...")

    # Create learning system
    memory = JarvisMemory(Path("/tmp/test_learning_memory.db"))
    learner = LearningSystem(memory=memory, db_path=Path("/tmp/test_learning.db"))

    print("\n1. Testing Success Tracking")
    # Track some executions
    learner.track_execution("create test.py", "aider", True, 2.5)
    learner.track_execution("create test.py", "aider", True, 2.3)
    learner.track_execution("create test.py", "ollama", False, 5.0)

    success_rate = learner.get_success_rate("create test.py", "aider")
    print(f"   Aider success rate: {success_rate:.0%}")

    print("\n2. Testing Preference Learning")
    # Simulate multiple executions to learn preferences
    for _ in range(5):
        learner.track_execution("write tests for calculator", "assistant", True, 1.5)
    for _ in range(3):
        learner.track_execution("document the API", "assistant", True, 2.0)

    preferences = learner.get_preferences()
    print(f"   Learned {len(preferences)} preferences:")
    for pref in preferences[:3]:
        print(f"     - {pref.category}/{pref.preference}: {pref.confidence:.0%}")

    print("\n3. Testing Style Detection")
    sample_python = '''
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)

class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b
'''

    style = learner.detect_coding_style("test.py", sample_python)
    print(f"   Detected {style.language} style:")
    for key, value in list(style.patterns.items())[:3]:
        print(f"     - {key}: {value}")

    print("\n4. Testing Recommendations")
    recommendations = learner.get_recommendations("create calculator.py")
    print(f"   Generated {len(recommendations)} recommendations:")
    for rec in recommendations:
        print(f"     - {rec.action} ({rec.confidence:.0%})")
        print(f"       Reason: {rec.reason}")

    print("\n5. Testing Project Context")
    context = learner.detect_project_context()
    print(f"   Detected project type: {context.project_type}")
    print(f"   Languages: {', '.join(context.languages[:3]) if context.languages else 'none'}")
    print(f"   Frameworks: {', '.join(context.frameworks[:3]) if context.frameworks else 'none'}")

    print("\n6. Testing Context Switching")
    projects = learner.get_active_projects(limit=3)
    print(f"   Found {len(projects)} active projects")
    for proj in projects:
        print(f"     - {Path(proj.project_path).name}: {proj.project_type} ({proj.activity_count} activities)")

    print("\n✅ Learning System Test Complete!")


if __name__ == "__main__":
    from pathlib import Path
    test_learning_system()
