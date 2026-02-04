#!/usr/bin/env python3
"""
Custom Tool Definition and Registration System

Allows users to create custom tools dynamically:
- Python function-based tools (sandboxed)
- Shell script tools (validated)
- API integration tools
- Persistent tool storage

Uses the BaseRepository pattern for consistent database operations.
"""
# ruff: noqa: S608

import ipaddress
import json
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from api.services.db import BaseRepository, DatabaseConnection

# Import security utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from security import (
    CommandValidationError,
    CommandValidator,
    PythonSandbox,
    SandboxExecutionError,
    log_command_execution,
)
from security.audit_logger import get_audit_logger

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class ToolType(Enum):
    """Types of custom tools"""

    PYTHON_FUNCTION = "python_function"
    SHELL_SCRIPT = "shell_script"
    API_CALL = "api_call"
    COMPOSITE = "composite"  # Combines multiple tools


@dataclass
class ToolParameter:
    """Parameter definition for a tool"""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
        }


@dataclass
class CustomToolDefinition:
    """Definition of a custom tool"""

    name: str
    description: str
    tool_type: ToolType
    parameters: list[ToolParameter]
    implementation: str  # Code/script/config
    category: str = "custom"
    tags: list[str] = field(default_factory=list)
    author: str = "user"
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "implementation": self.implementation,
            "category": self.category,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomToolDefinition":
        return cls(
            name=data["name"],
            description=data["description"],
            tool_type=ToolType(data["tool_type"]),
            parameters=[
                ToolParameter(**p) if isinstance(p, dict) else p for p in data["parameters"]
            ],
            implementation=data["implementation"],
            category=data.get("category", "custom"),
            tags=data.get("tags", []),
            author=data.get("author", "user"),
            version=data.get("version", "1.0.0"),
        )


class CustomToolRepository(BaseRepository[CustomToolDefinition]):
    """Repository for custom tool definitions."""

    @property
    def table_name(self) -> str:
        return "custom_tools"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS custom_tools (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                tool_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                implementation TEXT NOT NULL,
                category TEXT DEFAULT 'custom',
                tags TEXT DEFAULT '[]',
                author TEXT DEFAULT 'user',
                version TEXT DEFAULT '1.0.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> CustomToolDefinition:
        return CustomToolDefinition(
            name=row["name"],
            description=row["description"],
            tool_type=ToolType(row["tool_type"]),
            parameters=[ToolParameter(**p) for p in json.loads(row["parameters"])],
            implementation=row["implementation"],
            category=row["category"],
            tags=json.loads(row["tags"]),
            author=row["author"],
            version=row["version"],
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["category"], name="idx_tools_category")
        self._create_index(["tool_type"], name="idx_tools_type")
        self._create_index(["author"], name="idx_tools_author")
        self._create_index(["updated_at"], name="idx_tools_updated")
        self._create_index(["category", "tool_type"], name="idx_tools_category_type")

    def upsert(self, tool: CustomToolDefinition) -> None:
        """Insert or replace a tool definition."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            """
            INSERT OR REPLACE INTO custom_tools
            (name, description, tool_type, parameters, implementation,
             category, tags, author, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool.name,
                tool.description,
                tool.tool_type.value,
                json.dumps([p.to_dict() for p in tool.parameters]),
                tool.implementation,
                tool.category,
                json.dumps(tool.tags),
                tool.author,
                tool.version,
                now,
                now,
            ),
        )
        self.db.get().commit()

    def find_by_filters(
        self, category: str | None = None, tool_type: ToolType | None = None
    ) -> list[CustomToolDefinition]:
        """Find tools with optional category and type filtering."""
        where_parts = []
        params: list[str] = []

        if category:
            where_parts.append("category = ?")
            params.append(category)

        if tool_type:
            where_parts.append("tool_type = ?")
            params.append(tool_type.value)

        if not where_parts:
            return self.find_all()

        return self.find_where(" AND ".join(where_parts), tuple(params))


