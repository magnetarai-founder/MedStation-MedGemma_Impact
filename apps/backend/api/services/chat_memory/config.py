"""
Configuration and constants for chat memory
"""
import os
from pathlib import Path

# Storage path for MagnetarCode
MEMORY_DIR = Path(os.path.expanduser("~/.magnetarcode/data"))
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Query performance logging threshold (log queries slower than this)
SLOW_QUERY_THRESHOLD_MS = 100
