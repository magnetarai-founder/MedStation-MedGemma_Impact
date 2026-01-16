"""
Accessibility Types - Enums and models for accessibility preferences

Extracted from accessibility_service.py during P2 decomposition.
Contains:
- ColorblindType enum (types of colorblindness)
- ThemeVariant enum (accessibility theme options)
- FontSize enum (font size presets)
- StatusIndicatorStyle model (indicator configuration)
- AccessibilityPreferences model (user preferences)
"""

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel


class ColorblindType(str, Enum):
    """Types of colorblindness

    Prevalence rates:
    - Protanopia/Protanomaly: ~2% of males
    - Deuteranopia/Deuteranomaly: ~6% of males
    - Tritanopia/Tritanomaly: ~0.02% of population
    - Achromatopsia: ~0.003% of population
    """
    NONE = "none"
    PROTANOPIA = "protanopia"  # Red-blind (1% males)
    DEUTERANOPIA = "deuteranopia"  # Green-blind (1% males)
    TRITANOPIA = "tritanopia"  # Blue-blind (0.01% population)
    PROTANOMALY = "protanomaly"  # Red-weak (1% males)
    DEUTERANOMALY = "deuteranomaly"  # Green-weak (5% males)
    TRITANOMALY = "tritanomaly"  # Blue-weak (0.01% population)
    ACHROMATOPSIA = "achromatopsia"  # Total colorblindness (0.003% population)


class ThemeVariant(str, Enum):
    """Theme variants for accessibility

    Options:
    - DEFAULT: Standard theme
    - HIGH_CONTRAST: Increased contrast for visibility
    - COLORBLIND_SAFE: Optimized for colorblind users
    - REDUCED_MOTION: Minimal animations
    - DARK_HIGH_CONTRAST: Dark theme with high contrast
    """
    DEFAULT = "default"
    HIGH_CONTRAST = "high_contrast"
    COLORBLIND_SAFE = "colorblind_safe"
    REDUCED_MOTION = "reduced_motion"
    DARK_HIGH_CONTRAST = "dark_high_contrast"


class FontSize(str, Enum):
    """Font size presets

    Base sizes:
    - SMALL: 12px
    - MEDIUM: 14px (default)
    - LARGE: 16px
    - EXTRA_LARGE: 18px
    - ACCESSIBILITY: 20px
    """
    SMALL = "small"  # 12px base
    MEDIUM = "medium"  # 14px base (default)
    LARGE = "large"  # 16px base
    EXTRA_LARGE = "extra_large"  # 18px base
    ACCESSIBILITY = "accessibility"  # 20px base


class StatusIndicatorStyle(BaseModel):
    """Configuration for status indicators

    Attributes:
        use_icons: Show status icons
        use_patterns: Use patterns in addition to colors
        use_text_labels: Show text labels
        high_contrast: Use high contrast colors
    """
    use_icons: bool = True
    use_patterns: bool = False
    use_text_labels: bool = False
    high_contrast: bool = False


class AccessibilityPreferences(BaseModel):
    """User accessibility preferences

    Attributes:
        user_id: User identifier
        colorblind_mode_enabled: Enable colorblind mode
        colorblind_type: Type of colorblindness
        theme_variant: Selected theme variant
        font_size: Font size preset
        high_contrast: Enable high contrast
        reduce_animations: Reduce motion/animations
        increase_click_areas: Larger clickable areas
        show_text_labels: Show text labels on icons
        keyboard_navigation: Enable keyboard navigation
        screen_reader_support: Optimize for screen readers
        status_indicator_style: Status indicator configuration
        custom_settings: Additional custom settings
        updated_at: Last update timestamp
    """
    user_id: str
    colorblind_mode_enabled: bool = False
    colorblind_type: ColorblindType = ColorblindType.NONE
    theme_variant: ThemeVariant = ThemeVariant.DEFAULT
    font_size: FontSize = FontSize.MEDIUM
    high_contrast: bool = False
    reduce_animations: bool = False
    increase_click_areas: bool = False
    show_text_labels: bool = False
    keyboard_navigation: bool = True
    screen_reader_support: bool = False
    status_indicator_style: StatusIndicatorStyle = StatusIndicatorStyle()
    custom_settings: Dict[str, Any] = {}
    updated_at: Optional[str] = None


__all__ = [
    # Enums
    "ColorblindType",
    "ThemeVariant",
    "FontSize",
    # Models
    "StatusIndicatorStyle",
    "AccessibilityPreferences",
]
