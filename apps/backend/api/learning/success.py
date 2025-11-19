"""
Learning System - Success Tracking

Success pattern tracking and analysis:
- track_execution: Record command execution results
- get_success_rate: Query historical success rates
- Success pattern database management

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import hashlib
import json
import sqlite3
from typing import Dict, Optional
from threading import Lock


def track_execution(
    conn: sqlite3.Connection,
    lock: Lock,
    command: str,
    tool: str,
    success: bool,
    execution_time: float,
    context: Optional[Dict] = None,
    learn_callback=None
) -> None:
    """
    Track command execution for learning.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        command: Command that was executed
        tool: Tool used to execute command
        success: Whether execution succeeded
        execution_time: Time taken in seconds
        context: Optional context dictionary
        learn_callback: Optional callback for preference learning
    """
    with lock:
        # Store in learning feedback
        conn.execute("""
            INSERT INTO learning_feedback
            (command, tool_used, execution_time, success, context_data)
            VALUES (?, ?, ?, ?, ?)
        """, (command, tool, execution_time, success, json.dumps(context or {})))

        # Update success patterns
        pattern_hash = hashlib.md5(f"{command}_{tool}".encode()).hexdigest()

        cursor = conn.execute("""
            SELECT success_count, failure_count, avg_time
            FROM success_patterns
            WHERE pattern_hash = ?
        """, (pattern_hash,))

        row = cursor.fetchone()

        if row:
            # Update existing pattern
            new_success = row['success_count'] + (1 if success else 0)
            new_failure = row['failure_count'] + (0 if success else 1)
            total = new_success + new_failure
            new_avg_time = (row['avg_time'] * (total - 1) + execution_time) / total
            confidence = new_success / total if total > 0 else 0

            conn.execute("""
                UPDATE success_patterns
                SET success_count = ?, failure_count = ?, total_count = ?, avg_time = ?,
                    confidence = ?, last_seen = CURRENT_TIMESTAMP
                WHERE pattern_hash = ?
            """, (new_success, new_failure, total, new_avg_time, confidence, pattern_hash))
        else:
            # Create new pattern
            conn.execute("""
                INSERT INTO success_patterns
                (pattern_hash, pattern_type, pattern_data, success_count,
                 failure_count, total_count, avg_time, confidence, last_seen)
                VALUES (?, 'command', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                pattern_hash,
                json.dumps({'command': command, 'tool': tool}),
                1 if success else 0,
                0 if success else 1,
                1,
                execution_time,
                1.0 if success else 0.0
            ))

        conn.commit()

        # Learn from this execution (if callback provided)
        if learn_callback:
            learn_callback(command, tool, success, execution_time)


def get_success_rate(conn: sqlite3.Connection, command: str, tool: str) -> float:
    """
    Get success rate for a command/tool combination.

    Args:
        conn: SQLite database connection
        command: Command to query
        tool: Tool to query

    Returns:
        Success rate (0.0 to 1.0), defaults to 0.5 if unknown
    """
    pattern_hash = hashlib.md5(f"{command}_{tool}".encode()).hexdigest()

    cursor = conn.execute("""
        SELECT confidence FROM success_patterns
        WHERE pattern_hash = ?
    """, (pattern_hash,))

    row = cursor.fetchone()
    return row['confidence'] if row else 0.5  # Default 50% if unknown
