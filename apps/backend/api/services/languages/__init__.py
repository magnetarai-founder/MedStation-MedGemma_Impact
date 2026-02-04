"""
Multi-Language Analysis Package

Provides unified code analysis across multiple programming languages:
- TypeScript/JavaScript - AST parsing, type extraction
- Go - struct/interface extraction, package analysis
- Rust - trait/impl analysis, lifetime detection
- Java - class hierarchy, annotation processing
- Python - Full AST analysis (see analysis.ast_search)

Features:
- Language detection from file content
- Cross-language symbol resolution
- Unified CodeEntity format
- Dynamic analyzer loading via registry
- Tree-sitter AST parsing with regex fallback
"""

from .analyzers import (
    GoAnalyzer,
    JavaAnalyzer,
    Language,
    LanguageAnalyzer,
    LanguageRegistry,
    RustAnalyzer,
    TypeScriptAnalyzer,
    UnifiedAnalyzer,
    detect_language,
    detect_language_from_content,
    get_analyzer,
    get_unified_analyzer,
)

__all__ = [
    # Language enum
    "Language",
    # Base analyzer
    "LanguageAnalyzer",
    # Concrete analyzers
    "TypeScriptAnalyzer",
    "GoAnalyzer",
    "RustAnalyzer",
    "JavaAnalyzer",
    # Registry and unified analyzer
    "LanguageRegistry",
    "UnifiedAnalyzer",
    # Utility functions
    "detect_language",
    "detect_language_from_content",
    "get_analyzer",
    "get_unified_analyzer",
]
