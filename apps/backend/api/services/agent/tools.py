#!/usr/bin/env python3
"""
Tool System for Agent Execution

Provides a registry of tools that agents can call:
- File operations (read, write, edit) - delegated to FileOperations service
- Code execution (run tests, linters)
- Search operations (grep, find)
- Terminal commands
"""

import logging
import subprocess

# Import security utilities
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
# Import unified file operations service
from api.services.file_operations import FileOperations
from security import CommandValidationError, CommandValidator, log_command_execution

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """Parameter definition for a tool"""

    name: str
    type: str  # "string", "integer", "boolean", "array"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """A tool that agents can call"""

    name: str
    description: str
    parameters: list[ToolParameter]
    function: Callable
    category: str = "general"  # "file", "code", "search", "terminal"

    def to_schema(self) -> dict[str, Any]:
        """Convert to JSON schema for LLM function calling"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {"type": param.type, "description": param.description}
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        }


class ToolRegistry:
    """Registry of available tools for agents"""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.tools: dict[str, Tool] = {}
        # Initialize command validator for secure command execution
        self.command_validator = CommandValidator(
            workspace_root=self.workspace_root, strict_mode=True
        )
        # Initialize unified file operations service
        self._file_ops = FileOperations(self.workspace_root)
        self._register_default_tools()

    def register(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Tool | None:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all available tools"""
        return list(self.tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get JSON schemas for all tools (for LLM function calling)"""
        return [tool.to_schema() for tool in self.tools.values()]

    def execute(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool with given parameters"""
        tool = self.get(tool_name)
        if not tool:
            return {"error": f"Tool not found: {tool_name}"}

        try:
            result = tool.function(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e!s}")
            return {"success": False, "error": str(e)}

    # ===== Tool Implementations =====

    def _register_default_tools(self):
        """Register all default tools"""

        # FILE OPERATIONS
        self.register(
            Tool(
                name="read_file",
                description="Read the contents of a file",
                category="file",
                parameters=[
                    ToolParameter("file_path", "string", "Path to file (relative to workspace)")
                ],
                function=self._read_file,
            )
        )

        self.register(
            Tool(
                name="write_file",
                description="Write content to a file (creates or overwrites)",
                category="file",
                parameters=[
                    ToolParameter("file_path", "string", "Path to file (relative to workspace)"),
                    ToolParameter("content", "string", "Content to write to file"),
                ],
                function=self._write_file,
            )
        )

        self.register(
            Tool(
                name="edit_file",
                description="Edit a file by replacing old text with new text",
                category="file",
                parameters=[
                    ToolParameter("file_path", "string", "Path to file (relative to workspace)"),
                    ToolParameter("old_text", "string", "Text to replace"),
                    ToolParameter("new_text", "string", "New text to insert"),
                ],
                function=self._edit_file,
            )
        )

        self.register(
            Tool(
                name="list_files",
                description="List files in a directory",
                category="file",
                parameters=[
                    ToolParameter("path", "string", "Directory path", required=False, default="."),
                    ToolParameter(
                        "pattern",
                        "string",
                        "Glob pattern (e.g., '*.py')",
                        required=False,
                        default="*",
                    ),
                ],
                function=self._list_files,
            )
        )

        # SEARCH OPERATIONS
        self.register(
            Tool(
                name="grep_code",
                description="Search for text/regex in files",
                category="search",
                parameters=[
                    ToolParameter("pattern", "string", "Search pattern (regex)"),
                    ToolParameter(
                        "file_pattern",
                        "string",
                        "File pattern (e.g., '*.py')",
                        required=False,
                        default="*",
                    ),
                    ToolParameter(
                        "context_lines", "integer", "Lines of context", required=False, default=2
                    ),
                ],
                function=self._grep_code,
            )
        )

        # TERMINAL COMMANDS
        self.register(
            Tool(
                name="run_command",
                description="Run a shell command in the workspace",
                category="terminal",
                parameters=[
                    ToolParameter("command", "string", "Shell command to execute"),
                    ToolParameter(
                        "timeout", "integer", "Timeout in seconds", required=False, default=30
                    ),
                ],
                function=self._run_command,
            )
        )

        # GIT OPERATIONS
        self.register(
            Tool(
                name="git_status",
                description="Get git status of the workspace",
                category="git",
                parameters=[],
                function=self._git_status,
            )
        )

        self.register(
            Tool(
                name="git_diff",
                description="Show git diff of changes",
                category="git",
                parameters=[
                    ToolParameter("file_path", "string", "File to diff (optional)", required=False)
                ],
                function=self._git_diff,
            )
        )

        self.register(
            Tool(
                name="git_commit",
                description="Commit changes to git",
                category="git",
                parameters=[
                    ToolParameter("message", "string", "Commit message"),
                    ToolParameter(
                        "files",
                        "string",
                        "Files to commit (space-separated, or 'all')",
                        required=False,
                        default="all",
                    ),
                ],
                function=self._git_commit,
            )
        )

        # PACKAGE MANAGEMENT
        self.register(
            Tool(
                name="npm_install",
                description="Install npm packages",
                category="package",
                parameters=[
                    ToolParameter(
                        "package",
                        "string",
                        "Package name (optional, installs all if empty)",
                        required=False,
                    )
                ],
                function=self._npm_install,
            )
        )

        self.register(
            Tool(
                name="pip_install",
                description="Install Python packages",
                category="package",
                parameters=[
                    ToolParameter(
                        "package",
                        "string",
                        "Package name (optional, installs from requirements.txt if empty)",
                        required=False,
                    )
                ],
                function=self._pip_install,
            )
        )

        # TESTING
        self.register(
            Tool(
                name="run_tests",
                description="Run project tests",
                category="testing",
                parameters=[
                    ToolParameter(
                        "test_path", "string", "Specific test file or directory", required=False
                    ),
                    ToolParameter(
                        "framework", "string", "Test framework (pytest, jest, etc.)", required=False
                    ),
                ],
                function=self._run_tests,
            )
        )

    def _read_file(self, file_path: str) -> str:
        """Read file contents using unified FileOperations service."""
        result = self._file_ops.read(file_path)
        if not result.success:
            if "not found" in result.error.lower():
                raise FileNotFoundError(result.error)
            elif "access denied" in result.error.lower():
                raise PermissionError(result.error)
            else:
                raise RuntimeError(result.error)
        return result.content

    def _write_file(self, file_path: str, content: str) -> str:
        """Write content to file using unified FileOperations service."""
        result = self._file_ops.write(file_path, content)
        if not result.success:
            if "access denied" in result.error.lower():
                raise PermissionError(result.error)
            else:
                raise RuntimeError(result.error)
        return result.content

    def _edit_file(self, file_path: str, old_text: str, new_text: str) -> str:
        """Edit file by replacing text using unified FileOperations service."""
        result = self._file_ops.edit(file_path, old_text, new_text)
        if not result.success:
            if "not found" in result.error.lower():
                raise ValueError(result.error)
            elif "access denied" in result.error.lower():
                raise PermissionError(result.error)
            else:
                raise ValueError(result.error)
        return result.content

    def _list_files(self, path: str = ".", pattern: str = "*") -> list[str]:
        """List files matching pattern using unified FileOperations service."""
        result = self._file_ops.list_files(path, pattern)
        if not result.success:
            if "not found" in result.error.lower():
                raise FileNotFoundError(result.error)
            elif "access denied" in result.error.lower():
                raise PermissionError(result.error)
            else:
                raise RuntimeError(result.error)
        # Return list of files
        return result.content.split("\n") if result.content else []

    def _grep_code(self, pattern: str, file_pattern: str = "*", context_lines: int = 2) -> str:
        """Search for pattern in files"""
        try:
            # Use ripgrep if available, fall back to grep
            cmd = ["rg", "-n", "-C", str(context_lines), pattern, "-g", file_pattern]
            result = subprocess.run(
                cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return result.stdout
            elif result.returncode == 1:
                return "No matches found"
            else:
                raise Exception(result.stderr)

        except FileNotFoundError:
            # Fallback to grep
            cmd = ["grep", "-rn", "-C", str(context_lines), pattern, "--include", file_pattern, "."]
            result = subprocess.run(
                cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return result.stdout
            elif result.returncode == 1:
                return "No matches found"
            else:
                raise Exception(result.stderr)

    def _run_command(self, command: str, timeout: int = 30) -> dict[str, Any]:
        """
        Run a shell command with security validation.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Dict with stdout, stderr, exit_code, and success status
        """
        try:
            # Validate command using secure validator
            base_cmd, args = self.command_validator.validate(command)

            # Execute command safely (no shell=True)
            result = subprocess.run(
                [base_cmd, *args],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Log command execution for audit
            log_command_execution(
                command=base_cmd,
                args=args,
                workspace=str(self.workspace_root),
                success=result.returncode == 0,
                exit_code=result.returncode,
                error=result.stderr if result.returncode != 0 else None,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

        except CommandValidationError as e:
            logger.error(f"Command validation failed: {e}")
            log_command_execution(
                command=command.split()[0] if command else "unknown",
                args=[],
                workspace=str(self.workspace_root),
                success=False,
                error=str(e),
            )
            return {"error": f"Command blocked by security validation: {e!s}", "success": False}

        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "success": False}

    def _git_status(self) -> str:
        """Get git status"""
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout if result.returncode == 0 else result.stderr

    def _git_diff(self, file_path: str | None = None) -> str:
        """Show git diff"""
        cmd = ["git", "diff"]
        if file_path:
            cmd.append(file_path)

        result = subprocess.run(
            cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else result.stderr

    def _git_commit(self, message: str, files: str = "all") -> dict[str, Any]:
        """Commit changes to git"""
        try:
            # Add files
            if files == "all":
                add_result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            else:
                file_list = files.split()
                add_result = subprocess.run(
                    ["git", "add", *file_list],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            if add_result.returncode != 0:
                return {"success": False, "error": f"git add failed: {add_result.stderr}"}

            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if commit_result.returncode == 0:
                return {"success": True, "message": commit_result.stdout}
            else:
                return {"success": False, "error": commit_result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _npm_install(self, package: str | None = None) -> dict[str, Any]:
        """Install npm packages"""
        try:
            if package:
                cmd = ["npm", "install", package]
            else:
                cmd = ["npm", "install"]

            result = subprocess.run(
                cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=120
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pip_install(self, package: str | None = None) -> dict[str, Any]:
        """Install Python packages"""
        try:
            if package:
                cmd = ["pip", "install", package]
            else:
                # Install from requirements.txt if it exists
                if (self.workspace_root / "requirements.txt").exists():
                    cmd = ["pip", "install", "-r", "requirements.txt"]
                else:
                    return {
                        "success": False,
                        "error": "No package specified and no requirements.txt found",
                    }

            result = subprocess.run(
                cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=120
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_tests(
        self, test_path: str | None = None, framework: str | None = None
    ) -> dict[str, Any]:
        """Run project tests"""
        try:
            # Auto-detect framework if not specified
            if not framework:
                if (self.workspace_root / "pytest.ini").exists() or (
                    self.workspace_root / "setup.py"
                ).exists():
                    framework = "pytest"
                elif (self.workspace_root / "package.json").exists():
                    framework = "jest"
                else:
                    framework = "pytest"  # Default

            # Build command
            if framework == "pytest":
                cmd = ["pytest"]
                if test_path:
                    cmd.append(test_path)
                cmd.extend(["-v", "--tb=short"])
            elif framework == "jest":
                cmd = ["npm", "test"]
                if test_path:
                    cmd.append(test_path)
            else:
                return {"success": False, "error": f"Unknown test framework: {framework}"}

            result = subprocess.run(
                cmd, cwd=self.workspace_root, capture_output=True, text=True, timeout=120
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "framework": framework,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
