"""
Application settings models and management.

This module defines the AppSettings model and provides functions to load/save
settings from the ElohimOS memory system.
"""

from pydantic import BaseModel

# Import ElohimOS memory (will be initialized in main.py)
_elohimos_memory = None


def set_elohimos_memory(memory) -> None:
    """Set the ElohimOS memory instance (called from main.py during initialization)"""
    global _elohimos_memory
    _elohimos_memory = memory


class AppSettings(BaseModel):
    # Performance & Memory
    max_file_size_mb: int = 1000
    enable_chunked_processing: bool = True
    chunk_size_rows: int = 50000
    app_memory_percent: int = 35
    processing_memory_percent: int = 50
    cache_memory_percent: int = 15

    # Default Download Options
    sql_default_format: str = "excel"
    json_default_format: str = "excel"
    json_auto_safe: bool = True
    json_max_depth: int = 5
    json_flatten_arrays: bool = False
    json_preserve_nulls: bool = True

    # Naming Patterns
    naming_pattern_global: str = "{name}_{YYYYMMDD}"
    naming_pattern_sql_excel: str | None = None
    naming_pattern_sql_csv: str | None = None
    naming_pattern_sql_tsv: str | None = None
    naming_pattern_sql_parquet: str | None = None
    naming_pattern_sql_json: str | None = None
    naming_pattern_json_excel: str | None = None
    naming_pattern_json_csv: str | None = None
    naming_pattern_json_tsv: str | None = None
    naming_pattern_json_parquet: str | None = None

    # Automation & Workflows
    automation_enabled: bool = True
    auto_save_interval_seconds: int = 300
    auto_backup_enabled: bool = True
    workflow_execution_enabled: bool = True

    # Database Performance
    database_cache_size_mb: int = 256
    max_query_timeout_seconds: int = 300
    enable_query_optimization: bool = True

    # Power User Features
    enable_semantic_search: bool = False
    semantic_similarity_threshold: float = 0.7
    show_keyboard_shortcuts: bool = False
    enable_bulk_operations: bool = False

    # Session
    session_timeout_hours: int = 24
    clear_temp_on_close: bool = True


def load_app_settings() -> AppSettings:
    """
    Load settings from database.

    Returns:
        AppSettings instance with stored settings or defaults
    """
    if _elohimos_memory is None:
        return AppSettings()

    stored = _elohimos_memory.get_all_settings()
    if stored:
        # Merge stored settings with defaults
        defaults = AppSettings().dict()
        defaults.update(stored)
        return AppSettings(**defaults)
    return AppSettings()


def save_app_settings(settings: AppSettings) -> None:
    """
    Save settings to database.

    Args:
        settings: AppSettings instance to save
    """
    if _elohimos_memory is None:
        raise RuntimeError("ElohimOS memory not initialized")

    _elohimos_memory.set_all_settings(settings.dict())
