"""
Background Code Analysis Package

Provides continuous, proactive code analysis:
- Security vulnerability scanning
- Performance bottleneck detection
- Code quality assessment
- Dependency analysis
- Dead code detection
"""

from .background_analyzer import (
    BackgroundAnalyzer,
    AnalysisResult,
    AnalysisSeverity,
    AnalysisType,
    get_background_analyzer,
)
from .ast_search import (
    ASTSearchEngine,
    CodeEntity,
    EntityType,
    get_ast_search,
)

__all__ = [
    # Background Analysis
    "BackgroundAnalyzer",
    "AnalysisResult",
    "AnalysisSeverity",
    "AnalysisType",
    "get_background_analyzer",
    # AST Search
    "ASTSearchEngine",
    "CodeEntity",
    "EntityType",
    "get_ast_search",
]
