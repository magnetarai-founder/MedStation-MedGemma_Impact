"""
Learning System - Coding Style Detection

Coding style detection and analysis:
- detect_coding_style: Analyze file content for style patterns
- Language-specific style detection (Python, JS/TS, Java)
- Style data storage and retrieval

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict
from threading import Lock

from .models import CodingStyle


def detect_coding_style(
    conn: sqlite3.Connection,
    lock: Lock,
    file_path: str,
    content: str
) -> CodingStyle:
    """
    Detect coding style from file content.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        file_path: Path to the file being analyzed
        content: File content to analyze

    Returns:
        CodingStyle object with detected patterns
    """
    language = _detect_language(file_path)
    patterns = {}

    if language == 'python':
        patterns = _detect_python_style(content)
    elif language in ['javascript', 'typescript']:
        patterns = _detect_js_style(content)
    elif language == 'java':
        patterns = _detect_java_style(content)

    # Store detected style
    with lock:
        _store_coding_style(conn, language, file_path, patterns)
        conn.commit()

    return CodingStyle(
        language=language,
        patterns=patterns,
        confidence=0.8,  # Would calculate based on sample size
        sample_count=1,
        indentation=patterns.get('indent', 4),
        quote_style=patterns.get('quotes', 'single')
    )


def _detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to the file

    Returns:
        Language name or 'unknown'
    """
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
    }

    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, 'unknown')


def _detect_python_style(content: str) -> Dict:
    """
    Detect Python coding style patterns.

    Analyzes:
    - Indentation (spaces)
    - Quote style (single vs double)
    - Type hints usage
    - Docstring style
    - Naming conventions (PascalCase for classes, snake_case for functions)

    Args:
        content: Python source code

    Returns:
        Dict of detected style patterns
    """
    lines = content.split('\n')
    patterns = {}

    # Indentation
    indent_counts = defaultdict(int)
    for line in lines:
        if line and line[0] == ' ':
            spaces = len(line) - len(line.lstrip())
            if spaces > 0:
                indent_counts[spaces] += 1

    if indent_counts:
        most_common_indent = max(indent_counts, key=indent_counts.get)
        patterns['indent'] = most_common_indent

    # Quotes
    single_quotes = content.count("'")
    double_quotes = content.count('"')
    patterns['quotes'] = 'single' if single_quotes > double_quotes else 'double'

    # Type hints
    patterns['type_hints'] = '->' in content or ': str' in content or ': int' in content

    # Docstrings
    patterns['docstring_style'] = (
        'triple_double' if '"""' in content else
        'triple_single' if "'''" in content else
        None
    )

    # Class naming
    class_pattern = re.compile(r'class\s+([A-Z][a-zA-Z0-9]*)')
    classes = class_pattern.findall(content)
    patterns['class_naming'] = 'PascalCase' if classes else None

    # Function naming
    func_pattern = re.compile(r'def\s+([a-z_][a-z0-9_]*)')
    functions = func_pattern.findall(content)
    patterns['function_naming'] = 'snake_case' if functions else None

    return patterns


def _detect_js_style(content: str) -> Dict:
    """
    Detect JavaScript/TypeScript style patterns.

    Analyzes:
    - Semicolon usage
    - Quote style
    - Variable declarations (const vs let)
    - Arrow function usage

    Args:
        content: JavaScript/TypeScript source code

    Returns:
        Dict of detected style patterns
    """
    patterns = {}

    # Semicolons
    patterns['semicolons'] = content.count(';') > content.count('\n') * 0.5

    # Quotes
    single_quotes = content.count("'")
    double_quotes = content.count('"')
    patterns['quotes'] = 'single' if single_quotes > double_quotes else 'double'

    # Const vs let
    const_count = content.count('const ')
    let_count = content.count('let ')
    patterns['variable_declaration'] = 'const' if const_count > let_count else 'let'

    # Arrow functions
    patterns['arrow_functions'] = '=>' in content

    return patterns


def _detect_java_style(content: str) -> Dict:
    """
    Detect Java style patterns.

    Analyzes:
    - Brace style (same line vs new line)
    - Access modifier usage

    Args:
        content: Java source code

    Returns:
        Dict of detected style patterns
    """
    patterns = {}

    # Brace style
    patterns['brace_style'] = 'same_line' if '{\n' in content else 'new_line'

    # Access modifiers
    patterns['explicit_access'] = 'private' in content or 'public' in content

    return patterns


def _store_coding_style(
    conn: sqlite3.Connection,
    language: str,
    file_path: str,
    patterns: Dict
) -> None:
    """
    Store detected coding style in database.

    Args:
        conn: SQLite database connection
        language: Programming language
        file_path: Path to analyzed file
        patterns: Detected style patterns
    """
    file_pattern = str(Path(file_path).parent / f"*.{Path(file_path).suffix}")

    cursor = conn.execute("""
        SELECT sample_count FROM coding_styles
        WHERE language = ? AND file_pattern = ?
    """, (language, file_pattern))

    row = cursor.fetchone()

    if row:
        # Update existing style data
        conn.execute("""
            UPDATE coding_styles
            SET style_data = ?, sample_count = sample_count + 1,
                last_updated = CURRENT_TIMESTAMP
            WHERE language = ? AND file_pattern = ?
        """, (json.dumps(patterns), language, file_pattern))
    else:
        # Insert new style data
        conn.execute("""
            INSERT INTO coding_styles
            (language, file_pattern, style_data, sample_count, confidence)
            VALUES (?, ?, ?, 1, 0.5)
        """, (language, file_pattern, json.dumps(patterns)))
