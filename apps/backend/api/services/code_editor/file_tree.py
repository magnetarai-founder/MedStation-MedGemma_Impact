"""
Code Editor File Tree Builder
Hierarchical file tree construction from flat file list
"""

from typing import List
from .models import FileTreeNode
from .db_workspaces import get_files_by_workspace


def build_file_tree(workspace_id: str) -> List[FileTreeNode]:
    """Build hierarchical file tree from flat file list"""
    files = get_files_by_workspace(workspace_id)

    # Build tree structure
    root_nodes = []
    path_map = {}

    for file_row in files:
        file_id, name, path, content = file_row
        parts = path.split('/')

        # Handle root files
        if len(parts) == 1:
            root_nodes.append(FileTreeNode(
                id=file_id,
                name=name,
                path=path,
                is_directory=False
            ))
            continue

        # Build directory structure
        current_path = ""
        for i, part in enumerate(parts[:-1]):
            current_path = f"{current_path}/{part}" if current_path else part

            if current_path not in path_map:
                node = FileTreeNode(
                    id=f"dir_{current_path}",
                    name=part,
                    path=current_path,
                    is_directory=True,
                    children=[]
                )
                path_map[current_path] = node

                # Add to parent or root
                if i == 0:
                    root_nodes.append(node)
                else:
                    parent_path = "/".join(parts[:i])
                    if parent_path in path_map:
                        path_map[parent_path].children.append(node)

        # Add file to parent directory
        file_node = FileTreeNode(
            id=file_id,
            name=name,
            path=path,
            is_directory=False
        )

        parent_path = "/".join(parts[:-1])
        if parent_path in path_map:
            path_map[parent_path].children.append(file_node)

    return root_nodes
