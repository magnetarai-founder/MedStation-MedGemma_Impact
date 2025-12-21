"""
Learning System - Main Orchestrator

Main LearningSystem class that orchestrates all learning components:
- Success tracking
- Preference learning
- Coding style detection
- Project context management
- Recommendation generation

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

# Import all modular components
try:
    from .storage import get_default_db_path, create_connection, setup_database
    from .models import UserPreference, CodingStyle, ProjectContext, Recommendation
    from .patterns import initialize_pattern_rules
    from .success import track_execution as _track_execution, get_success_rate as _get_success_rate
    from .preferences import learn_from_execution, get_preferences as _get_preferences, record_preference as _record_preference
    from .style import detect_coding_style as _detect_coding_style
    from .context import detect_project_context as _detect_project_context, switch_context as _switch_context, get_active_projects as _get_active_projects
    from .recommendations import get_recommendations as _get_recommendations
except ImportError:
    from storage import get_default_db_path, create_connection, setup_database
    from models import UserPreference, CodingStyle, ProjectContext, Recommendation
    from patterns import initialize_pattern_rules
    from success import track_execution as _track_execution, get_success_rate as _get_success_rate
    from preferences import learn_from_execution, get_preferences as _get_preferences, record_preference as _record_preference
    from style import detect_coding_style as _detect_coding_style
    from context import detect_project_context as _detect_project_context, switch_context as _switch_context, get_active_projects as _get_active_projects
    from recommendations import get_recommendations as _get_recommendations

logger = logging.getLogger(__name__)


class LearningSystem:
    """
    Adaptive learning system for ElohimOS.

    Learns from user interactions to provide intelligent recommendations,
    track success patterns, detect coding styles, and manage project contexts.
    """

    def __init__(self, memory=None, db_path: Path = None):
        """
        Initialize the learning system.

        Args:
            memory: Optional JarvisMemory instance (for integration)
            db_path: Optional path to SQLite database (defaults to data_dir/learning.db)
        """
        self.memory = memory
        self._lock = Lock()

        # Database setup
        if db_path is None:
            db_path = get_default_db_path()

        self.db_path = db_path
        self.conn = create_connection(db_path)
        setup_database(self.conn)

        # Initialize pattern detection rules
        self.pattern_rules = initialize_pattern_rules()

        logger.info(f"Learning system initialized with database: {db_path}")

    # ============= SUCCESS TRACKING =============

    def track_execution(
        self,
        command: str,
        tool: str,
        success: bool,
        execution_time: float,
        context: Optional[Dict] = None
    ) -> None:
        """
        Track command execution for learning.

        Args:
            command: Command that was executed
            tool: Tool used to execute command
            success: Whether execution succeeded
            execution_time: Time taken in seconds
            context: Optional context dictionary
        """
        _track_execution(
            self.conn,
            self._lock,
            command,
            tool,
            success,
            execution_time,
            context,
            learn_callback=self._learn_from_execution
        )

    def get_success_rate(self, command: str, tool: str) -> float:
        """
        Get success rate for a command/tool combination.

        Args:
            command: Command to query
            tool: Tool to query

        Returns:
            Success rate (0.0 to 1.0)
        """
        return _get_success_rate(self.conn, command, tool)

    # ============= PREFERENCE LEARNING =============

    def _learn_from_execution(
        self,
        command: str,
        tool: str,
        success: bool,
        execution_time: float
    ) -> None:
        """
        Learn preferences from execution patterns (internal).

        Args:
            command: Command that was executed
            tool: Tool used
            success: Whether execution succeeded
            execution_time: Time taken in seconds
        """
        learn_from_execution(self.conn, self._lock, command, tool, success, execution_time)

    def get_preferences(self, category: Optional[str] = None) -> List[UserPreference]:
        """
        Get learned user preferences.

        Args:
            category: Optional category filter

        Returns:
            List of UserPreference objects
        """
        return _get_preferences(self.conn, category)

    # ============= STYLE DETECTION =============

    def detect_coding_style(self, file_path: str, content: str) -> CodingStyle:
        """
        Detect coding style from file content.

        Args:
            file_path: Path to the file being analyzed
            content: File content to analyze

        Returns:
            CodingStyle object with detected patterns
        """
        return _detect_coding_style(self.conn, self._lock, file_path, content)

    # ============= RECOMMENDATIONS =============

    def get_recommendations(
        self,
        command: str,
        context: Optional[Dict] = None
    ) -> List[Recommendation]:
        """
        Get learning-based recommendations for a command.

        Args:
            command: Command to get recommendations for
            context: Optional context dict with file_path, etc.

        Returns:
            List of Recommendation objects
        """
        return _get_recommendations(self.conn, command, context)

    # ============= CONTEXT AWARENESS =============

    def detect_project_context(self, cwd: str = None) -> ProjectContext:
        """
        Detect and store project context.

        Args:
            cwd: Current working directory (defaults to Path.cwd())

        Returns:
            ProjectContext object with detected metadata
        """
        return _detect_project_context(self.conn, self._lock, cwd)

    def switch_context(self, project_path: str) -> ProjectContext:
        """
        Switch to a different project context.

        Args:
            project_path: Path to the project

        Returns:
            ProjectContext for the specified project
        """
        return _switch_context(self.conn, self._lock, project_path)

    def get_active_projects(self, limit: int = 5) -> List[ProjectContext]:
        """
        Get recently active projects.

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of ProjectContext objects
        """
        return _get_active_projects(self.conn, limit)

    # ============= SIMPLE INTERFACES =============

    def record_command(self, command: str, success: bool = True) -> None:
        """
        Record a command execution (simple interface).

        Args:
            command: Command that was executed
            success: Whether execution succeeded
        """
        self.track_execution(command, tool="unknown", success=success, execution_time=0.0)

    def record_preference(self, category: str, preference: str) -> None:
        """
        Record a user preference directly.

        Args:
            category: Preference category
            preference: Preference value
        """
        _record_preference(self.conn, self._lock, category, preference)

    def record_model_performance(
        self,
        model: str,
        response_time: float,
        quality_score: float
    ) -> None:
        """
        Record model performance metrics.

        Args:
            model: Model name
            response_time: Response time in seconds
            quality_score: Quality score (0.0 to 1.0)
        """
        pattern_data = {
            'model': model,
            'response_time': response_time,
            'quality_score': quality_score,
            'timestamp': datetime.now().isoformat()
        }

        pattern_hash = hashlib.sha256(
            f"model_perf_{model}_{datetime.now().date()}".encode()
        ).hexdigest()

        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO success_patterns
                (pattern_hash, pattern_type, pattern_data, success_count, failure_count,
                 total_count, avg_time, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (pattern_hash, 'model_performance', json.dumps(pattern_data),
                  1, 0, 1, response_time))
            self.conn.commit()

    # ============= ANALYTICS =============

    def get_learned_patterns(self) -> List[Dict]:
        """
        Get all learned patterns.

        Returns:
            List of pattern dicts with success rates
        """
        patterns = self.conn.execute("""
            SELECT pattern_type, pattern_data, success_count, total_count,
                   success_count * 1.0 / total_count as success_rate
            FROM success_patterns
            WHERE total_count > 5
            ORDER BY success_rate DESC
            LIMIT 20
        """).fetchall()

        return [dict(p) for p in patterns]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get learning system statistics.

        Returns:
            Dict with success_rate, pattern_count, preference_count
        """
        stats = {}

        # Success rate
        total = self.conn.execute(
            "SELECT SUM(total_count), SUM(success_count) FROM success_patterns"
        ).fetchone()
        if total and total[0]:
            stats['success_rate'] = total[1] / total[0]
        else:
            stats['success_rate'] = 0.0

        # Pattern count
        stats['pattern_count'] = self.conn.execute(
            "SELECT COUNT(*) FROM success_patterns"
        ).fetchone()[0]

        # Preference count
        stats['preference_count'] = self.conn.execute(
            "SELECT COUNT(*) FROM user_preferences"
        ).fetchone()[0]

        return stats

    def get_best_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get the best performing model for a task type.

        Args:
            task_type: Type of task (code_generation, chat, analysis)

        Returns:
            Model name, or default model
        """
        # For now, return a default model based on task type
        model_map = {
            'code_generation': 'qwen2.5-coder:32b',
            'chat': 'phi3:mini',
            'analysis': 'llama3.1:8b'
        }
        return model_map.get(task_type, 'qwen2.5-coder:1.5b-instruct')
