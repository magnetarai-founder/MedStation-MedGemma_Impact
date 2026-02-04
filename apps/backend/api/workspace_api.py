"""
Workspace API for MagnetarCode

Provides file tree browsing and file content reading for context.

Endpoints:
  GET  /api/v1/workspace/files      - Get file tree for workspace
  POST /api/v1/workspace/read       - Read file contents
  GET  /api/v1/workspace/search     - Search files by name/content
"""

import pathlib
from typing import Any

from api.services.file_operations import FileOperations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])

# ===== Configuration =====

MAX_FILE_SIZE = 1024 * 1024  # 1MB
IGNORE_PATTERNS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".build",
    "build",
    "dist",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    ".swiftpm",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
}

# ===== Models =====


class FileNode(BaseModel):
    """A file or directory node"""

    name: str
    path: str
    type: str  # "file" or "directory"
    size: int | None = None
    children: list["FileNode"] | None = None


class WorkspaceScanRequest(BaseModel):
    """Request to scan a directory"""

    path: str = Field(..., description="Path to directory to scan")
    max_depth: int | None = Field(5, description="Maximum directory depth")


class FileReadRequest(BaseModel):
    """Request to read file contents"""

    workspace_path: str = Field(..., description="Path to workspace root")
    file_path: str = Field(..., description="Relative path to file within workspace")
    max_lines: int | None = Field(None, description="Maximum lines to read (for large files)")


class FileReadResponse(BaseModel):
    """Response with file contents"""

    path: str
    content: str
    lines: int
    size: int
    language: str | None = None


class FileSearchResult(BaseModel):
    """Search result"""

    path: str
    line_number: int | None = None
    snippet: str | None = None
    score: float


# ===== Helpers =====


def should_ignore(path: pathlib.Path) -> bool:
    """Check if path should be ignored"""
    name = path.name

    # Check exact matches for current path
    if name in IGNORE_PATTERNS:
        return True

    # Check if any parent directory matches ignore patterns
    for parent in path.parents:
        if parent.name in IGNORE_PATTERNS:
            return True

    # Check glob patterns
    for pattern in IGNORE_PATTERNS:
        if "*" in pattern and path.match(pattern):
            return True

    # Ignore hidden files (except .gitignore, .env, etc)
    return bool(
        name.startswith(".") and name not in {".gitignore", ".env", ".env.local", ".dockerignore"}
    )


def get_language(file_path: str) -> str | None:
    """Detect programming language from file extension"""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascriptreact",
        ".tsx": "typescriptreact",
        ".swift": "swift",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sql": "sql",
    }

    ext = pathlib.Path(file_path).suffix.lower()
    return ext_map.get(ext)


def _create_file_node(path: pathlib.Path) -> FileNode:
    """Create a file node with metadata."""
    node = FileNode(name=path.name, path=str(path), type="directory" if path.is_dir() else "file")

    # Add size for files
    if path.is_file():
        try:
            node.size = path.stat().st_size
        except OSError:
            node.size = 0

    return node


def _get_directory_children(
    root_path: pathlib.Path, max_depth: int, current_depth: int
) -> list[FileNode] | None:
    """Get children of a directory, respecting ignore patterns."""
    children = []
    try:
        for item in sorted(root_path.iterdir(), key=lambda x: (x.is_file(), x.name)):
            # Skip ignored paths
            if should_ignore(item):
                continue

            # Recurse
            child = build_file_tree(item, max_depth, current_depth + 1)
            if child:
                children.append(child)

        return children if children else None
    except PermissionError:
        # Skip directories we can't read
        return None


def build_file_tree(
    root_path: pathlib.Path, max_depth: int = 10, current_depth: int = 0
) -> FileNode | None:
    """
    Build file tree recursively.

    Args:
        root_path: Root directory path
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        FileNode tree
    """
    if not root_path.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")

    if current_depth >= max_depth:
        return None

    # Create node
    node = _create_file_node(root_path)

    # Recurse for directories
    if root_path.is_dir():
        node.children = _get_directory_children(root_path, max_depth, current_depth)

    return node


# ===== Endpoints =====


@router.get("/files", response_model=FileNode)
async def get_file_tree(
    workspace_path: str = Query(..., description="Path to workspace root"),
    max_depth: int = Query(5, description="Maximum directory depth"),
):
    """
    Get file tree for workspace.

    Returns hierarchical file tree with directories and files.
    Ignores common build artifacts and dependencies.
    Cached for 30 seconds to improve performance.

    **Example:**
    ```bash
    curl "http://localhost:8001/api/v1/workspace/files?workspace_path=/path/to/project"
    ```
    """
    from .utils.cache import cache_file_tree

    path = pathlib.Path(workspace_path).resolve()

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_path}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {workspace_path}")

    @cache_file_tree(ttl=30)
    async def _build_tree(ws_path: str, depth: int) -> FileNode | None:
        try:
            tree = build_file_tree(pathlib.Path(ws_path).resolve(), max_depth=depth)
            return tree
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to build file tree: {e!s}")

    return await _build_tree(workspace_path, max_depth)


