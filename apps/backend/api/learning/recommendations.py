"""
Learning System - Recommendation Engine

Learning-based recommendation generation:
- get_recommendations: Generate recommendations for a command
- Tool recommendations based on success patterns
- Workflow recommendations based on preferences
- Style recommendations based on detected patterns

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import json
import sqlite3
from typing import Dict, List, Optional

try:
    from .models import Recommendation
except ImportError:
    from models import Recommendation

try:
    from .success import get_success_rate
except ImportError:
    from success import get_success_rate

try:
    from .preferences import get_preferences
except ImportError:
    from preferences import get_preferences

try:
    from .style import _detect_language
except ImportError:
    from style import _detect_language


def get_recommendations(
    conn: sqlite3.Connection,
    command: str,
    context: Optional[Dict] = None
) -> List[Recommendation]:
    """
    Get learning-based recommendations for a command.

    Args:
        conn: SQLite database connection
        command: Command to get recommendations for
        context: Optional context dict with file_path, etc.

    Returns:
        List of Recommendation objects
    """
    recommendations = []

    # Tool recommendations based on success patterns
    tool_rec = _recommend_tool(conn, command)
    if tool_rec:
        recommendations.append(tool_rec)

    # Workflow recommendations based on patterns
    workflow_rec = _recommend_workflow(conn, command, context)
    if workflow_rec:
        recommendations.append(workflow_rec)

    # Style recommendations based on detected patterns
    if context and 'file_path' in context:
        style_rec = _recommend_style(conn, context['file_path'])
        if style_rec:
            recommendations.append(style_rec)

    return recommendations


def _recommend_tool(conn: sqlite3.Connection, command: str) -> Optional[Recommendation]:
    """
    Recommend best tool based on success patterns.

    Args:
        conn: SQLite database connection
        command: Command to analyze

    Returns:
        Recommendation for best tool, or None
    """
    # Check success rates for different tools
    tools = ['aider', 'ollama', 'assistant', 'system']
    best_tool = None
    best_rate = 0.0

    for tool in tools:
        rate = get_success_rate(conn, command, tool)
        if rate > best_rate:
            best_rate = rate
            best_tool = tool

    if best_tool and best_rate > 0.7:
        return Recommendation(
            action=f"Use {best_tool} for this command",
            reason=f"Historical success rate: {best_rate:.0%}",
            confidence=best_rate,
            based_on=['success_patterns']
        )

    return None


def _recommend_workflow(
    conn: sqlite3.Connection,
    command: str,
    context: Optional[Dict] = None
) -> Optional[Recommendation]:
    """
    Recommend workflow based on user preferences.

    Args:
        conn: SQLite database connection
        command: Command to analyze
        context: Optional context dict

    Returns:
        Workflow recommendation, or None
    """
    preferences = get_preferences(conn, 'workflow')

    if preferences:
        top_pref = preferences[0]

        if top_pref.preference == 'testing_focused' and 'test' not in command.lower():
            return Recommendation(
                action="Consider adding tests",
                reason=f"You typically prefer test-driven development (confidence: {top_pref.confidence:.0%})",
                confidence=top_pref.confidence,
                based_on=['workflow_preferences']
            )
        elif top_pref.preference == 'documentation_focused' and 'doc' not in command.lower():
            return Recommendation(
                action="Remember to update documentation",
                reason=f"You typically prioritize documentation (confidence: {top_pref.confidence:.0%})",
                confidence=top_pref.confidence,
                based_on=['workflow_preferences']
            )

    return None


def _recommend_style(conn: sqlite3.Connection, file_path: str) -> Optional[Recommendation]:
    """
    Recommend coding style based on detected patterns.

    Args:
        conn: SQLite database connection
        file_path: Path to file being edited

    Returns:
        Style recommendation, or None
    """
    language = _detect_language(file_path)

    cursor = conn.execute("""
        SELECT style_data, confidence
        FROM coding_styles
        WHERE language = ?
        ORDER BY sample_count DESC
        LIMIT 1
    """, (language,))

    row = cursor.fetchone()

    if row and row['confidence'] > 0.7:
        style_data = json.loads(row['style_data'])

        if language == 'python' and 'indent' in style_data:
            return Recommendation(
                action=f"Use {style_data['indent']} spaces for indentation",
                reason=f"Project standard detected from existing code",
                confidence=row['confidence'],
                based_on=['coding_style']
            )

    return None
