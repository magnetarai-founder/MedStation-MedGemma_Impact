"""
Jarvis Memory Templates and Utilities

Pure data definitions and utility functions for the Jarvis BigQuery-inspired memory system.
Extracted from jarvis_bigquery_memory.py during P2 decomposition.

Contains:
- MemoryType enum
- MemoryTemplate dataclass
- SemanticMemory dataclass
- SQL CTE templates for memory operations
- cosine_similarity() pure function
- generate_hash_embedding() fallback embedding function
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any


class MemoryType(Enum):
    """Types of memory patterns"""
    COMMAND_PATTERN = "command_pattern"
    CODE_TEMPLATE = "code_template"
    ERROR_SOLUTION = "error_solution"
    WORKFLOW_SEQUENCE = "workflow_sequence"
    SEMANTIC_CLUSTER = "semantic_cluster"


@dataclass
class MemoryTemplate:
    """SQL template for memory operations"""
    id: str
    name: str
    category: str
    pattern: str  # SQL CTE pattern
    parameters: List[str]
    confidence: float = 0.8


@dataclass
class SemanticMemory:
    """Semantic memory entry with embedding"""
    command: str
    embedding: List[float]  # Vector representation
    context: Dict[str, Any]
    timestamp: str
    success: bool
    tool_used: str
    execution_time: float


# ============================================
# PURE UTILITY FUNCTIONS
# ============================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    if not vec1 or not vec2:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a**2 for a in vec1) ** 0.5
    norm2 = sum(b**2 for b in vec2) ** 0.5

    if norm1 * norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def generate_hash_embedding(text: str, dimensions: int = 128) -> List[float]:
    """
    Generate a simple hash-based embedding vector.

    This is a fallback when no ML embedding model is available.
    Uses word hashing to create a normalized vector.

    Args:
        text: Input text to embed
        dimensions: Vector dimensions (default 128)

    Returns:
        Normalized embedding vector
    """
    words = (text or "").lower().split()
    vector = [0.0] * dimensions

    for word in words:
        idx = abs(hash(word)) % dimensions
        vector[idx] += 1.0

    # L2 normalize
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


# ============================================
# SQL CTE TEMPLATES
# ============================================

def get_default_templates() -> List[MemoryTemplate]:
    """
    Get default SQL CTE templates for memory operations.

    These templates are inspired by BigQuery competition approaches
    for grounded pattern matching with zero hallucination.

    Returns:
        List of MemoryTemplate objects
    """
    return [
        # Command Analysis Templates
        MemoryTemplate(
            id="CMD_001",
            name="Similar Command Finder",
            category="command_analysis",
            pattern="""
            WITH command_patterns AS (
                SELECT
                    command,
                    task_type,
                    tool_used,
                    AVG(execution_time) as avg_time,
                    COUNT(*) as usage_count,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate
                FROM command_memory
                WHERE command LIKE ?
                GROUP BY command, task_type, tool_used
            ),
            ranked_patterns AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY usage_count DESC, success_rate DESC) as rank
                FROM command_patterns
            )
            SELECT * FROM ranked_patterns WHERE rank <= 5
            """,
            parameters=["command_pattern"],
            confidence=0.85
        ),

        # Error Pattern Templates
        MemoryTemplate(
            id="ERR_001",
            name="Error Solution Finder",
            category="error_handling",
            pattern="""
            WITH error_matches AS (
                SELECT
                    error_pattern,
                    solution_template,
                    tool_suggestion,
                    (success_count * 1.0) / NULLIF(success_count + failure_count, 0) as success_rate
                FROM error_solutions
                WHERE error_pattern LIKE ?
                    OR error_hash = ?
            ),
            ranked_solutions AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY success_rate DESC) as rank
                FROM error_matches
                WHERE success_rate > 0.5
            )
            SELECT * FROM ranked_solutions WHERE rank = 1
            """,
            parameters=["error_pattern", "error_hash"],
            confidence=0.9
        ),

        # Workflow Discovery Templates
        MemoryTemplate(
            id="WF_001",
            name="Workflow Pattern Detector",
            category="workflow_analysis",
            pattern="""
            WITH recent_commands AS (
                SELECT
                    command,
                    task_type,
                    tool_used,
                    timestamp,
                    LAG(command, 1) OVER (ORDER BY timestamp) as prev_command,
                    LAG(command, 2) OVER (ORDER BY timestamp) as prev_command_2
                FROM command_memory
                WHERE timestamp > datetime('now', '-1 hour')
            ),
            command_sequences AS (
                SELECT
                    prev_command_2 || ' -> ' || prev_command || ' -> ' || command as sequence,
                    COUNT(*) as occurrence_count
                FROM recent_commands
                WHERE prev_command IS NOT NULL
                GROUP BY sequence
                HAVING occurrence_count > 1
            )
            SELECT * FROM command_sequences
            ORDER BY occurrence_count DESC
            LIMIT 5
            """,
            parameters=[],
            confidence=0.75
        ),
    ]


# Template lookup by ID for convenience
def get_template_by_id(template_id: str) -> MemoryTemplate | None:
    """
    Get a template by its ID.

    Args:
        template_id: Template ID (e.g., "CMD_001", "ERR_001")

    Returns:
        MemoryTemplate or None if not found
    """
    templates = get_default_templates()
    for template in templates:
        if template.id == template_id:
            return template
    return None


__all__ = [
    # Enums
    "MemoryType",
    # Dataclasses
    "MemoryTemplate",
    "SemanticMemory",
    # Pure functions
    "cosine_similarity",
    "generate_hash_embedding",
    # Template functions
    "get_default_templates",
    "get_template_by_id",
]
