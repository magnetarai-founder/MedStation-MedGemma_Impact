"""
Model Catalog Service

Manages the global catalog of installed models on the system.
Source of truth is Ollama API, with local database caching.

Architecture:
- Ollama has 10 models installed (system-wide)
- Model catalog syncs from Ollama periodically
- Users choose which models they want to see (per-user preferences)
"""

import logging
import sqlite3
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelInfo:
    """Model information from catalog"""

    def __init__(
        self,
        model_name: str,
        size: Optional[str] = None,
        status: str = "installed",
        installed_at: Optional[str] = None,
        last_seen: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.model_name = model_name
        self.size = size
        self.status = status
        self.installed_at = installed_at
        self.last_seen = last_seen
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "model_name": self.model_name,
            "size": self.size,
            "status": self.status,
            "installed_at": self.installed_at,
            "last_seen": self.last_seen,
            "metadata": self.metadata
        }


class ModelCatalog:
    """
    Global model catalog service

    Maintains catalog of installed models by syncing with Ollama.
    """

    def __init__(self, db_path: Path, ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize model catalog

        Args:
            db_path: Path to SQLite database (elohim.db)
            ollama_base_url: Ollama API base URL
        """
        self.db_path = db_path
        self.ollama_base_url = ollama_base_url

    async def sync_from_ollama(self) -> bool:
        """
        Sync model catalog from Ollama

        Fetches installed models from Ollama and updates local catalog.

        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Query Ollama for installed models
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                data = response.json()

            models = data.get("models", [])
            logger.info(f"Fetched {len(models)} models from Ollama")

            if not models:
                logger.warning("No models found in Ollama")
                return True

            # Update catalog in database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.utcnow().isoformat()

            for model in models:
                model_name = model.get("name")
                if not model_name:
                    continue

                # Extract size
                size = model.get("size")
                if size is not None:
                    # Convert bytes to human-readable format
                    size_gb = size / (1024 ** 3)
                    size_str = f"{size_gb:.1f}GB"
                else:
                    size_str = None

                # Get modified_at
                modified_at = model.get("modified_at")

                cursor.execute("""
                    INSERT INTO model_installations
                    (model_name, size, status, installed_at, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(model_name) DO UPDATE SET
                        size = excluded.size,
                        status = 'installed',
                        last_seen = excluded.last_seen
                """, (
                    model_name,
                    size_str,
                    "installed",
                    modified_at or now,
                    now
                ))

            conn.commit()
            conn.close()

            logger.info(f"✓ Synced {len(models)} models to catalog")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models from Ollama: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to sync model catalog: {e}")
            return False

    def get_all_models(self) -> List[ModelInfo]:
        """
        Get all models from catalog

        Returns:
            List of ModelInfo objects
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT model_name, size, status, installed_at, last_seen
                FROM model_installations
                WHERE status = 'installed'
                ORDER BY model_name ASC
            """)

            rows = cursor.fetchall()
            conn.close()

            models = []
            for row in rows:
                models.append(ModelInfo(
                    model_name=row[0],
                    size=row[1],
                    status=row[2],
                    installed_at=row[3],
                    last_seen=row[4]
                ))

            return models

        except Exception as e:
            logger.error(f"Failed to get all models from catalog: {e}")
            return []

    def get_model_names(self) -> List[str]:
        """
        Get list of installed model names

        Returns:
            List of model names
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT model_name
                FROM model_installations
                WHERE status = 'installed'
                ORDER BY model_name ASC
            """)

            rows = cursor.fetchall()
            conn.close()

            return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to get model names: {e}")
            return []

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get specific model from catalog

        Args:
            model_name: Model name

        Returns:
            ModelInfo if found, None otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT model_name, size, status, installed_at, last_seen
                FROM model_installations
                WHERE model_name = ?
            """, (model_name,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return ModelInfo(
                model_name=row[0],
                size=row[1],
                status=row[2],
                installed_at=row[3],
                last_seen=row[4]
            )

        except Exception as e:
            logger.error(f"Failed to get model {model_name}: {e}")
            return None

    def update_model_status(self, model_name: str, status: str) -> bool:
        """
        Update model status

        Args:
            model_name: Model name
            status: New status (installed|downloading|failed|unknown)

        Returns:
            True if successful, False otherwise
        """
        try:
            if status not in ("installed", "downloading", "failed", "unknown"):
                logger.error(f"Invalid status: {status}")
                return False

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.utcnow().isoformat()

            cursor.execute("""
                UPDATE model_installations
                SET status = ?, last_seen = ?
                WHERE model_name = ?
            """, (status, now, model_name))

            conn.commit()
            conn.close()

            logger.debug(f"✓ Updated model {model_name} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update model status: {e}")
            return False


# Singleton instance (initialized by app startup)
_model_catalog: Optional[ModelCatalog] = None


def init_model_catalog(db_path: Path, ollama_base_url: str = "http://localhost:11434") -> ModelCatalog:
    """
    Initialize the global model catalog singleton

    Args:
        db_path: Path to SQLite database
        ollama_base_url: Ollama API base URL

    Returns:
        ModelCatalog instance
    """
    global _model_catalog
    _model_catalog = ModelCatalog(db_path, ollama_base_url)
    return _model_catalog


def get_model_catalog() -> ModelCatalog:
    """
    Get the global model catalog instance

    Returns:
        ModelCatalog instance

    Raises:
        RuntimeError: If catalog not initialized
    """
    if _model_catalog is None:
        raise RuntimeError("Model catalog not initialized. Call init_model_catalog() first.")
    return _model_catalog
