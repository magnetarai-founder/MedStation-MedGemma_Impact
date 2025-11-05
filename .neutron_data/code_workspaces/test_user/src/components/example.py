"""
Example Python File - Demonstrates Monaco Syntax Highlighting

This shows integration of all 4 projects:
- Continue: File operations
- Codex: Line-numbered reading
- Jarvis: Permission checking
- Big Query: Template patterns (Phase 11)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileNode:
    """Represents a file in the tree (from Continue's pattern)"""
    name: str
    path: Path
    type: str  # 'file' or 'directory'
    children: Optional[List['FileNode']] = None


class CodeWorkspace:
    """
    Manages code workspace operations
    Integrates Continue + Codex + Jarvis patterns
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.permission_layer = None  # Jarvis PermissionLayer

    def walk_directory(self, recursive: bool = True) -> List[FileNode]:
        """
        Walk directory using Continue's walkDir pattern
        With Jarvis permission checking
        """
        nodes = []

        for entry in self.base_path.iterdir():
            # Skip ignored paths (Continue pattern)
            if self._should_ignore(entry):
                continue

            # Check permissions (Jarvis pattern)
            if not self._check_permission(entry):
                continue

            node = FileNode(
                name=entry.name,
                path=entry,
                type='directory' if entry.is_dir() else 'file'
            )

            if entry.is_dir() and recursive:
                node.children = self.walk_directory_recursive(entry)

            nodes.append(node)

        return nodes

    def _should_ignore(self, path: Path) -> bool:
        """Continue's shouldIgnore pattern"""
        ignore_list = ['node_modules', '.git', '__pycache__', '.venv']
        return any(pattern in str(path) for pattern in ignore_list)

    def _check_permission(self, path: Path) -> bool:
        """Jarvis permission layer integration"""
        # Risk assessment would go here
        return True


# Demo usage
if __name__ == "__main__":
    workspace = CodeWorkspace(Path("/Users/indiedevhipps/Documents/ElohimOS"))
    files = workspace.walk_directory()

    print(f"✅ Found {len(files)} items in workspace")
    print("🎉 Phase 2: Read-Only File Operations - COMPLETE!")
