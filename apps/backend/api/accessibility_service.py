"""
Compatibility Shim for Accessibility Service

The implementation now lives in the `api.accessibility` package:
- api.accessibility.service: AccessibilityService class

This shim maintains backward compatibility.
"""

from api.accessibility.service import AccessibilityService
from api.accessibility.types import (
    ColorblindType,
    ThemeVariant,
    FontSize,
    StatusIndicatorStyle,
    AccessibilityPreferences,
)

__all__ = [
    "AccessibilityService",
    "ColorblindType",
    "ThemeVariant",
    "FontSize",
    "StatusIndicatorStyle",
    "AccessibilityPreferences",
]
