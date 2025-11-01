"""
Centralized Path Configuration for ElohimOS

All file paths are now configurable via environment variables.
This allows deployment flexibility and easier testing.

Environment Variables:
- ELOHIMOS_DATA_DIR: Base data directory (default: .neutron_data)
- ELOHIMOS_TEMP_DIR: Temporary files directory (default: temp_uploads)
- ELOHIMOS_EXPORTS_DIR: Export files directory (default: temp_exports)

Usage:
    from config_paths import PATHS

    memory_db = PATHS.memory_db
    uploads_dir = PATHS.uploads_dir
"""

import os
from pathlib import Path
from typing import Optional


class PathConfig:
    """
    Centralized path configuration with environment variable support
    """

    def __init__(self, base_dir: Optional[str] = None):
        # Base data directory (configurable via env var)
        self.data_dir = Path(base_dir or os.getenv("ELOHIMOS_DATA_DIR", ".neutron_data"))

        # Ensure base directory exists
        self.data_dir.mkdir(exist_ok=True)

    # ===== Database Paths =====
    # Consolidated: 3 databases total (was 7+)

    @property
    def app_db(self) -> Path:
        """Main application database (consolidated from auth, users, docs, chat, workflows)"""
        return self.data_dir / "elohimos_app.db"

    @property
    def vault_db(self) -> Path:
        """Vault database for secure storage (kept separate for security isolation)"""
        return self.data_dir / "vault.db"

    @property
    def datasets_dir(self) -> Path:
        """Datasets directory"""
        path = self.data_dir / "datasets"
        path.mkdir(exist_ok=True)
        return path

    @property
    def datasets_db(self) -> Path:
        """Datasets database (kept separate for easy backup/restore)"""
        return self.datasets_dir / "datasets.db"

    # ===== Backwards Compatibility Aliases =====
    # All these now point to the consolidated app database

    @property
    def memory_dir(self) -> Path:
        """Memory/chat storage directory"""
        path = self.data_dir / "memory"
        path.mkdir(exist_ok=True)
        return path

    @property
    def memory_db(self) -> Path:
        """Chat memory database"""
        return self.memory_dir / "chat_memory.db"

    @property
    def users_db(self) -> Path:
        """Users database (now in app_db)"""
        return self.app_db

    @property
    def auth_db(self) -> Path:
        """Auth database (now in app_db)"""
        return self.app_db

    @property
    def docs_db(self) -> Path:
        """Documents database (now in app_db)"""
        return self.app_db

    @property
    def workflows_db(self) -> Path:
        """Workflows database (now in app_db)"""
        return self.app_db

    @property
    def p2p_chat_db(self) -> Path:
        """P2P chat database (now in app_db)"""
        return self.app_db

    # ===== Upload and Storage Directories =====

    @property
    def uploads_dir(self) -> Path:
        """Chat uploads directory"""
        path = self.data_dir / "uploads"
        path.mkdir(exist_ok=True)
        return path

    @property
    def shared_files_dir(self) -> Path:
        """P2P shared files directory"""
        path = self.data_dir / "shared_files"
        path.mkdir(exist_ok=True)
        return path

    @property
    def cache_dir(self) -> Path:
        """Cache directory"""
        path = self.data_dir / "cache"
        path.mkdir(exist_ok=True)
        return path

    @property
    def chats_dir(self) -> Path:
        """Chats export directory"""
        path = self.data_dir / "chats"
        path.mkdir(exist_ok=True)
        return path

    @property
    def p2p_dir(self) -> Path:
        """P2P data directory"""
        path = self.data_dir / "p2p"
        path.mkdir(exist_ok=True)
        return path

    @property
    def code_dir(self) -> Path:
        """Code files directory"""
        path = self.data_dir / "code"
        path.mkdir(exist_ok=True)
        return path

    # ===== Temporary Directories =====

    @property
    def temp_uploads_dir(self) -> Path:
        """Temporary uploads directory (configurable)"""
        temp_dir = Path(os.getenv("ELOHIMOS_TEMP_DIR", "temp_uploads"))
        temp_dir.mkdir(exist_ok=True)
        return temp_dir

    @property
    def temp_exports_dir(self) -> Path:
        """Temporary exports directory (configurable)"""
        exports_dir = Path(os.getenv("ELOHIMOS_EXPORTS_DIR", "temp_exports"))
        exports_dir.mkdir(exist_ok=True)
        return exports_dir

    # ===== Other Files =====

    @property
    def model_favorites(self) -> Path:
        """Model favorites JSON file"""
        return self.data_dir / "model_favorites.json"

    # ===== Helper Methods =====

    def get_full_path(self, relative_path: str) -> Path:
        """
        Convert a relative path to a full path within the data directory

        Example:
            PATHS.get_full_path("memory/chat_memory.db")
        """
        return self.data_dir / relative_path

    def exists(self, path: Path) -> bool:
        """Check if a path exists"""
        return path.exists()

    def __repr__(self) -> str:
        return f"PathConfig(data_dir='{self.data_dir}')"


# ===== Global Instance =====

# Single global instance for all modules to use
PATHS = PathConfig()


# ===== Backwards Compatibility Helpers =====

def get_config_paths() -> PathConfig:
    """Get the global PathConfig instance"""
    return PATHS

def get_memory_dir() -> Path:
    """Get memory directory (backwards compatibility)"""
    return PATHS.memory_dir  # Now properly defined in PathConfig

def get_data_dir() -> Path:
    """Get base data directory (backwards compatibility)"""
    return PATHS.data_dir

def get_uploads_dir() -> Path:
    """Get uploads directory (backwards compatibility)"""
    return PATHS.uploads_dir
