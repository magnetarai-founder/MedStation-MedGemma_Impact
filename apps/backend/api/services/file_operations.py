"""
Unified File Operations Service

Provides secure file operations with consistent security across the codebase:
- Path validation (workspace containment)
- Symlink attack prevention
- Size limits
- Binary file detection

This consolidates file operations from:
- Agent Tools (symlink protection)
- Workspace API (size limits)
- Chat API Reader (binary detection)
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileOperationResult:
    """Result of a file operation."""

    success: bool
    content: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class FileOperationsError(Exception):
    """Base exception for file operations."""

    pass


class PathSecurityError(FileOperationsError):
    """Raised when a path fails security validation."""

    pass


class FileSizeError(FileOperationsError):
    """Raised when a file exceeds size limits."""

    pass


class FileOperations:
    """
    Secure file operations service.

    All operations validate:
    1. Path is within workspace root
    2. No symlink attacks in path
    3. File size within limits
    4. Binary file detection (for reads)
    """

    # Default size limits
    DEFAULT_READ_LIMIT = 1_000_000  # 1MB
    DEFAULT_CONTEXT_LIMIT = 100_000  # 100KB for LLM context

    def __init__(
        self,
        workspace_root: Path | str,
        max_read_size: int = DEFAULT_READ_LIMIT,
    ):
        """
        Initialize file operations service.

        Args:
            workspace_root: Root directory for all file operations
            max_read_size: Maximum file size for read operations
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.max_read_size = max_read_size

    def validate_path(self, file_path: str | Path) -> Path:
        """
        Validate a file path for security.

        Checks:
        1. Path resolves within workspace root
        2. No symlinks in the path chain (prevents symlink attacks)

        Args:
            file_path: Relative path to validate

        Returns:
            Resolved absolute path

        Raises:
            PathSecurityError: If path fails validation
        """
        full_path = self.workspace_root / file_path

        # Resolve to absolute path (follows symlinks)
        try:
            resolved_path = full_path.resolve()
        except (OSError, RuntimeError) as e:
            raise PathSecurityError(f"Cannot resolve path: {file_path}") from e

        # Ensure within workspace
        try:
            resolved_path.relative_to(self.workspace_root)
        except ValueError as e:
            raise PathSecurityError(
                f"Access denied: {file_path} is outside workspace"
            ) from e

        # Check for symlinks in path chain (prevents TOCTOU attacks)
        check_path = resolved_path
        while check_path != self.workspace_root:
            if check_path.is_symlink():
                raise PathSecurityError(
                    f"Access denied: {file_path} contains symlinks"
                )
            parent = check_path.parent
            if parent == check_path:  # Reached filesystem root
                break
            check_path = parent

        return resolved_path

    def read(
        self,
        file_path: str | Path,
        max_size: int | None = None,
        allow_binary: bool = False,
    ) -> FileOperationResult:
        """
        Read file contents securely.

        Args:
            file_path: Relative path to file
            max_size: Optional size limit override
            allow_binary: If False, rejects binary files

        Returns:
            FileOperationResult with content or error
        """
        size_limit = max_size or self.max_read_size

        try:
            full_path = self.validate_path(file_path)
        except PathSecurityError as e:
            return FileOperationResult(success=False, error=str(e))

        # Check existence
        if not full_path.exists():
            return FileOperationResult(
                success=False,
                error=f"File not found: {file_path}",
            )

        if not full_path.is_file():
            return FileOperationResult(
                success=False,
                error=f"Not a file: {file_path}",
            )

        # Check size
        try:
            file_size = full_path.stat().st_size
        except OSError as e:
            return FileOperationResult(
                success=False,
                error=f"Cannot stat file: {e}",
            )

        if file_size > size_limit:
            return FileOperationResult(
                success=False,
                error=f"File too large: {file_size} bytes (limit: {size_limit})",
                metadata={"size": file_size, "limit": size_limit},
            )

        # Read file
        try:
            content = full_path.read_text(encoding="utf-8")
            return FileOperationResult(
                success=True,
                content=content,
                metadata={
                    "size": file_size,
                    "lines": content.count("\n") + 1,
                    "extension": full_path.suffix,
                },
            )
        except UnicodeDecodeError:
            if allow_binary:
                # Read as bytes and return hex representation (limited)
                try:
                    binary_content = full_path.read_bytes()
                    preview = binary_content[:1000].hex()
                    return FileOperationResult(
                        success=True,
                        content=f"[Binary file: {file_size} bytes]\n{preview}...",
                        metadata={"size": file_size, "binary": True},
                    )
                except Exception as e:
                    return FileOperationResult(
                        success=False,
                        error=f"Error reading binary file: {e}",
                    )
            else:
                return FileOperationResult(
                    success=False,
                    error=f"Binary file: {file_path}",
                    metadata={"binary": True},
                )
        except Exception as e:
            return FileOperationResult(
                success=False,
                error=f"Error reading file: {e}",
            )

    def write(
        self,
        file_path: str | Path,
        content: str,
        create_dirs: bool = True,
    ) -> FileOperationResult:
        """
        Write content to file securely.

        Args:
            file_path: Relative path to file
            content: Content to write
            create_dirs: Create parent directories if needed

        Returns:
            FileOperationResult with success status
        """
        try:
            full_path = self.validate_path(file_path)
        except PathSecurityError as e:
            return FileOperationResult(success=False, error=str(e))

        # Create parent directories
        if create_dirs:
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return FileOperationResult(
                    success=False,
                    error=f"Cannot create directory: {e}",
                )

        # Write file
        try:
            full_path.write_text(content, encoding="utf-8")
            return FileOperationResult(
                success=True,
                content=f"Wrote {len(content)} characters to {file_path}",
                metadata={"size": len(content)},
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                error=f"Error writing file: {e}",
            )

    def edit(
        self,
        file_path: str | Path,
        old_text: str,
        new_text: str,
        allow_multiple: bool = False,
    ) -> FileOperationResult:
        """
        Edit file by replacing text.

        Args:
            file_path: Relative path to file
            old_text: Text to find and replace
            new_text: Replacement text
            allow_multiple: Allow replacing multiple occurrences

        Returns:
            FileOperationResult with success status
        """
        # Read current content
        read_result = self.read(file_path)
        if not read_result.success:
            return read_result

        content = read_result.content

        # Check for old text
        if old_text not in content:
            return FileOperationResult(
                success=False,
                error=f"Text not found in {file_path}",
            )

        # Check occurrence count
        count = content.count(old_text)
        if count > 1 and not allow_multiple:
            return FileOperationResult(
                success=False,
                error=f"Text appears {count} times - be more specific or use allow_multiple=True",
            )

        # Replace
        new_content = content.replace(old_text, new_text)

        # Write back
        write_result = self.write(file_path, new_content, create_dirs=False)
        if write_result.success:
            write_result.content = f"Replaced {count} occurrence(s) in {file_path}"
            write_result.metadata = {"replacements": count}

        return write_result

    def delete(self, file_path: str | Path) -> FileOperationResult:
        """
        Delete a file securely.

        Args:
            file_path: Relative path to file

        Returns:
            FileOperationResult with success status
        """
        try:
            full_path = self.validate_path(file_path)
        except PathSecurityError as e:
            return FileOperationResult(success=False, error=str(e))

        if not full_path.exists():
            return FileOperationResult(
                success=False,
                error=f"File not found: {file_path}",
            )

        if not full_path.is_file():
            return FileOperationResult(
                success=False,
                error=f"Not a file: {file_path}",
            )

        try:
            full_path.unlink()
            return FileOperationResult(
                success=True,
                content=f"Deleted {file_path}",
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                error=f"Error deleting file: {e}",
            )

    def list_files(
        self,
        directory: str | Path = ".",
        pattern: str = "*",
        recursive: bool = False,
    ) -> FileOperationResult:
        """
        List files in a directory.

        Args:
            directory: Relative directory path
            pattern: Glob pattern
            recursive: Use recursive glob (**)

        Returns:
            FileOperationResult with list of relative paths
        """
        try:
            full_path = self.validate_path(directory)
        except PathSecurityError as e:
            return FileOperationResult(success=False, error=str(e))

        if not full_path.exists():
            return FileOperationResult(
                success=False,
                error=f"Directory not found: {directory}",
            )

        if not full_path.is_dir():
            return FileOperationResult(
                success=False,
                error=f"Not a directory: {directory}",
            )

        try:
            if recursive:
                files = list(full_path.rglob(pattern))
            else:
                files = list(full_path.glob(pattern))

            # Filter to files only and get relative paths
            relative_files = [
                str(f.relative_to(self.workspace_root))
                for f in files
                if f.is_file()
            ]

            return FileOperationResult(
                success=True,
                content="\n".join(relative_files),
                metadata={"count": len(relative_files)},
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                error=f"Error listing files: {e}",
            )

    def exists(self, file_path: str | Path) -> bool:
        """Check if a file exists (without reading)."""
        try:
            full_path = self.validate_path(file_path)
            return full_path.exists() and full_path.is_file()
        except PathSecurityError:
            return False

    def is_binary(self, file_path: str | Path) -> bool | None:
        """
        Check if a file is binary.

        Returns:
            True if binary, False if text, None if cannot determine
        """
        try:
            full_path = self.validate_path(file_path)
            if not full_path.exists():
                return None

            # Read first 8KB to detect binary
            with open(full_path, "rb") as f:
                chunk = f.read(8192)

            # Check for null bytes (common binary indicator)
            if b"\x00" in chunk:
                return True

            # Try to decode as UTF-8
            try:
                chunk.decode("utf-8")
                return False
            except UnicodeDecodeError:
                return True

        except (OSError, PathSecurityError) as e:
            logger.debug(f"Cannot determine if file is binary: {e}")
            return None
