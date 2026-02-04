"""
Configuration for the Auto-Healing Test System.

Provides configurable settings for healing behavior, confidence thresholds,
and framework-specific options.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from enum import Enum


class HealingMode(Enum):
    """Modes for auto-healing behavior."""
    AGGRESSIVE = "aggressive"  # Auto-fix everything with confidence >= 0.5
    BALANCED = "balanced"      # Auto-fix with confidence >= 0.7 (default)
    CONSERVATIVE = "conservative"  # Auto-fix only with confidence >= 0.9
    DRY_RUN = "dry_run"       # Analyze only, no fixes applied


@dataclass
class AutoHealerConfig:
    """Configuration for the AutoHealer system."""

    # Healing behavior
    mode: HealingMode = HealingMode.BALANCED
    max_healing_attempts: int = 3
    verify_fixes: bool = True

    # Confidence thresholds (0.0 to 1.0)
    min_confidence_import_fix: float = 0.9
    min_confidence_update_expected: float = 0.7
    min_confidence_update_mock: float = 0.8
    min_confidence_adjust_assertion: float = 0.5

    # Timeouts (seconds)
    test_execution_timeout: int = 60
    verification_timeout: int = 30

    # File patterns
    python_test_patterns: List[str] = field(default_factory=lambda: [
        "**/test_*.py",
        "**/*_test.py",
        "**/tests.py"
    ])

    typescript_test_patterns: List[str] = field(default_factory=lambda: [
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.spec.ts",
        "**/*.spec.tsx"
    ])

    # Exclusions
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/node_modules/**",
        "**/venv/**",
        "**/.venv/**",
        "**/build/**",
        "**/dist/**"
    ])

    # Test frameworks
    pytest_args: List[str] = field(default_factory=lambda: [
        '-v',
        '--tb=short',
        '--no-header'
    ])

    jest_args: List[str] = field(default_factory=lambda: [
        '--verbose',
        '--no-coverage'
    ])

    # Reporting
    generate_reports: bool = True
    export_json: bool = True
    report_directory: Optional[Path] = None

    # Safety features
    backup_before_fix: bool = True
    require_git_clean: bool = False
    dry_run_by_default: bool = False

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # Advanced options
    parallel_healing: bool = False
    max_parallel_workers: int = 4
    cache_analysis_results: bool = True
    cache_ttl_seconds: int = 3600

    # Strategy-specific settings
    import_fix_enabled: bool = True
    expected_value_update_enabled: bool = True
    mock_update_enabled: bool = True
    assertion_adjustment_enabled: bool = True
    code_fix_suggestions_enabled: bool = True

    # Heuristics tuning
    intentional_change_indicators: Set[str] = field(default_factory=lambda: {
        'refactor',
        'update',
        'change',
        'modify',
        'improve',
        'enhance'
    })

    # File change tracking
    track_changes: bool = True
    create_backup_suffix: str = ".backup"
    max_backups: int = 5

    def get_min_confidence_for_mode(self) -> float:
        """Get minimum confidence threshold based on mode."""
        thresholds = {
            HealingMode.AGGRESSIVE: 0.5,
            HealingMode.BALANCED: 0.7,
            HealingMode.CONSERVATIVE: 0.9,
            HealingMode.DRY_RUN: 1.0  # Never auto-fix in dry-run
        }
        return thresholds.get(self.mode, 0.7)

    def should_auto_fix(self, confidence: float, strategy_enabled: bool = True) -> bool:
        """
        Determine if a fix should be auto-applied.

        Args:
            confidence: Confidence score (0.0 to 1.0)
            strategy_enabled: Whether the specific strategy is enabled

        Returns:
            True if fix should be auto-applied
        """
        if self.mode == HealingMode.DRY_RUN:
            return False

        if not strategy_enabled:
            return False

        min_confidence = self.get_min_confidence_for_mode()
        return confidence >= min_confidence

    def get_test_patterns(self, language: str = "python") -> List[str]:
        """
        Get test file patterns for a specific language.

        Args:
            language: "python" or "typescript"

        Returns:
            List of glob patterns
        """
        if language.lower() in ["python", "py"]:
            return self.python_test_patterns
        elif language.lower() in ["typescript", "ts", "javascript", "js"]:
            return self.typescript_test_patterns
        else:
            return self.python_test_patterns + self.typescript_test_patterns

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'mode': self.mode.value,
            'max_healing_attempts': self.max_healing_attempts,
            'verify_fixes': self.verify_fixes,
            'min_confidence_import_fix': self.min_confidence_import_fix,
            'min_confidence_update_expected': self.min_confidence_update_expected,
            'min_confidence_update_mock': self.min_confidence_update_mock,
            'min_confidence_adjust_assertion': self.min_confidence_adjust_assertion,
            'test_execution_timeout': self.test_execution_timeout,
            'verification_timeout': self.verification_timeout,
            'generate_reports': self.generate_reports,
            'export_json': self.export_json,
            'backup_before_fix': self.backup_before_fix,
            'parallel_healing': self.parallel_healing,
            'max_parallel_workers': self.max_parallel_workers
        }

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'AutoHealerConfig':
        """Create configuration from dictionary."""
        # Convert mode string to enum if needed
        if 'mode' in config_dict and isinstance(config_dict['mode'], str):
            config_dict['mode'] = HealingMode(config_dict['mode'])

        return cls(**config_dict)

    @classmethod
    def load_from_file(cls, config_file: Path) -> 'AutoHealerConfig':
        """Load configuration from JSON/YAML file."""
        import json

        with open(config_file, 'r') as f:
            config_dict = json.load(f)

        return cls.from_dict(config_dict)

    def save_to_file(self, config_file: Path) -> None:
        """Save configuration to JSON file."""
        import json

        with open(config_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# Predefined configurations
AGGRESSIVE_CONFIG = AutoHealerConfig(
    mode=HealingMode.AGGRESSIVE,
    min_confidence_import_fix=0.5,
    min_confidence_update_expected=0.5,
    min_confidence_update_mock=0.5,
    min_confidence_adjust_assertion=0.4,
    verify_fixes=True,
    backup_before_fix=True
)

BALANCED_CONFIG = AutoHealerConfig(
    mode=HealingMode.BALANCED,
    min_confidence_import_fix=0.9,
    min_confidence_update_expected=0.7,
    min_confidence_update_mock=0.8,
    min_confidence_adjust_assertion=0.6,
    verify_fixes=True,
    backup_before_fix=True
)

CONSERVATIVE_CONFIG = AutoHealerConfig(
    mode=HealingMode.CONSERVATIVE,
    min_confidence_import_fix=0.95,
    min_confidence_update_expected=0.9,
    min_confidence_update_mock=0.9,
    min_confidence_adjust_assertion=0.8,
    verify_fixes=True,
    backup_before_fix=True,
    require_git_clean=True
)

DRY_RUN_CONFIG = AutoHealerConfig(
    mode=HealingMode.DRY_RUN,
    verify_fixes=False,
    backup_before_fix=False,
    dry_run_by_default=True
)

# Default configuration
DEFAULT_CONFIG = BALANCED_CONFIG


def get_config(mode: str = "balanced") -> AutoHealerConfig:
    """
    Get a predefined configuration by name.

    Args:
        mode: Configuration mode ("aggressive", "balanced", "conservative", "dry_run")

    Returns:
        AutoHealerConfig instance
    """
    configs = {
        "aggressive": AGGRESSIVE_CONFIG,
        "balanced": BALANCED_CONFIG,
        "conservative": CONSERVATIVE_CONFIG,
        "dry_run": DRY_RUN_CONFIG
    }

    return configs.get(mode.lower(), BALANCED_CONFIG)


# Example usage
if __name__ == "__main__":
    # Create a custom configuration
    config = AutoHealerConfig(
        mode=HealingMode.BALANCED,
        max_healing_attempts=5,
        verify_fixes=True
    )

    print("Configuration:")
    print(f"  Mode: {config.mode.value}")
    print(f"  Max attempts: {config.max_healing_attempts}")
    print(f"  Min confidence: {config.get_min_confidence_for_mode()}")

    # Test auto-fix decision
    print(f"\nShould auto-fix at 0.8 confidence? {config.should_auto_fix(0.8)}")
    print(f"Should auto-fix at 0.5 confidence? {config.should_auto_fix(0.5)}")

    # Save configuration
    config.save_to_file(Path("auto_healer_config.json"))
    print("\nConfiguration saved to auto_healer_config.json")