@router.post("/read", response_model=FileReadResponse)
async def read_file(request: FileReadRequest) -> FileReadResponse:
    """
    Read file contents using unified FileOperations service.

    Returns file content with metadata (size, language, line count).
    Rejects files larger than 1MB to prevent memory issues.

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/workspace/read \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_path": "/path/to/project",
        "file_path": "src/main.py"
      }'
    ```
    """
    workspace_path = pathlib.Path(request.workspace_path).resolve()

    # Use unified FileOperations service for secure file access
    file_ops = FileOperations(workspace_path, max_read_size=MAX_FILE_SIZE)
    result = file_ops.read(request.file_path)

    if not result.success:
        error = result.error.lower()
        if "not found" in error:
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        elif "access denied" in error or "outside workspace" in error or "symlink" in error:
            raise HTTPException(status_code=403, detail="File path outside workspace")
        elif "too large" in error:
            raise HTTPException(status_code=413, detail=result.error)
        elif "binary" in error:
            raise HTTPException(status_code=400, detail="File is not text (binary file)")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {result.error}")

    content = result.content
    file_size = result.metadata.get("size", 0)
    lines = content.splitlines()

    # Limit lines if requested
    if request.max_lines and len(lines) > request.max_lines:
        content = "\n".join(lines[: request.max_lines])
        content += f"\n... (truncated, {len(lines) - request.max_lines} more lines)"

    return FileReadResponse(
        path=request.file_path,
        content=content,
        lines=len(lines),
        size=file_size,
        language=get_language(request.file_path),
    )


@router.get("/search", response_model=list[FileSearchResult])
async def search_files(
    workspace_path: str = Query(..., description="Path to workspace root"),
    query: str = Query(..., description="Search query"),
    type: str = Query("name", description="Search type: 'name' or 'content'"),
    limit: int = Query(50, description="Maximum results"),
):
    """
    Search files by name or content.

    **Search Types:**
    - `name`: Search file names (fast)
    - `content`: Search file contents (slower, uses ripgrep if available)

    **Example:**
    ```bash
    # Search by name
    curl "http://localhost:8001/api/v1/workspace/search?workspace_path=/path/to/project&query=auth&type=name"

    # Search by content
    curl "http://localhost:8001/api/v1/workspace/search?workspace_path=/path/to/project&query=TODO&type=content"
    ```
    """
    path = pathlib.Path(workspace_path).resolve()

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_path}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {workspace_path}")

    results = []

    if type == "name":
        # Search by file name
        query_lower = query.lower()
        for file_path in path.rglob("*"):
            if should_ignore(file_path):
                continue

            if file_path.is_file() and query_lower in file_path.name.lower():
                rel_path = str(file_path.relative_to(path))
                score = 1.0 if file_path.name.lower() == query_lower else 0.5
                results.append(FileSearchResult(path=rel_path, score=score))

            if len(results) >= limit:
                break

    elif type == "content":
        # Search file contents using ripgrep (fast) or fallback to Python
        try:
            from .services.ripgrep_search import get_ripgrep_search

            # Use ripgrep for fast search
            searcher = get_ripgrep_search(path)
            search_results = await searcher.search(
                pattern=query,
                max_results=limit,
                regex=False,  # Literal search by default
            )

            # Convert to FileSearchResult format
            for match in search_results.matches:
                results.append(
                    FileSearchResult(
                        path=match.file_path,
                        line_number=match.line_number,
                        snippet=match.line_text[:100],
                        score=1.0,
                    )
                )

        except (ImportError, RuntimeError):
            # Fallback to Python-based search if ripgrep not available
            for file_path in path.rglob("*"):
                if should_ignore(file_path):
                    continue

                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if query in content:
                            # Find first occurrence
                            lines = content.splitlines()
                            for i, line in enumerate(lines):
                                if query in line:
                                    rel_path = str(file_path.relative_to(path))
                                    results.append(
                                        FileSearchResult(
                                            path=rel_path,
                                            line_number=i + 1,
                                            snippet=line.strip()[:100],
                                            score=1.0,
                                        )
                                    )
                                    break
                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary files and permission errors
                        continue

                if len(results) >= limit:
                    break

    else:
        raise HTTPException(status_code=400, detail=f"Invalid search type: {type}")

    # Sort by score (descending)
    results.sort(key=lambda x: x.score, reverse=True)

    return results[:limit]


@router.post("/scan")
async def scan_directory(request: WorkspaceScanRequest) -> dict[str, Any]:
    """
    Scan a directory and return file tree.

    Similar to /files endpoint but takes POST request with path in body.

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/workspace/scan \
      -H "Content-Type: application/json" \
      -d '{"path": "/path/to/project"}'
    ```
    """
    path = pathlib.Path(request.path).resolve()

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {request.path}")

    try:
        tree = build_file_tree(path, max_depth=5)
        # Convert FileNode tree to flat list of items
        items = []

        def flatten_tree(node: FileNode | None, parent_path: str = "") -> None:
            if not node:
                return
            item_path = f"{parent_path}/{node.name}" if parent_path else node.name
            items.append(
                {
                    "name": node.name,
                    "path": item_path,
                    "type": node.type,
                    "size": node.size,
                }
            )
            if node.children:
                for child in node.children:
                    flatten_tree(child, item_path)

        flatten_tree(tree)

        return {"items": items, "count": len(items), "root": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan directory: {e!s}")


@router.get("/list")
async def list_workspaces() -> dict[str, Any]:
    """
    List all known workspaces.

    Returns a list of workspaces from the terminal multiplexer.

    **Example:**
    ```bash
    curl "http://localhost:8001/api/v1/workspace/list"
    ```
    """
    try:
        from .services.terminal import get_multiplexer

        multiplexer = get_multiplexer()
        workspaces = multiplexer.list_workspaces()

        return {"workspaces": workspaces, "count": len(workspaces)}
    except (RuntimeError, AttributeError):
        # If multiplexer not available, return empty list
        return {"workspaces": [], "count": 0}


@router.get("/health")
async def workspace_health() -> dict[str, Any]:
    """Health check for workspace service"""
    return {
        "status": "healthy",
        "max_file_size": MAX_FILE_SIZE,
        "ignore_patterns": len(IGNORE_PATTERNS),
    }
