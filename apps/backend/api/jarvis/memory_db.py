"""
Jarvis Memory Database - Database schema and utility functions

Provides:
- Database schema DDL for memory tables
- Connection configuration (WAL mode, indexes)
- Embedding generation with multiple fallbacks
- Cosine similarity calculation
- Hash utilities

Extracted from jarvis_memory.py during P2 decomposition.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


# ===== Database Schema =====

COMMAND_MEMORY_TABLE = """
    CREATE TABLE IF NOT EXISTS command_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT NOT NULL,
        command_hash TEXT UNIQUE,
        embedding_json TEXT,  -- JSON array of floats
        task_type TEXT,
        tool_used TEXT,
        success BOOLEAN,
        execution_time REAL,
        context_json TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

PATTERN_TEMPLATES_TABLE = """
    CREATE TABLE IF NOT EXISTS pattern_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_name TEXT UNIQUE,
        pattern_sql TEXT,
        category TEXT,
        usage_count INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0,
        avg_execution_time REAL DEFAULT 0,
        last_used DATETIME
    )
"""

SEMANTIC_CLUSTERS_TABLE = """
    CREATE TABLE IF NOT EXISTS semantic_clusters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cluster_name TEXT,
        centroid_embedding TEXT,  -- JSON array
        member_commands TEXT,  -- JSON array of command IDs
        common_tools TEXT,  -- JSON array
        cluster_confidence REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

ERROR_SOLUTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS error_solutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        error_pattern TEXT,
        error_hash TEXT UNIQUE,
        solution_template TEXT,
        tool_suggestion TEXT,
        success_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        last_seen DATETIME
    )
"""

WORKFLOW_SEQUENCES_TABLE = """
    CREATE TABLE IF NOT EXISTS workflow_sequences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_name TEXT,
        command_sequence TEXT,  -- JSON array
        total_time REAL,
        success_rate REAL,
        usage_count INTEGER DEFAULT 0,
        last_executed DATETIME
    )
"""

SEMANTIC_MEMORY_TABLE = """
    CREATE TABLE IF NOT EXISTS semantic_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT,
        embedding TEXT,  -- JSON array
        context TEXT,  -- JSON object
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

CONTENT_CHUNKS_TABLE = """
    CREATE TABLE IF NOT EXISTS content_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT,
        start_line INTEGER,
        end_line INTEGER,
        chunk TEXT,
        embedding_json TEXT,
        tags TEXT,
        touched_at TIMESTAMP,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

# Index definitions
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_command_hash ON command_memory(command_hash)",
    "CREATE INDEX IF NOT EXISTS idx_timestamp ON command_memory(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_task_type ON command_memory(task_type)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_timestamp ON semantic_memory(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_path ON content_chunks(path)",
]


def get_default_db_path() -> Path:
    """Get default database path from config.

    Returns:
        Path to jarvis_memory.db in the configured data directory
    """
    try:
        from config_paths import get_config_paths
        paths = get_config_paths()
        base = Path(os.getenv('JARVIS_DB_DIR', str(paths.data_dir))).expanduser()
    except ImportError:
        try:
            from api.config_paths import get_config_paths
            paths = get_config_paths()
            base = Path(os.getenv('JARVIS_DB_DIR', str(paths.data_dir))).expanduser()
        except ImportError:
            base = Path(os.getenv('JARVIS_DB_DIR', '~/.neutron_data')).expanduser()

    return base / "jarvis_memory.db"


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create optimized SQLite connection for Jarvis memory.

    Configures:
    - WAL mode for concurrent access
    - Row factory for dict-like access
    - 30 second timeout for locks
    - DEFERRED isolation for better concurrency
    - Memory-mapped I/O for performance

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Configured sqlite3.Connection
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        timeout=30.0,
        isolation_level='DEFERRED'
    )
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=30000000000")

    return conn


def setup_schema(conn: sqlite3.Connection) -> None:
    """Create all memory tables and indexes.

    Args:
        conn: Active SQLite connection

    Note:
        Safe to call multiple times (uses IF NOT EXISTS)
    """
    # Create tables
    conn.execute(COMMAND_MEMORY_TABLE)
    conn.execute(PATTERN_TEMPLATES_TABLE)
    conn.execute(SEMANTIC_CLUSTERS_TABLE)
    conn.execute(ERROR_SOLUTIONS_TABLE)
    conn.execute(WORKFLOW_SEQUENCES_TABLE)
    conn.execute(SEMANTIC_MEMORY_TABLE)
    conn.execute(CONTENT_CHUNKS_TABLE)

    # Create indexes
    for index_sql in INDEXES:
        conn.execute(index_sql)

    conn.commit()


# ===== Embedding Utilities =====

def generate_embedding(text: str) -> List[float]:
    """Generate an embedding vector for text.

    Priority order:
    1. MLX embedder (if available on Apple Silicon)
    2. SimpleEmbedding from chat_enhancements
    3. Legacy 128-d hash embedding (fallback)

    Args:
        text: Text to embed

    Returns:
        List of floats representing the text embedding
    """
    # Try MLX embedder first
    try:
        from mlx_embedder import get_mlx_embedder
        embedder = get_mlx_embedder()
        if embedder.is_available():
            vec = embedder.embed(text or "")
            if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
                return [float(x) for x in vec]
    except ImportError:
        pass  # MLX not available
    except Exception:
        pass

    # Try SimpleEmbedding from chat_enhancements
    try:
        from chat_enhancements import SimpleEmbedding
        return SimpleEmbedding.create_embedding(text or "")
    except ImportError:
        try:
            from api.chat_enhancements import SimpleEmbedding
            return SimpleEmbedding.create_embedding(text or "")
        except ImportError:
            pass
    except Exception:
        pass

    # Legacy fallback: simple 128-d hash embedding
    return _hash_embedding(text)


def _hash_embedding(text: str) -> List[float]:
    """Generate a simple 128-d hash-based embedding.

    Used as fallback when no proper embedding model is available.

    Args:
        text: Text to embed

    Returns:
        Normalized 128-dimensional vector
    """
    words = (text or "").lower().split()
    vector = [0.0] * 128
    for word in words:
        idx = abs(hash(word)) % 128
        vector[idx] += 1.0
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score between 0.0 and 1.0
    """
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a ** 2 for a in vec1) ** 0.5
    norm2 = sum(b ** 2 for b in vec2) ** 0.5

    if norm1 * norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


# ===== Hash Utilities =====

def command_hash(command: str) -> str:
    """Generate SHA-256 hash for a command.

    Args:
        command: Command text

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(command.encode()).hexdigest()


def error_hash(error_message: str) -> str:
    """Generate SHA-256 hash for an error message.

    Args:
        error_message: Error message text

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(error_message.encode()).hexdigest()


__all__ = [
    # Schema constants
    "COMMAND_MEMORY_TABLE",
    "PATTERN_TEMPLATES_TABLE",
    "SEMANTIC_CLUSTERS_TABLE",
    "ERROR_SOLUTIONS_TABLE",
    "WORKFLOW_SEQUENCES_TABLE",
    "SEMANTIC_MEMORY_TABLE",
    "CONTENT_CHUNKS_TABLE",
    "INDEXES",
    # Connection utilities
    "get_default_db_path",
    "create_connection",
    "setup_schema",
    # Embedding utilities
    "generate_embedding",
    "cosine_similarity",
    # Hash utilities
    "command_hash",
    "error_hash",
]
