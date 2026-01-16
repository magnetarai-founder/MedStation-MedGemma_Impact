"""
Accessibility Package

Accessibility preferences management for ElohimOS:
- Colorblind mode support
- High contrast themes
- Font size adjustments
- Animation preferences
"""

from api.accessibility.types import (
    ColorblindType,
    ThemeVariant,
    FontSize,
    StatusIndicatorStyle,
    AccessibilityPreferences,
)
from api.accessibility.service import AccessibilityService

__all__ = [
    "ColorblindType",
    "ThemeVariant",
    "FontSize",
    "StatusIndicatorStyle",
    "AccessibilityPreferences",
    "AccessibilityService",
]
