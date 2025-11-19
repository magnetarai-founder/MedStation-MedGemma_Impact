"""
Code Editor Disk Scanner
Recursively scan directories and import files
"""

from pathlib import Path
from typing import List, Dict, Any


def scan_disk_directory(dir_path: str) -> List[Dict[str, Any]]:
    """Recursively scan directory and return file list"""
    files = []
    base_path = Path(dir_path)

    # Ignore patterns
    ignore_patterns = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv',
        '.DS_Store', '.vscode', '.idea', 'dist', 'build'
    }

    for file_path in base_path.rglob('*'):
        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in ignore_patterns):
            continue

        # Skip directories themselves
        if file_path.is_dir():
            continue

        # Get relative path
        rel_path = file_path.relative_to(base_path)

        # Detect language from extension
        ext = file_path.suffix.lower()
        lang_map = {
            '.js': 'javascript', '.jsx': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'shell',
        }
        language = lang_map.get(ext, 'plaintext')

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            # Skip binary files or files that can't be read
            continue

        files.append({
            'name': file_path.name,
            'path': str(rel_path).replace('\\', '/'),
            'content': content,
            'language': language
        })

    return files
