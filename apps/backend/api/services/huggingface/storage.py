"""
HuggingFace Storage Manager

Manages local storage for GGUF models downloaded from HuggingFace Hub.
Default location: ~/.magnetar/models/huggingface/
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HuggingFaceStorage:
    """
    Manages local GGUF model storage

    Directory structure:
    ~/.magnetar/
      models/
        huggingface/
          manifest.json           # Tracks all downloaded models
          google--medgemma-1.5-4b-it-GGUF/
            medgemma-1.5-4b-it-Q4_K_M.gguf
            model_info.json
          bartowski--Llama-3.2-3B-Instruct-GGUF/
            Llama-3.2-3B-Instruct-Q4_K_M.gguf
            model_info.json
    """

    DEFAULT_BASE_PATH = Path.home() / ".magnetar" / "models" / "huggingface"

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or self.DEFAULT_BASE_PATH
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"HuggingFace storage initialized at: {self.base_path}")

    @property
    def manifest_path(self) -> Path:
        """Path to the manifest file tracking all models"""
        return self.base_path / "manifest.json"

    def _load_manifest(self) -> Dict[str, Any]:
        """Load the manifest file"""
        if not self.manifest_path.exists():
            return {"version": 1, "models": {}, "updated_at": None}

        try:
            with open(self.manifest_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load manifest: {e}")
            return {"version": 1, "models": {}, "updated_at": None}

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save the manifest file"""
        manifest["updated_at"] = datetime.utcnow().isoformat()
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save manifest: {e}")

    def get_model_directory(self, repo_id: str) -> Path:
        """
        Get the directory for a specific model

        Args:
            repo_id: HuggingFace repo ID (e.g., 'google/medgemma-1.5-4b-it-GGUF')

        Returns:
            Path to the model directory
        """
        # Sanitize repo_id for filesystem (replace / with --)
        safe_name = repo_id.replace("/", "--")
        return self.base_path / safe_name

    def get_model_path(self, repo_id: str, filename: str) -> Path:
        """
        Get the full path to a specific GGUF file

        Args:
            repo_id: HuggingFace repo ID
            filename: GGUF filename

        Returns:
            Full path to the model file
        """
        return self.get_model_directory(repo_id) / filename

    def get_partial_path(self, repo_id: str, filename: str) -> Path:
        """
        Get the path to a partial download file

        Used for resumable downloads.
        """
        model_path = self.get_model_path(repo_id, filename)
        return model_path.with_suffix(model_path.suffix + ".partial")

    def is_model_downloaded(self, repo_id: str, filename: str) -> bool:
        """Check if a model is fully downloaded"""
        model_path = self.get_model_path(repo_id, filename)
        return model_path.exists()

    def get_partial_size(self, repo_id: str, filename: str) -> int:
        """Get size of partial download for resume support"""
        partial_path = self.get_partial_path(repo_id, filename)
        if partial_path.exists():
            return partial_path.stat().st_size
        return 0

    def register_model(
        self,
        repo_id: str,
        filename: str,
        size_bytes: int,
        quantization: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a downloaded model in the manifest

        Args:
            repo_id: HuggingFace repo ID
            filename: GGUF filename
            size_bytes: File size in bytes
            quantization: Quantization level (e.g., 'Q4_K_M')
            metadata: Additional model metadata
        """
        manifest = self._load_manifest()

        model_id = f"{repo_id}:{filename}"
        model_path = self.get_model_path(repo_id, filename)

        manifest["models"][model_id] = {
            "repo_id": repo_id,
            "filename": filename,
            "path": str(model_path),
            "size_bytes": size_bytes,
            "quantization": quantization,
            "downloaded_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        self._save_manifest(manifest)

        # Also save model info alongside the file
        model_dir = self.get_model_directory(repo_id)
        model_dir.mkdir(parents=True, exist_ok=True)

        info_path = model_dir / "model_info.json"
        try:
            with open(info_path, "w") as f:
                json.dump(manifest["models"][model_id], f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save model info: {e}")

        logger.info(f"Registered model: {model_id}")

    def unregister_model(self, repo_id: str, filename: str) -> bool:
        """
        Unregister a model and delete its files

        Args:
            repo_id: HuggingFace repo ID
            filename: GGUF filename

        Returns:
            True if model was found and deleted
        """
        manifest = self._load_manifest()
        model_id = f"{repo_id}:{filename}"

        if model_id not in manifest["models"]:
            return False

        # Delete the model file
        model_path = self.get_model_path(repo_id, filename)
        if model_path.exists():
            model_path.unlink()
            logger.info(f"Deleted model file: {model_path}")

        # Delete partial file if exists
        partial_path = self.get_partial_path(repo_id, filename)
        if partial_path.exists():
            partial_path.unlink()

        # Delete model info
        model_dir = self.get_model_directory(repo_id)
        info_path = model_dir / "model_info.json"
        if info_path.exists():
            info_path.unlink()

        # Remove empty directory
        try:
            if model_dir.exists() and not any(model_dir.iterdir()):
                model_dir.rmdir()
        except OSError:
            pass  # Directory not empty or other error

        # Update manifest
        del manifest["models"][model_id]
        self._save_manifest(manifest)

        logger.info(f"Unregistered model: {model_id}")
        return True

    def list_downloaded_models(self) -> List[Dict[str, Any]]:
        """
        List all downloaded models

        Returns:
            List of model info dictionaries
        """
        manifest = self._load_manifest()
        models = []

        for model_id, info in manifest["models"].items():
            # Verify file still exists
            model_path = Path(info["path"])
            if model_path.exists():
                info["exists"] = True
                info["actual_size"] = model_path.stat().st_size
            else:
                info["exists"] = False
                info["actual_size"] = 0

            models.append(info)

        return models

    def get_model_info(self, repo_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get info for a specific model"""
        manifest = self._load_manifest()
        model_id = f"{repo_id}:{filename}"
        return manifest["models"].get(model_id)

    def get_total_storage_used(self) -> int:
        """Get total storage used by all downloaded models in bytes"""
        total = 0
        for model in self.list_downloaded_models():
            if model.get("exists"):
                total += model.get("actual_size", 0)
        return total

    def get_storage_summary(self) -> Dict[str, Any]:
        """Get storage usage summary"""
        models = self.list_downloaded_models()
        total_bytes = sum(m.get("actual_size", 0) for m in models if m.get("exists"))

        return {
            "model_count": len([m for m in models if m.get("exists")]),
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / (1024**3), 2),
            "storage_path": str(self.base_path),
        }


# Singleton instance
_storage_instance: Optional[HuggingFaceStorage] = None


def get_huggingface_storage() -> HuggingFaceStorage:
    """Get the singleton HuggingFace storage instance"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = HuggingFaceStorage()
    return _storage_instance


__all__ = [
    "HuggingFaceStorage",
    "get_huggingface_storage",
]
