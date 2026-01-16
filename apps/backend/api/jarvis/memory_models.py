"""
Jarvis Memory Models - Data models for BigQuery-inspired memory system

Provides:
- MemoryType enum for categorizing memory patterns
- MemoryTemplate dataclass for SQL CTE templates
- SemanticMemory dataclass for semantic embeddings
- Pre-defined CTE templates for memory operations

Extracted from jarvis_memory.py during P2 decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


class MemoryType(Enum):
    """Types of memory patterns.

    Categories:
    - COMMAND_PATTERN: User command patterns and variations
    - CODE_TEMPLATE: Reusable code snippets and templates
    - ERROR_SOLUTION: Error messages paired with solutions
    - WORKFLOW_SEQUENCE: Chains of commands forming workflows
    - SEMANTIC_CLUSTER: Grouped semantically similar items
    """
    COMMAND_PATTERN = "command_pattern"
    CODE_TEMPLATE = "code_template"
    ERROR_SOLUTION = "error_solution"
    WORKFLOW_SEQUENCE = "workflow_sequence"
    SEMANTIC_CLUSTER = "semantic_cluster"


@dataclass
class MemoryTemplate:
    """SQL CTE template for memory operations.

    Based on BigQuery competition approach - using grounded SQL patterns
    for zero-hallucination memory queries.

    Attributes:
        id: Unique template identifier (e.g., CMD_001, ERR_001)
        name: Human-readable template name
        category: Template category (command_analysis, error_handling, etc.)
        pattern: SQL CTE pattern with ? placeholders
        parameters: List of parameter names for documentation
        confidence: Default confidence score for matches (0.0-1.0)
    """
    id: str
    name: str
    category: str
    pattern: str  # SQL CTE pattern
    parameters: List[str]
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SemanticMemory:
    """Semantic memory entry with embedding vector.

    Stores command executions with their vector embeddings for
    similarity search and semantic clustering.

    Attributes:
        command: The executed command text
        embedding: Vector representation (list of floats)
        context: Additional context (file paths, environment, etc.)
        timestamp: ISO format timestamp
        success: Whether execution succeeded
        tool_used: Which tool executed the command
        execution_time: Time taken in seconds
    """
    command: str
    embedding: List[float]  # Vector representation
    context: Dict[str, Any]
    timestamp: str
    success: bool
    tool_used: str
    execution_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticMemory":
        """Create from dictionary."""
        return cls(
            command=data["command"],
            embedding=data.get("embedding", []),
            context=data.get("context", {}),
            timestamp=data.get("timestamp", ""),
            success=data.get("success", False),
            tool_used=data.get("tool_used", "unknown"),
            execution_time=data.get("execution_time", 0.0)
        )


# ===== Pre-defined CTE Templates =====

def get_default_templates() -> List[MemoryTemplate]:
    """Get pre-defined SQL CTE templates for memory operations.

    Returns templates for:
    - Similar command finding (CMD_001)
    - Error solution lookup (ERR_001)
    - Workflow pattern detection (WF_001)
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


__all__ = [
    # Enums
    "MemoryType",
    # Dataclasses
    "MemoryTemplate",
    "SemanticMemory",
    # Template factory
    "get_default_templates",
]
