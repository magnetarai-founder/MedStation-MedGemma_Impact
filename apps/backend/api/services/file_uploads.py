"""
File upload utilities placeholder.

To host validation, storage, and cleanup helpers migrated from main.py.
"""

from pathlib import Path


def ensure_upload_dir(path: Path) -> None:  # pragma: no cover - placeholder
    path.mkdir(parents=True, exist_ok=True)
