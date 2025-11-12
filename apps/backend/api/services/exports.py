"""
Result export utilities placeholder.

To host Excel/CSV/Parquet/JSON export helpers.
"""

from pathlib import Path


def ensure_exports_dir(path: Path) -> None:  # pragma: no cover - placeholder
    path.mkdir(parents=True, exist_ok=True)

