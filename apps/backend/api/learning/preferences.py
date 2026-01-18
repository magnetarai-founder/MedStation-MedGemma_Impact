"""
Learning System - Preference Learning

User preference tracking and learning:
- learn_from_execution: Infer preferences from execution patterns
- update_preference: Update preference signals
- get_preferences: Query learned preferences

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import sqlite3
from typing import List, Optional
from threading import Lock

from .models import UserPreference


def learn_from_execution(
    conn: sqlite3.Connection,
    lock: Lock,
    command: str,
    tool: str,
    success: bool,
    execution_time: Optional[float]
) -> None:
    """
    Learn preferences from execution patterns.

    Infers user preferences from successful executions, timing, and command types.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        command: Command that was executed
        tool: Tool used
        success: Whether execution succeeded
        execution_time: Time taken in seconds (optional)
    """
    with lock:
        # Learn tool preferences
        if success:
            _update_preference(conn, 'tool', tool, positive=True)

        # Learn timing preferences
        if execution_time is not None:
            if execution_time < 2.0:
                _update_preference(conn, 'speed', 'fast_execution', positive=True)
            elif execution_time > 10.0:
                _update_preference(conn, 'speed', 'thorough_execution', positive=True)

        # Learn command type preferences
        command_lower = command.lower()
        if 'test' in command_lower:
            _update_preference(conn, 'workflow', 'testing_focused', positive=True)
        if 'document' in command_lower or 'readme' in command_lower:
            _update_preference(conn, 'workflow', 'documentation_focused', positive=True)

        conn.commit()


def _update_preference(
    conn: sqlite3.Connection,
    category: str,
    preference: str,
    positive: bool = True
) -> None:
    """
    Update a user preference based on observed behavior.

    Args:
        conn: SQLite database connection
        category: Preference category (e.g., 'tool', 'workflow', 'speed')
        preference: Specific preference value
        positive: Whether this is a positive or negative signal
    """
    cursor = conn.execute("""
        SELECT positive_signals, negative_signals
        FROM user_preferences
        WHERE category = ? AND preference = ?
    """, (category, preference))

    row = cursor.fetchone()

    if row:
        # Update existing preference
        pos = row['positive_signals'] + (1 if positive else 0)
        neg = row['negative_signals'] + (0 if positive else 1)
        confidence = pos / (pos + neg) if (pos + neg) > 0 else 0.5

        conn.execute("""
            UPDATE user_preferences
            SET positive_signals = ?, negative_signals = ?,
                confidence = ?, last_observed = CURRENT_TIMESTAMP
            WHERE category = ? AND preference = ?
        """, (pos, neg, confidence, category, preference))
    else:
        # Insert new preference
        conn.execute("""
            INSERT INTO user_preferences
            (category, preference, positive_signals, negative_signals,
             confidence, last_observed)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            category, preference,
            1 if positive else 0,
            0 if positive else 1,
            1.0 if positive else 0.0
        ))


def get_preferences(
    conn: sqlite3.Connection,
    category: Optional[str] = None
) -> List[UserPreference]:
    """
    Get learned user preferences.

    Args:
        conn: SQLite database connection
        category: Optional category filter

    Returns:
        List of UserPreference objects with confidence > 0.6
    """
    if category:
        cursor = conn.execute("""
            SELECT * FROM user_preferences
            WHERE category = ? AND confidence > 0.6
            ORDER BY confidence DESC
        """, (category,))
    else:
        cursor = conn.execute("""
            SELECT * FROM user_preferences
            WHERE confidence > 0.6
            ORDER BY category, confidence DESC
        """)

    preferences = []
    for row in cursor:
        preferences.append(UserPreference(
            category=row['category'],
            preference=row['preference'],
            confidence=row['confidence'],
            evidence_count=row['positive_signals'] + row['negative_signals'],
            last_observed=row['last_observed']
        ))

    return preferences


def record_preference(
    conn: sqlite3.Connection,
    lock: Lock,
    category: str,
    preference: str
) -> None:
    """
    Record a user preference directly.

    Simple interface for explicit preference recording.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        category: Preference category
        preference: Preference value
    """
    with lock:
        _update_preference(conn, category, preference, positive=True)
        conn.commit()
