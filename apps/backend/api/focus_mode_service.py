"""
Focus Mode Service

Manages three focus modes for ElohimOS:
- 🌙 Quiet Mode: Muted colors, subtle animations, distraction-free
- ⚡ Field Mode: High contrast, battery saver, optimized for outdoor use
- 🚨 Emergency Mode: Critical functions only, auto-trigger on low battery

Features:
- Focus mode state persistence
- Auto-trigger logic (battery monitor, panic mode)
- Audit logging of mode changes
- User preferences per mode
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import sqlite3
import json
from pathlib import Path
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FocusMode(str, Enum):
    """Focus mode types"""
    QUIET = "quiet"
    FIELD = "field"
    EMERGENCY = "emergency"


class FocusModeConfig(BaseModel):
    """Configuration for a focus mode"""
    mode: FocusMode
    enabled: bool = True
    auto_trigger_battery: Optional[int] = None  # Battery % to auto-trigger
    auto_trigger_panic: bool = False  # Trigger on panic mode
    preferences: Dict[str, Any] = {}


class FocusModeState(BaseModel):
    """Current focus mode state"""
    current_mode: FocusMode
    previous_mode: Optional[FocusMode] = None
    changed_at: str
    changed_by: Optional[str] = None
    trigger_reason: Optional[str] = None  # "manual", "battery", "panic"
    battery_level: Optional[int] = None


class FocusModeService:
    """
    Service for managing focus modes
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize focus mode service

        Args:
            db_path: Path to database (defaults to data dir)
        """
        if db_path is None:
            from config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "elohimos_app.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize focus mode tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Focus mode state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_mode_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_mode TEXT NOT NULL DEFAULT 'field',
                previous_mode TEXT,
                changed_at TEXT NOT NULL,
                changed_by TEXT,
                trigger_reason TEXT,
                battery_level INTEGER
            )
        """)

        # Focus mode configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_mode_config (
                mode TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                auto_trigger_battery INTEGER,
                auto_trigger_panic INTEGER DEFAULT 0,
                preferences TEXT
            )
        """)

        # Focus mode history (for analytics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_mode_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                trigger_reason TEXT,
                battery_level INTEGER,
                changed_at TEXT NOT NULL,
                changed_by TEXT,
                duration_seconds INTEGER
            )
        """)

        # Insert default state if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO focus_mode_state (id, current_mode, changed_at)
            VALUES (1, 'field', ?)
        """, (datetime.utcnow().isoformat(),))

        # Insert default configurations
        for mode in FocusMode:
            auto_battery = 10 if mode == FocusMode.EMERGENCY else None
            cursor.execute("""
                INSERT OR IGNORE INTO focus_mode_config (mode, auto_trigger_battery, auto_trigger_panic)
                VALUES (?, ?, ?)
            """, (mode.value, auto_battery, 1 if mode == FocusMode.EMERGENCY else 0))

        conn.commit()
        conn.close()

        logger.info("Focus mode service initialized")

    def get_current_mode(self) -> FocusModeState:
        """
        Get current focus mode state

        Returns:
            Current focus mode state
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT current_mode, previous_mode, changed_at, changed_by, trigger_reason, battery_level
            FROM focus_mode_state
            WHERE id = 1
        """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return FocusModeState(
                current_mode=FocusMode(row[0]),
                previous_mode=FocusMode(row[1]) if row[1] else None,
                changed_at=row[2],
                changed_by=row[3],
                trigger_reason=row[4],
                battery_level=row[5]
            )

        # Fallback to default
        return FocusModeState(
            current_mode=FocusMode.FIELD,
            changed_at=datetime.utcnow().isoformat()
        )

    def set_mode(
        self,
        mode: FocusMode,
        user_id: Optional[str] = None,
        trigger_reason: str = "manual",
        battery_level: Optional[int] = None
    ) -> FocusModeState:
        """
        Set focus mode

        Args:
            mode: New focus mode
            user_id: User making the change
            trigger_reason: Reason for change ("manual", "battery", "panic")
            battery_level: Current battery level

        Returns:
            New focus mode state
        """
        current_state = self.get_current_mode()

        # Don't change if already in this mode
        if current_state.current_mode == mode:
            return current_state

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = datetime.utcnow().isoformat()

        # Calculate duration of previous mode
        if current_state.changed_at:
            try:
                prev_time = datetime.fromisoformat(current_state.changed_at)
                now_time = datetime.utcnow()
                duration = int((now_time - prev_time).total_seconds())
            except (ValueError, TypeError):
                duration = None
        else:
            duration = None

        # Record history entry for previous mode
        cursor.execute("""
            INSERT INTO focus_mode_history
            (mode, trigger_reason, battery_level, changed_at, changed_by, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            current_state.current_mode.value,
            current_state.trigger_reason,
            current_state.battery_level,
            current_state.changed_at,
            current_state.changed_by,
            duration
        ))

        # Update current state
        cursor.execute("""
            UPDATE focus_mode_state
            SET current_mode = ?,
                previous_mode = ?,
                changed_at = ?,
                changed_by = ?,
                trigger_reason = ?,
                battery_level = ?
            WHERE id = 1
        """, (
            mode.value,
            current_state.current_mode.value,
            timestamp,
            user_id,
            trigger_reason,
            battery_level
        ))

        conn.commit()
        conn.close()

        logger.info(f"Focus mode changed: {current_state.current_mode.value} → {mode.value} (reason: {trigger_reason})")

        # Log to audit system if available
        try:
            from audit_logger import audit_log_sync, AuditAction
            audit_log_sync(
                user_id=user_id or "system",
                action=AuditAction.SETTINGS_CHANGED,
                resource="focus_mode",
                resource_id=mode.value,
                details={
                    "previous_mode": current_state.current_mode.value,
                    "new_mode": mode.value,
                    "trigger_reason": trigger_reason,
                    "battery_level": battery_level
                }
            )
        except Exception as e:
            logger.debug(f"Could not log to audit: {e}")

        return FocusModeState(
            current_mode=mode,
            previous_mode=current_state.current_mode,
            changed_at=timestamp,
            changed_by=user_id,
            trigger_reason=trigger_reason,
            battery_level=battery_level
        )

    def get_mode_config(self, mode: FocusMode) -> FocusModeConfig:
        """
        Get configuration for a focus mode

        Args:
            mode: Focus mode

        Returns:
            Mode configuration
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT enabled, auto_trigger_battery, auto_trigger_panic, preferences
            FROM focus_mode_config
            WHERE mode = ?
        """, (mode.value,))

        row = cursor.fetchone()
        conn.close()

        if row:
            preferences = json.loads(row[3]) if row[3] else {}
            return FocusModeConfig(
                mode=mode,
                enabled=bool(row[0]),
                auto_trigger_battery=row[1],
                auto_trigger_panic=bool(row[2]),
                preferences=preferences
            )

        # Default config
        return FocusModeConfig(mode=mode)

    def update_mode_config(self, config: FocusModeConfig) -> FocusModeConfig:
        """
        Update configuration for a focus mode

        Args:
            config: New configuration

        Returns:
            Updated configuration
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        preferences_json = json.dumps(config.preferences) if config.preferences else None

        cursor.execute("""
            UPDATE focus_mode_config
            SET enabled = ?,
                auto_trigger_battery = ?,
                auto_trigger_panic = ?,
                preferences = ?
            WHERE mode = ?
        """, (
            int(config.enabled),
            config.auto_trigger_battery,
            int(config.auto_trigger_panic),
            preferences_json,
            config.mode.value
        ))

        conn.commit()
        conn.close()

        logger.info(f"Updated config for {config.mode.value}: auto_battery={config.auto_trigger_battery}, auto_panic={config.auto_trigger_panic}")

        return config

    def check_auto_trigger(self, battery_level: int, panic_mode_active: bool = False) -> Optional[FocusMode]:
        """
        Check if any mode should auto-trigger based on conditions

        Args:
            battery_level: Current battery level (0-100)
            panic_mode_active: Whether panic mode is active

        Returns:
            Mode to trigger, or None
        """
        # Check emergency mode first (highest priority)
        emergency_config = self.get_mode_config(FocusMode.EMERGENCY)
        if emergency_config.enabled:
            if panic_mode_active and emergency_config.auto_trigger_panic:
                return FocusMode.EMERGENCY
            if emergency_config.auto_trigger_battery and battery_level <= emergency_config.auto_trigger_battery:
                return FocusMode.EMERGENCY

        # Check field mode
        field_config = self.get_mode_config(FocusMode.FIELD)
        if field_config.enabled:
            if field_config.auto_trigger_battery and battery_level <= field_config.auto_trigger_battery:
                return FocusMode.FIELD

        # Check quiet mode
        quiet_config = self.get_mode_config(FocusMode.QUIET)
        if quiet_config.enabled:
            if quiet_config.auto_trigger_battery and battery_level <= quiet_config.auto_trigger_battery:
                return FocusMode.QUIET

        return None

    def get_mode_history(self, limit: int = 50) -> list:
        """
        Get focus mode change history

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of history entries
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT mode, trigger_reason, battery_level, changed_at, changed_by, duration_seconds
            FROM focus_mode_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "mode": row[0],
                "trigger_reason": row[1],
                "battery_level": row[2],
                "changed_at": row[3],
                "changed_by": row[4],
                "duration_seconds": row[5]
            })

        return history

    def get_mode_stats(self) -> Dict[str, Any]:
        """
        Get statistics about focus mode usage

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count changes per mode
        cursor.execute("""
            SELECT mode, COUNT(*), AVG(duration_seconds), SUM(duration_seconds)
            FROM focus_mode_history
            GROUP BY mode
        """)

        mode_stats = {}
        for row in cursor.fetchall():
            mode_stats[row[0]] = {
                "usage_count": row[1],
                "avg_duration_seconds": row[2],
                "total_duration_seconds": row[3]
            }

        # Count trigger reasons
        cursor.execute("""
            SELECT trigger_reason, COUNT(*)
            FROM focus_mode_history
            GROUP BY trigger_reason
        """)

        trigger_stats = {}
        for row in cursor.fetchall():
            if row[0]:
                trigger_stats[row[0]] = row[1]

        conn.close()

        return {
            "mode_usage": mode_stats,
            "trigger_reasons": trigger_stats
        }


# Global focus mode service instance
_focus_mode_service: Optional[FocusModeService] = None


def get_focus_mode_service() -> FocusModeService:
    """
    Get or create global focus mode service instance

    Returns:
        FocusModeService instance
    """
    global _focus_mode_service

    if _focus_mode_service is None:
        _focus_mode_service = FocusModeService()

    return _focus_mode_service
