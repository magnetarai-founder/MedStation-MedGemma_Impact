"""
Preference Learner

Learns and adapts to user preferences over time.
This is a key differentiator from Claude Code and Codex.
"""

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A learned behavioral pattern."""

    pattern_name: str
    pattern_type: str  # "coding_style", "tool_usage", "response_preference", etc.
    value: Any
    confidence: float
    observation_count: int
    last_updated: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_name": self.pattern_name,
            "pattern_type": self.pattern_type,
            "value": self.value,
            "confidence": self.confidence,
            "observation_count": self.observation_count,
            "last_updated": self.last_updated,
        }


@dataclass
class UserPreferences:
    """Aggregated user preferences."""

    user_id: str

    # Coding style preferences
    preferred_languages: list[str] = field(default_factory=list)
    indentation_style: str = "spaces"  # "spaces" or "tabs"
    indent_size: int = 4
    quote_style: str = "double"  # "single" or "double"
    naming_convention: str = "snake_case"  # "snake_case", "camelCase", "PascalCase"

    # Response preferences
    response_verbosity: str = "medium"  # "brief", "medium", "detailed"
    include_explanations: bool = True
    include_examples: bool = True
    preferred_response_format: str = "markdown"

    # Tool usage preferences
    favorite_tools: list[str] = field(default_factory=list)
    auto_approve_edits: bool = False
    prefer_streaming: bool = True

    # Workspace preferences
    common_file_patterns: list[str] = field(default_factory=list)
    ignored_directories: list[str] = field(default_factory=list)

    # Learning metadata
    total_interactions: int = 0
    last_interaction: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferred_languages": self.preferred_languages,
            "indentation_style": self.indentation_style,
            "indent_size": self.indent_size,
            "quote_style": self.quote_style,
            "naming_convention": self.naming_convention,
            "response_verbosity": self.response_verbosity,
            "include_explanations": self.include_explanations,
            "include_examples": self.include_examples,
            "preferred_response_format": self.preferred_response_format,
            "favorite_tools": self.favorite_tools,
            "auto_approve_edits": self.auto_approve_edits,
            "prefer_streaming": self.prefer_streaming,
            "common_file_patterns": self.common_file_patterns,
            "ignored_directories": self.ignored_directories,
            "total_interactions": self.total_interactions,
            "last_interaction": self.last_interaction,
        }


class PreferenceLearner:
    """
    Learns user preferences from interactions.

    Features:
    - Observes coding patterns and style
    - Tracks tool usage preferences
    - Adapts response format to user preferences
    - Remembers workspace-specific settings
    """

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_db()

        # Pattern extractors
        self._extractors = {
            "coding_style": self._extract_coding_style,
            "response_preference": self._extract_response_preference,
            "tool_usage": self._extract_tool_usage,
        }

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()

        with self._write_lock:
            conn.executescript("""
                -- User preferences
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferences_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Learned patterns
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    observation_count INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, pattern_name, pattern_type)
                );

                CREATE INDEX IF NOT EXISTS idx_patterns_user
                    ON learned_patterns(user_id);

                -- Interaction history (for learning)
                CREATE TABLE IF NOT EXISTS interaction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_interactions_user
                    ON interaction_history(user_id);
                CREATE INDEX IF NOT EXISTS idx_interactions_time
                    ON interaction_history(timestamp DESC);
            """)
            conn.commit()

    async def observe_interaction(
        self,
        user_id: str,
        interaction_type: str,
        data: dict[str, Any],
    ) -> list[LearnedPattern]:
        """
        Observe an interaction and extract patterns.

        Args:
            user_id: User ID
            interaction_type: Type of interaction (chat, edit, tool_use, etc.)
            data: Interaction data

        Returns:
            List of newly learned or updated patterns
        """
        now = datetime.utcnow().isoformat()
        learned = []

        conn = self._get_conn()

        # Store interaction
        with self._write_lock:
            conn.execute("""
                INSERT INTO interaction_history
                (user_id, interaction_type, data_json, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, interaction_type, json.dumps(data), now))
            conn.commit()

        # Extract patterns based on interaction type
        if interaction_type == "code_edit":
            learned.extend(await self._learn_from_code_edit(user_id, data))

        elif interaction_type == "chat_response":
            learned.extend(await self._learn_from_chat(user_id, data))

        elif interaction_type == "tool_use":
            learned.extend(await self._learn_from_tool_use(user_id, data))

        elif interaction_type == "feedback":
            learned.extend(await self._learn_from_feedback(user_id, data))

        # Update user preferences
        await self._update_preferences(user_id, learned)

        return learned

    async def _learn_from_code_edit(
        self,
        user_id: str,
        data: dict[str, Any],
    ) -> list[LearnedPattern]:
        """Learn from code edit interactions."""
        learned = []
        code = data.get("code", "")
        language = data.get("language", "")
        file_path = data.get("file_path", "")

        # Learn language preference
        if language:
            pattern = await self._update_pattern(
                user_id=user_id,
                pattern_name=f"language_{language}",
                pattern_type="coding_style",
                value={"language": language, "file_extension": Path(file_path).suffix if file_path else ""},
            )
            learned.append(pattern)

        # Learn indentation style
        if code:
            indent_info = self._detect_indentation(code)
            if indent_info:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="indentation",
                    pattern_type="coding_style",
                    value=indent_info,
                )
                learned.append(pattern)

            # Learn quote style
            quote_style = self._detect_quote_style(code)
            if quote_style:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="quote_style",
                    pattern_type="coding_style",
                    value={"style": quote_style},
                )
                learned.append(pattern)

            # Learn naming convention
            naming = self._detect_naming_convention(code, language)
            if naming:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="naming_convention",
                    pattern_type="coding_style",
                    value={"convention": naming},
                )
                learned.append(pattern)

        return learned

    async def _learn_from_chat(
        self,
        user_id: str,
        data: dict[str, Any],
    ) -> list[LearnedPattern]:
        """Learn from chat interactions."""
        learned = []
        response = data.get("response", "")
        accepted = data.get("accepted", True)

        # Learn response length preference
        if response:
            word_count = len(response.split())
            verbosity = "brief" if word_count < 50 else "detailed" if word_count > 300 else "medium"

            if accepted:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="response_verbosity",
                    pattern_type="response_preference",
                    value={"verbosity": verbosity, "word_count": word_count},
                )
                learned.append(pattern)

            # Learn explanation preference
            has_explanation = "because" in response.lower() or "this works by" in response.lower()
            if has_explanation and accepted:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="include_explanations",
                    pattern_type="response_preference",
                    value={"include": True},
                )
                learned.append(pattern)

            # Learn example preference
            has_example = "```" in response or "for example" in response.lower()
            if has_example and accepted:
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name="include_examples",
                    pattern_type="response_preference",
                    value={"include": True},
                )
                learned.append(pattern)

        return learned

    async def _learn_from_tool_use(
        self,
        user_id: str,
        data: dict[str, Any],
    ) -> list[LearnedPattern]:
        """Learn from tool usage."""
        learned = []
        tool_name = data.get("tool", "")
        success = data.get("success", True)

        if tool_name and success:
            pattern = await self._update_pattern(
                user_id=user_id,
                pattern_name=f"tool_{tool_name}",
                pattern_type="tool_usage",
                value={"tool": tool_name, "success_count": 1},
            )
            learned.append(pattern)

        return learned

    async def _learn_from_feedback(
        self,
        user_id: str,
        data: dict[str, Any],
    ) -> list[LearnedPattern]:
        """Learn from explicit user feedback."""
        learned = []
        feedback_type = data.get("type", "")
        positive = data.get("positive", True)

        # Explicit preferences
        if feedback_type == "verbosity":
            preference = data.get("preference", "medium")
            pattern = await self._update_pattern(
                user_id=user_id,
                pattern_name="response_verbosity_explicit",
                pattern_type="response_preference",
                value={"verbosity": preference, "explicit": True},
                confidence_boost=0.3 if positive else -0.2,
            )
            learned.append(pattern)

        elif feedback_type == "code_style":
            style = data.get("style", {})
            for key, value in style.items():
                pattern = await self._update_pattern(
                    user_id=user_id,
                    pattern_name=f"style_{key}",
                    pattern_type="coding_style",
                    value={key: value, "explicit": True},
                    confidence_boost=0.3 if positive else -0.2,
                )
                learned.append(pattern)

        return learned

    async def _update_pattern(
        self,
        user_id: str,
        pattern_name: str,
        pattern_type: str,
        value: Any,
        confidence_boost: float = 0.05,
    ) -> LearnedPattern:
        """Update or create a learned pattern."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            # Try to update existing
            cursor = conn.execute("""
                SELECT confidence, observation_count
                FROM learned_patterns
                WHERE user_id = ? AND pattern_name = ? AND pattern_type = ?
            """, (user_id, pattern_name, pattern_type))

            row = cursor.fetchone()

            if row:
                # Update existing
                new_confidence = min(0.99, max(0.01, row["confidence"] + confidence_boost))
                new_count = row["observation_count"] + 1

                conn.execute("""
                    UPDATE learned_patterns
                    SET value_json = ?,
                        confidence = ?,
                        observation_count = ?,
                        updated_at = ?
                    WHERE user_id = ? AND pattern_name = ? AND pattern_type = ?
                """, (
                    json.dumps(value), new_confidence, new_count, now,
                    user_id, pattern_name, pattern_type,
                ))
            else:
                # Create new
                new_confidence = 0.5 + confidence_boost
                new_count = 1

                conn.execute("""
                    INSERT INTO learned_patterns
                    (user_id, pattern_name, pattern_type, value_json, confidence, observation_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, pattern_name, pattern_type,
                    json.dumps(value), new_confidence, new_count, now, now,
                ))

            conn.commit()

        return LearnedPattern(
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            value=value,
            confidence=new_confidence,
            observation_count=new_count,
            last_updated=now,
        )

    async def _update_preferences(
        self,
        user_id: str,
        learned_patterns: list[LearnedPattern],
    ) -> None:
        """Update user preferences based on learned patterns."""
        if not learned_patterns:
            return

        prefs = await self.get_preferences(user_id)
        now = datetime.utcnow().isoformat()

        for pattern in learned_patterns:
            if pattern.confidence < 0.6:
                continue  # Not confident enough

            if pattern.pattern_type == "coding_style":
                if "language" in pattern.value:
                    lang = pattern.value["language"]
                    if lang not in prefs.preferred_languages:
                        prefs.preferred_languages.append(lang)
                        prefs.preferred_languages = prefs.preferred_languages[-5:]  # Keep last 5

                if pattern.pattern_name == "indentation":
                    prefs.indentation_style = pattern.value.get("style", prefs.indentation_style)
                    prefs.indent_size = pattern.value.get("size", prefs.indent_size)

                if pattern.pattern_name == "quote_style":
                    prefs.quote_style = pattern.value.get("style", prefs.quote_style)

                if pattern.pattern_name == "naming_convention":
                    prefs.naming_convention = pattern.value.get("convention", prefs.naming_convention)

            elif pattern.pattern_type == "response_preference":
                if "verbosity" in pattern.value:
                    prefs.response_verbosity = pattern.value["verbosity"]

                if pattern.pattern_name == "include_explanations":
                    prefs.include_explanations = pattern.value.get("include", True)

                if pattern.pattern_name == "include_examples":
                    prefs.include_examples = pattern.value.get("include", True)

            elif pattern.pattern_type == "tool_usage":
                tool = pattern.value.get("tool", "")
                if tool and tool not in prefs.favorite_tools:
                    prefs.favorite_tools.append(tool)
                    prefs.favorite_tools = prefs.favorite_tools[-10:]  # Keep last 10

        prefs.total_interactions += 1
        prefs.last_interaction = now

        # Save preferences
        await self._save_preferences(prefs)

    async def _save_preferences(self, prefs: UserPreferences) -> None:
        """Save user preferences."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            conn.execute("""
                INSERT INTO user_preferences
                (user_id, preferences_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    preferences_json = ?,
                    updated_at = ?
            """, (
                prefs.user_id, json.dumps(prefs.to_dict()), now, now,
                json.dumps(prefs.to_dict()), now,
            ))
            conn.commit()

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences."""
        conn = self._get_conn()

        row = conn.execute("""
            SELECT preferences_json
            FROM user_preferences
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if row:
            data = json.loads(row["preferences_json"])
            return UserPreferences(
                user_id=user_id,
                preferred_languages=data.get("preferred_languages", []),
                indentation_style=data.get("indentation_style", "spaces"),
                indent_size=data.get("indent_size", 4),
                quote_style=data.get("quote_style", "double"),
                naming_convention=data.get("naming_convention", "snake_case"),
                response_verbosity=data.get("response_verbosity", "medium"),
                include_explanations=data.get("include_explanations", True),
                include_examples=data.get("include_examples", True),
                preferred_response_format=data.get("preferred_response_format", "markdown"),
                favorite_tools=data.get("favorite_tools", []),
                auto_approve_edits=data.get("auto_approve_edits", False),
                prefer_streaming=data.get("prefer_streaming", True),
                common_file_patterns=data.get("common_file_patterns", []),
                ignored_directories=data.get("ignored_directories", []),
                total_interactions=data.get("total_interactions", 0),
                last_interaction=data.get("last_interaction", ""),
            )
        else:
            return UserPreferences(user_id=user_id)

    async def get_patterns(
        self,
        user_id: str,
        pattern_type: str | None = None,
        min_confidence: float = 0.5,
    ) -> list[LearnedPattern]:
        """Get learned patterns for a user."""
        conn = self._get_conn()

        sql = """
            SELECT pattern_name, pattern_type, value_json, confidence, observation_count, updated_at
            FROM learned_patterns
            WHERE user_id = ? AND confidence >= ?
        """
        params = [user_id, min_confidence]

        if pattern_type:
            sql += " AND pattern_type = ?"
            params.append(pattern_type)

        sql += " ORDER BY confidence DESC, observation_count DESC"

        patterns = []
        for row in conn.execute(sql, params):
            patterns.append(LearnedPattern(
                pattern_name=row["pattern_name"],
                pattern_type=row["pattern_type"],
                value=json.loads(row["value_json"]),
                confidence=row["confidence"],
                observation_count=row["observation_count"],
                last_updated=row["updated_at"],
            ))

        return patterns

    def _detect_indentation(self, code: str) -> dict[str, Any] | None:
        """Detect indentation style from code."""
        lines = code.split("\n")
        space_lines = 0
        tab_lines = 0
        indent_sizes = []

        for line in lines:
            if line.startswith("\t"):
                tab_lines += 1
            elif line.startswith("  "):
                space_lines += 1
                # Count leading spaces
                stripped = line.lstrip()
                if stripped:
                    indent = len(line) - len(stripped)
                    if indent > 0:
                        indent_sizes.append(indent)

        if tab_lines > space_lines:
            return {"style": "tabs", "size": 1}
        elif space_lines > 0:
            # Find most common indent size
            if indent_sizes:
                from collections import Counter
                # Find GCD-like common divisor
                common = Counter(indent_sizes).most_common(3)
                if common:
                    likely_size = min(s for s, _ in common if s in [2, 4])
                    return {"style": "spaces", "size": likely_size}
            return {"style": "spaces", "size": 4}

        return None

    def _detect_quote_style(self, code: str) -> str | None:
        """Detect quote style from code."""
        single_count = code.count("'")
        double_count = code.count('"')

        # Exclude triple quotes
        single_count -= code.count("'''") * 3
        double_count -= code.count('"""') * 3

        if double_count > single_count * 1.5:
            return "double"
        elif single_count > double_count * 1.5:
            return "single"

        return None

    def _detect_naming_convention(self, code: str, language: str) -> str | None:
        """Detect naming convention from code."""
        import re

        # Extract identifiers (simplified)
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code)

        snake_count = sum(1 for i in identifiers if '_' in i and i.islower())
        camel_count = sum(1 for i in identifiers if i[0].islower() and any(c.isupper() for c in i))
        pascal_count = sum(1 for i in identifiers if i[0].isupper() and any(c.islower() for c in i))

        counts = [
            ("snake_case", snake_count),
            ("camelCase", camel_count),
            ("PascalCase", pascal_count),
        ]

        winner = max(counts, key=lambda x: x[1])
        if winner[1] > 5:  # Need at least 5 examples
            return winner[0]

        # Default based on language
        if language in ["python", "rust", "ruby"]:
            return "snake_case"
        elif language in ["javascript", "typescript", "java"]:
            return "camelCase"

        return None

    def _extract_coding_style(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract coding style patterns."""
        return []  # Implemented in _learn_from_code_edit

    def _extract_response_preference(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract response preference patterns."""
        return []  # Implemented in _learn_from_chat

    def _extract_tool_usage(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract tool usage patterns."""
        return []  # Implemented in _learn_from_tool_use


# Global instance
_learner: PreferenceLearner | None = None


def get_preference_learner() -> PreferenceLearner:
    """Get or create global preference learner."""
    global _learner

    if _learner is None:
        data_dir = Path.home() / ".magnetarcode/data"
        db_path = data_dir / "preferences.db"
        _learner = PreferenceLearner(db_path)

    return _learner
