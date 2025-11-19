"""
Learning System - Data Models

Type definitions and dataclasses for the learning system:
- UserPreference: Learned user preferences
- CodingStyle: Detected coding style patterns
- ProjectContext: Project-specific context and settings
- Recommendation: Learning-based recommendations

Extracted from learning_system.py during Phase 6.3c modularization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class UserPreference:
    """Learned user preference"""
    category: str  # e.g., 'tool', 'style', 'workflow'
    preference: str  # e.g., 'aider', 'verbose', 'test-first'
    confidence: float  # 0.0 to 1.0
    evidence_count: int
    last_observed: str


@dataclass
class CodingStyle:
    """Detected coding style patterns"""
    language: str
    patterns: Dict[str, Any]  # e.g., {'indent': 4, 'quotes': 'single'}
    confidence: float
    sample_count: int
    indentation: int = 4  # Default indentation
    quote_style: str = 'single'  # Default quote style


@dataclass
class ProjectContext:
    """Project-specific context and settings"""
    project_path: str
    project_type: str  # e.g., 'python-web', 'node-cli', 'data-science'
    languages: List[str]
    frameworks: List[str]
    dependencies: List[str]
    typical_workflows: List[str]
    last_active: str
    activity_count: int


@dataclass
class Recommendation:
    """Learning-based recommendation"""
    action: str
    reason: str
    confidence: float
    based_on: List[str]  # What evidence supports this
