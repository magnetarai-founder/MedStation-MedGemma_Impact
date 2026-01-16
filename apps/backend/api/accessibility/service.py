"""
Accessibility Preferences Service

Manages accessibility settings for improved usability:
- Colorblind mode (high contrast, patterns + colors)
- High contrast themes
- Font size adjustments
- Animation preferences
- Screen reader support
- Keyboard navigation settings

Features:
- User-specific accessibility preferences
- Theme variant management
- Status indicator configurations
- Persistent settings storage

Module structure (P2 decomposition):
- accessibility_types.py: Enums (ColorblindType, ThemeVariant, FontSize) and models
- accessibility_service.py: AccessibilityService class (this file)
"""

from typing import Optional
from datetime import datetime, UTC
import sqlite3
import json
from pathlib import Path
import logging

# Import from extracted module (P2 decomposition)
from api.accessibility.types import (
    ColorblindType,
    ThemeVariant,
    FontSize,
    StatusIndicatorStyle,
    AccessibilityPreferences,
)

logger = logging.getLogger(__name__)


class AccessibilityService:
    """
    Service for managing accessibility preferences
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize accessibility service

        Args:
            db_path: Path to database (defaults to data dir)
        """
        if db_path is None:
            from config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "elohimos_app.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize accessibility preferences table"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accessibility_preferences (
                user_id TEXT PRIMARY KEY,
                colorblind_mode_enabled INTEGER DEFAULT 0,
                colorblind_type TEXT DEFAULT 'none',
                theme_variant TEXT DEFAULT 'default',
                font_size TEXT DEFAULT 'medium',
                high_contrast INTEGER DEFAULT 0,
                reduce_animations INTEGER DEFAULT 0,
                increase_click_areas INTEGER DEFAULT 0,
                show_text_labels INTEGER DEFAULT 0,
                keyboard_navigation INTEGER DEFAULT 1,
                screen_reader_support INTEGER DEFAULT 0,
                status_indicator_style TEXT,
                custom_settings TEXT,
                updated_at TEXT
            )
        """)

        conn.commit()
        conn.close()

        logger.info("Accessibility service initialized")

    def get_preferences(self, user_id: str) -> AccessibilityPreferences:
        """
        Get accessibility preferences for a user

        Args:
            user_id: User ID

        Returns:
            Accessibility preferences (defaults if not found)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT colorblind_mode_enabled, colorblind_type, theme_variant, font_size,
                   high_contrast, reduce_animations, increase_click_areas, show_text_labels,
                   keyboard_navigation, screen_reader_support, status_indicator_style,
                   custom_settings, updated_at
            FROM accessibility_preferences
            WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            indicator_style = json.loads(row[10]) if row[10] else {}
            custom = json.loads(row[11]) if row[11] else {}

            return AccessibilityPreferences(
                user_id=user_id,
                colorblind_mode_enabled=bool(row[0]),
                colorblind_type=ColorblindType(row[1]),
                theme_variant=ThemeVariant(row[2]),
                font_size=FontSize(row[3]),
                high_contrast=bool(row[4]),
                reduce_animations=bool(row[5]),
                increase_click_areas=bool(row[6]),
                show_text_labels=bool(row[7]),
                keyboard_navigation=bool(row[8]),
                screen_reader_support=bool(row[9]),
                status_indicator_style=StatusIndicatorStyle(**indicator_style),
                custom_settings=custom,
                updated_at=row[12]
            )

        # Return defaults
        return AccessibilityPreferences(user_id=user_id)

    def update_preferences(self, preferences: AccessibilityPreferences) -> AccessibilityPreferences:
        """
        Update accessibility preferences for a user

        Args:
            preferences: New preferences

        Returns:
            Updated preferences
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        updated_at = datetime.now(UTC).isoformat()

        indicator_style_json = json.dumps(preferences.status_indicator_style.dict())
        custom_json = json.dumps(preferences.custom_settings) if preferences.custom_settings else None

        cursor.execute("""
            INSERT OR REPLACE INTO accessibility_preferences
            (user_id, colorblind_mode_enabled, colorblind_type, theme_variant, font_size,
             high_contrast, reduce_animations, increase_click_areas, show_text_labels,
             keyboard_navigation, screen_reader_support, status_indicator_style,
             custom_settings, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            preferences.user_id,
            int(preferences.colorblind_mode_enabled),
            preferences.colorblind_type.value,
            preferences.theme_variant.value,
            preferences.font_size.value,
            int(preferences.high_contrast),
            int(preferences.reduce_animations),
            int(preferences.increase_click_areas),
            int(preferences.show_text_labels),
            int(preferences.keyboard_navigation),
            int(preferences.screen_reader_support),
            indicator_style_json,
            custom_json,
            updated_at
        ))

        conn.commit()
        conn.close()

        preferences.updated_at = updated_at

        logger.info(f"Updated accessibility preferences for user {preferences.user_id}")

        # Log to audit system
        try:
            from audit_logger import audit_log_sync, AuditAction
            audit_log_sync(
                user_id=preferences.user_id,
                action=AuditAction.SETTINGS_CHANGED,
                resource="accessibility",
                resource_id=preferences.user_id,
                details={
                    "colorblind_mode": preferences.colorblind_mode_enabled,
                    "colorblind_type": preferences.colorblind_type.value,
                    "theme_variant": preferences.theme_variant.value,
                    "high_contrast": preferences.high_contrast
                }
            )
        except Exception as e:
            logger.debug(f"Could not log to audit: {e}")

        return preferences

    def enable_colorblind_mode(
        self,
        user_id: str,
        colorblind_type: ColorblindType
    ) -> AccessibilityPreferences:
        """
        Enable colorblind mode for a user

        Args:
            user_id: User ID
            colorblind_type: Type of colorblindness

        Returns:
            Updated preferences
        """
        prefs = self.get_preferences(user_id)
        prefs.colorblind_mode_enabled = True
        prefs.colorblind_type = colorblind_type

        # Auto-enable supporting features
        prefs.status_indicator_style.use_icons = True
        prefs.status_indicator_style.use_patterns = True
        prefs.show_text_labels = True

        # Use colorblind-safe theme
        if prefs.theme_variant == ThemeVariant.DEFAULT:
            prefs.theme_variant = ThemeVariant.COLORBLIND_SAFE

        return self.update_preferences(prefs)

    def enable_high_contrast(self, user_id: str) -> AccessibilityPreferences:
        """
        Enable high contrast mode for a user

        Args:
            user_id: User ID

        Returns:
            Updated preferences
        """
        prefs = self.get_preferences(user_id)
        prefs.high_contrast = True
        prefs.theme_variant = ThemeVariant.HIGH_CONTRAST
        prefs.status_indicator_style.high_contrast = True

        return self.update_preferences(prefs)

    def set_font_size(self, user_id: str, font_size: FontSize) -> AccessibilityPreferences:
        """
        Set font size for a user

        Args:
            user_id: User ID
            font_size: Font size preset

        Returns:
            Updated preferences
        """
        prefs = self.get_preferences(user_id)
        prefs.font_size = font_size

        return self.update_preferences(prefs)

    def get_theme_config(self, theme_variant: ThemeVariant) -> Dict[str, Any]:
        """
        Get theme configuration for a variant

        Args:
            theme_variant: Theme variant

        Returns:
            Theme configuration dictionary
        """
        themes = {
            ThemeVariant.DEFAULT: {
                "name": "Default",
                "colors": {
                    "success": "#10b981",  # Green
                    "error": "#ef4444",    # Red
                    "warning": "#f59e0b",  # Yellow
                    "info": "#3b82f6",     # Blue
                    "neutral": "#6b7280"   # Gray
                },
                "contrast_ratio": 4.5,
                "use_patterns": False
            },
            ThemeVariant.HIGH_CONTRAST: {
                "name": "High Contrast",
                "colors": {
                    "success": "#00ff00",  # Bright green
                    "error": "#ff0000",    # Bright red
                    "warning": "#ffff00",  # Bright yellow
                    "info": "#0000ff",     # Bright blue
                    "neutral": "#ffffff"   # White
                },
                "contrast_ratio": 7.0,
                "use_patterns": True
            },
            ThemeVariant.COLORBLIND_SAFE: {
                "name": "Colorblind Safe",
                "colors": {
                    "success": "#0173b2",  # Blue (universally distinct)
                    "error": "#de8f05",    # Orange (universally distinct)
                    "warning": "#cc78bc",  # Pink (universally distinct)
                    "info": "#029e73",     # Teal (universally distinct)
                    "neutral": "#949494"   # Gray
                },
                "contrast_ratio": 5.0,
                "use_patterns": True,
                "use_icons": True,
                "use_text_labels": True
            },
            ThemeVariant.REDUCED_MOTION: {
                "name": "Reduced Motion",
                "colors": {
                    "success": "#10b981",
                    "error": "#ef4444",
                    "warning": "#f59e0b",
                    "info": "#3b82f6",
                    "neutral": "#6b7280"
                },
                "contrast_ratio": 4.5,
                "disable_animations": True,
                "transition_duration": "0ms"
            },
            ThemeVariant.DARK_HIGH_CONTRAST: {
                "name": "Dark High Contrast",
                "colors": {
                    "success": "#00ff00",
                    "error": "#ff0000",
                    "warning": "#ffff00",
                    "info": "#00ffff",
                    "neutral": "#ffffff"
                },
                "background": "#000000",
                "foreground": "#ffffff",
                "contrast_ratio": 7.0,
                "use_patterns": True
            }
        }

        return themes.get(theme_variant, themes[ThemeVariant.DEFAULT])

    def get_status_indicator_config(
        self,
        preferences: AccessibilityPreferences
    ) -> Dict[str, Any]:
        """
        Get status indicator configuration based on preferences

        Args:
            preferences: User preferences

        Returns:
            Status indicator configuration
        """
        return {
            "success": {
                "icon": "✅" if preferences.status_indicator_style.use_icons else None,
                "color": "#10b981" if not preferences.colorblind_mode_enabled else "#0173b2",
                "pattern": "solid" if preferences.status_indicator_style.use_patterns else None,
                "text": "Success" if preferences.show_text_labels else None
            },
            "error": {
                "icon": "❌" if preferences.status_indicator_style.use_icons else None,
                "color": "#ef4444" if not preferences.colorblind_mode_enabled else "#de8f05",
                "pattern": "diagonal-stripes" if preferences.status_indicator_style.use_patterns else None,
                "text": "Error" if preferences.show_text_labels else None
            },
            "warning": {
                "icon": "⚠️" if preferences.status_indicator_style.use_icons else None,
                "color": "#f59e0b" if not preferences.colorblind_mode_enabled else "#cc78bc",
                "pattern": "dots" if preferences.status_indicator_style.use_patterns else None,
                "text": "Warning" if preferences.show_text_labels else None
            },
            "info": {
                "icon": "ℹ️" if preferences.status_indicator_style.use_icons else None,
                "color": "#3b82f6" if not preferences.colorblind_mode_enabled else "#029e73",
                "pattern": "horizontal-stripes" if preferences.status_indicator_style.use_patterns else None,
                "text": "Info" if preferences.show_text_labels else None
            },
            "paused": {
                "icon": "⏸️" if preferences.status_indicator_style.use_icons else None,
                "color": "#6b7280",
                "pattern": "checkerboard" if preferences.status_indicator_style.use_patterns else None,
                "text": "Paused" if preferences.show_text_labels else None
            },
            "syncing": {
                "icon": "🔄" if preferences.status_indicator_style.use_icons else None,
                "color": "#3b82f6",
                "pattern": "spinner" if preferences.status_indicator_style.use_patterns else None,
                "text": "Syncing" if preferences.show_text_labels else None,
                "animated": not preferences.reduce_animations
            }
        }


# Global accessibility service instance
_accessibility_service: Optional[AccessibilityService] = None


def get_accessibility_service() -> AccessibilityService:
    """
    Get or create global accessibility service instance

    Returns:
        AccessibilityService instance
    """
    global _accessibility_service

    if _accessibility_service is None:
        _accessibility_service = AccessibilityService()

    return _accessibility_service


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Service
    "AccessibilityService",
    "get_accessibility_service",
    # Re-exported from accessibility_types
    "ColorblindType",
    "ThemeVariant",
    "FontSize",
    "StatusIndicatorStyle",
    "AccessibilityPreferences",
]