class CustomToolRegistry:
    """
    Registry for custom user-defined tools.

    Stores tool definitions using CustomToolRepository and provides execution.
    Uses DatabaseConnection for thread-safe database access.
    """

    def __init__(self, db_path: Path | None = None, workspace_root: Path | None = None):
        if db_path is None:
            data_dir = Path("~/.magnetarcode/data").expanduser()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "custom_tools.db"

        self.workspace_root = workspace_root or Path.cwd()
        self._compiled_tools: dict[str, Callable] = {}

        # Initialize database connection and repository
        self._db = DatabaseConnection(db_path)
        self._repo = CustomToolRepository(self._db)

        # Initialize security components
        self.sandbox = PythonSandbox(
            max_execution_time=30,
            max_memory_mb=256,  # 30 second limit  # 256 MB limit
        )
        self.command_validator = CommandValidator(workspace_root=self.workspace_root)
        self.audit_logger = get_audit_logger()

    def register_tool(self, tool_def: CustomToolDefinition) -> bool:
        """
        Register a new custom tool.

        Args:
            tool_def: Tool definition

        Returns:
            True if registered successfully
        """
        try:
            self._repo.upsert(tool_def)

            # Compile the tool
            self._compile_tool(tool_def)
            return True

        except Exception as e:
            logger.error(f"Error registering tool: {e}")
            return False

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a custom tool."""
        try:
            self._repo.delete_by_id(tool_name, id_column="name")

            # Remove from compiled cache
            if tool_name in self._compiled_tools:
                del self._compiled_tools[tool_name]

            return True
        except Exception as e:
            logger.error(f"Error unregistering tool: {e}")
            return False

    def get_tool(self, tool_name: str) -> CustomToolDefinition | None:
        """Get a tool definition by name."""
        return self._repo.find_by_id(tool_name, id_column="name")

    def list_tools(
        self, category: str | None = None, tool_type: ToolType | None = None
    ) -> list[CustomToolDefinition]:
        """List all custom tools with optional filtering."""
        return self._repo.find_by_filters(category=category, tool_type=tool_type)

    def _compile_tool(self, tool_def: CustomToolDefinition):
        """Compile a tool for execution"""
        if tool_def.tool_type == ToolType.PYTHON_FUNCTION:
            self._compile_python_tool(tool_def)
        elif tool_def.tool_type == ToolType.SHELL_SCRIPT:
            self._compile_shell_tool(tool_def)
        elif tool_def.tool_type == ToolType.API_CALL:
            self._compile_api_tool(tool_def)

    def _compile_python_tool(self, tool_def: CustomToolDefinition):
        """
        Compile a Python function tool using secure sandbox.

        The tool will execute in a restricted Python environment with:
        - Limited builtins (no file I/O, network, imports)
        - Resource limits (30s execution, 256MB memory)
        - Audit logging
        """
        # Validate code before compilation
        validation = self.sandbox.validate_only(tool_def.implementation)
        if not validation["valid"]:
            raise ValueError(f"Tool code validation failed: {'; '.join(validation['errors'])}")

        # Create wrapper function that executes in sandbox
        def sandboxed_executor(**kwargs):
            try:
                # Execute in sandbox
                result = self.sandbox.execute(
                    code=tool_def.implementation, function_name=tool_def.name, **kwargs
                )

                # Log successful execution
                self.audit_logger.log_custom_tool_execution(
                    tool_name=tool_def.name, parameters=kwargs, success=True, result=result
                )

                return result

            except (SandboxExecutionError, Exception) as e:
                # Log failed execution
                self.audit_logger.log_custom_tool_execution(
                    tool_name=tool_def.name, parameters=kwargs, success=False, error=str(e)
                )
                raise ValueError(f"Tool execution failed: {e}")

        self._compiled_tools[tool_def.name] = sandboxed_executor

    def _compile_shell_tool(self, tool_def: CustomToolDefinition):
        """
        Compile a shell script tool with command validation.

        Scripts are validated against command whitelist before execution.
        """

        def shell_executor(**kwargs):
            try:
                # Replace placeholders in script with actual values
                script = tool_def.implementation
                for param in tool_def.parameters:
                    value = kwargs.get(param.name, param.default)
                    # SECURITY: Use shlex.quote() for proper shell escaping
                    # This prevents shell injection via newlines, backticks, $(), etc.
                    import shlex

                    sanitized_value = shlex.quote(str(value))
                    script = script.replace(f"${{{param.name}}}", sanitized_value)

                # Validate command before execution
                base_cmd, args = self.command_validator.validate(script)

                # Execute validated command (no shell=True)
                result = subprocess.run(
                    [base_cmd, *args],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # Log execution
                log_command_execution(
                    command=base_cmd,
                    args=args,
                    workspace=str(self.workspace_root),
                    success=result.returncode == 0,
                    exit_code=result.returncode,
                )

                # Log tool execution
                self.audit_logger.log_custom_tool_execution(
                    tool_name=tool_def.name,
                    parameters=kwargs,
                    success=result.returncode == 0,
                    result={"exit_code": result.returncode},
                )

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }

            except CommandValidationError as e:
                # Log validation failure
                self.audit_logger.log_custom_tool_execution(
                    tool_name=tool_def.name,
                    parameters=kwargs,
                    success=False,
                    error=f"Command validation failed: {e}",
                )
                raise ValueError(f"Command validation failed: {e}")

        self._compiled_tools[tool_def.name] = shell_executor

    def _validate_url_for_ssrf(self, url: str) -> None:
        """
        Validate URL to prevent SSRF attacks.

        Blocks:
        - Non-HTTP(S) schemes
        - Localhost and loopback addresses
        - Private IP ranges (10.x, 172.16-31.x, 192.168.x)
        - Cloud metadata service IPs (169.254.169.254)

        Raises:
            ValueError: If URL is not safe for external requests
        """
        parsed = urlparse(url)

        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL scheme '{parsed.scheme}' not allowed. Only http/https permitted.")

        if not parsed.hostname:
            raise ValueError("URL must include a hostname")

        hostname = parsed.hostname.lower()

        # Block obvious dangerous hosts
        dangerous_hosts = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "[::1]",
            "169.254.169.254",  # AWS/cloud metadata
            "metadata.google.internal",  # GCP metadata
            "metadata.azure.com",  # Azure metadata
        }

        if hostname in dangerous_hosts:
            raise ValueError(f"Access to '{hostname}' is blocked for security reasons")

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)

            # Block private, loopback, and link-local addresses
            if ip.is_private:
                raise ValueError(f"Access to private IP '{hostname}' is blocked")
            if ip.is_loopback:
                raise ValueError(f"Access to loopback IP '{hostname}' is blocked")
            if ip.is_link_local:
                raise ValueError(f"Access to link-local IP '{hostname}' is blocked")
            if ip.is_reserved:
                raise ValueError(f"Access to reserved IP '{hostname}' is blocked")

        except ValueError:
            # Not an IP address - it's a hostname, which is OK
            # But check for localhost variants
            if "localhost" in hostname or hostname.endswith(".local"):
                raise ValueError(f"Access to local hostname '{hostname}' is blocked")

        logger.debug(f"URL validated for SSRF: {url}")

    def _compile_api_tool(self, tool_def: CustomToolDefinition):
        """Compile an API call tool"""
        import httpx

        # Parse API configuration from implementation
        api_config = json.loads(tool_def.implementation)

        # Reference to self for SSRF validation in nested function
        validate_url = self._validate_url_for_ssrf

        async def api_executor(**kwargs):
            # Build request
            url = api_config["url"]
            method = api_config.get("method", "GET")
            headers = api_config.get("headers", {})

            # Replace placeholders in URL and headers
            for param in tool_def.parameters:
                value = kwargs.get(param.name, param.default)
                url = url.replace(f"{{{param.name}}}", str(value))
                for key in headers:
                    headers[key] = headers[key].replace(f"{{{param.name}}}", str(value))

            # SECURITY: Validate URL to prevent SSRF attacks
            validate_url(url)

            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=kwargs if method in ["POST", "PUT", "PATCH"] else None,
                )

                return {
                    "status_code": response.status_code,
                    "body": response.json() if response.content else None,
                    "headers": dict(response.headers),
                }

        self._compiled_tools[tool_def.name] = api_executor

    def execute_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """
        Execute a custom tool

        Args:
            tool_name: Name of the tool
            **kwargs: Tool parameters

        Returns:
            Execution result
        """
        # Get compiled tool
        if tool_name not in self._compiled_tools:
            tool_def = self.get_tool(tool_name)
            if not tool_def:
                raise ValueError(f"Tool not found: {tool_name}")
            self._compile_tool(tool_def)

        func = self._compiled_tools[tool_name]

        try:
            result = func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
_custom_tool_registry: CustomToolRegistry | None = None


def get_custom_tool_registry() -> CustomToolRegistry:
    """Get or create global custom tool registry"""
    global _custom_tool_registry
    if _custom_tool_registry is None:
        _custom_tool_registry = CustomToolRegistry()
    return _custom_tool_registry


# ===== Example Custom Tools =====

EXAMPLE_PYTHON_TOOL = CustomToolDefinition(
    name="format_code",
    description="Format code using black formatter",
    tool_type=ToolType.PYTHON_FUNCTION,
    parameters=[
        ToolParameter(name="code", type="string", description="Code to format"),
        ToolParameter(
            name="line_length",
            type="integer",
            description="Maximum line length",
            required=False,
            default=88,
        ),
    ],
    implementation="""
import black

def format_code(code: str, line_length: int = 88) -> str:
    try:
        formatted = black.format_str(code, mode=black.Mode(line_length=line_length))
        return formatted
    except Exception as e:
        return f"Error formatting code: {e}"
""",
    category="formatting",
    tags=["python", "formatting", "black"],
)

EXAMPLE_SHELL_TOOL = CustomToolDefinition(
    name="count_lines",
    description="Count lines in a file",
    tool_type=ToolType.SHELL_SCRIPT,
    parameters=[ToolParameter(name="file_path", type="string", description="Path to file")],
    implementation="wc -l ${file_path}",
    category="file_operations",
    tags=["shell", "file", "count"],
)

EXAMPLE_API_TOOL = CustomToolDefinition(
    name="github_search",
    description="Search GitHub repositories",
    tool_type=ToolType.API_CALL,
    parameters=[ToolParameter(name="query", type="string", description="Search query")],
    implementation=json.dumps(
        {
            "url": "https://api.github.com/search/repositories?q={query}",
            "method": "GET",
            "headers": {"Accept": "application/vnd.github.v3+json"},
        }
    ),
    category="api",
    tags=["github", "search", "api"],
)
