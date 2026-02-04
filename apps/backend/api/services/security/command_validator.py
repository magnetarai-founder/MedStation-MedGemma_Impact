"""
Command Validation and Injection Prevention

Provides secure command validation to prevent command injection attacks.
All shell commands must be validated before execution.
"""

import re
import shlex
from pathlib import Path


class CommandValidationError(Exception):
    """Raised when command validation fails"""

    pass


class CommandValidator:
    """
    Validates shell commands to prevent injection attacks.

    Uses a whitelist approach - only explicitly allowed commands can run.
    """

    # Allowed base commands (whitelist)
    ALLOWED_COMMANDS = {
        # File operations
        "ls",
        "cat",
        "head",
        "tail",
        "find",
        "stat",
        # Version control
        "git",
        # Code tools
        "python",
        "python3",
        "node",
        "npm",
        "pip",
        "pytest",
        "black",
        "ruff",
        "mypy",
        "flake8",
        "pylint",
        "swift",
        "cargo",
        "go",
        # Search and text processing
        "grep",
        "rg",
        "ag",
        "ack",
        "sed",
        "awk",
        # Build tools
        "make",
        "cmake",
        "gradle",
        "mvn",
        # Testing
        "jest",
        "mocha",
        "vitest",
        # Database
        "sqlite3",
        "psql",
        "mysql",
        # Utilities
        "echo",
        "pwd",
        "which",
        "date",
        "wc",
        "sort",
        "uniq",
        "curl",
        "wget",
    }

    # Safe git subcommands
    SAFE_GIT_SUBCOMMANDS = {
        "status",
        "diff",
        "log",
        "show",
        "branch",
        "remote",
        "add",
        "commit",
        "push",
        "pull",
        "fetch",
        "checkout",
        "merge",
        "rebase",
        "stash",
        "tag",
        "clone",
    }

    # Dangerous patterns that should never appear
    DANGEROUS_PATTERNS = [
        r";\s*",  # Command chaining with semicolon
        r"\|\s*",  # Piping (can be dangerous)
        r"&&",  # AND chaining
        r"\|\|",  # OR chaining
        r"`",  # Command substitution
        r"\$\(",  # Command substitution
        r">\s*/dev/",  # Writing to devices
        r">\s*/etc/",  # Writing to system dirs
        r">\s*/bin/",  # Writing to binary dirs
        r">\s*/usr/",  # Writing to system dirs
        r"rm\s+-rf\s+/",  # Destructive rm from root
        r"chmod\s+777",  # Overly permissive chmod
        r"eval\s*",  # Code evaluation
        r"exec\s*",  # Code execution
        r"\.\./",  # Path traversal
        r"~/.ssh",  # SSH directory access
        r"~/.aws",  # AWS credentials
        r"/etc/passwd",  # System files
        r"/etc/shadow",  # System files
    ]

    def __init__(self, workspace_root: Path | None = None, strict_mode: bool = True):
        """
        Initialize command validator.

        Args:
            workspace_root: Root directory for file operations (for path validation)
            strict_mode: If True, reject any command with suspicious patterns
        """
        self.workspace_root = workspace_root
        self.strict_mode = strict_mode

    def validate(self, command: str | list[str]) -> tuple[str, list[str]]:
        """
        Validate a command for safe execution.

        Args:
            command: Command string or list of arguments

        Returns:
            Tuple of (base_command, args) if valid

        Raises:
            CommandValidationError: If command is invalid or dangerous
        """
        # Handle both string and list inputs
        if isinstance(command, str):
            # Parse command string safely
            try:
                parts = shlex.split(command)
            except ValueError as e:
                raise CommandValidationError(f"Invalid command syntax: {e}")
        else:
            parts = command

        if not parts:
            raise CommandValidationError("Empty command")

        base_command = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        # Check for dangerous patterns in the full command
        full_command = " ".join(parts)
        self._check_dangerous_patterns(full_command)

        # Validate base command is in whitelist
        if base_command not in self.ALLOWED_COMMANDS:
            raise CommandValidationError(
                f"Command '{base_command}' is not in the allowed list. "
                f"Allowed commands: {', '.join(sorted(self.ALLOWED_COMMANDS))}"
            )

        # Special validation for git commands
        if base_command == "git":
            self._validate_git_command(args)

        # Validate arguments don't contain injection attempts
        for arg in args:
            self._validate_argument(arg)

        # Validate file paths if workspace_root is set
        if self.workspace_root:
            self._validate_paths(args)

        return base_command, args

    def _check_dangerous_patterns(self, command: str):
        """Check for dangerous patterns in command"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                raise CommandValidationError(f"Command contains dangerous pattern: {pattern}")

    def _validate_git_command(self, args: list[str]):
        """Validate git subcommand is safe"""
        if not args:
            return  # Just "git" is okay (shows help)

        subcommand = args[0]
        if subcommand not in self.SAFE_GIT_SUBCOMMANDS:
            raise CommandValidationError(
                f"Git subcommand '{subcommand}' is not allowed. "
                f"Allowed: {', '.join(sorted(self.SAFE_GIT_SUBCOMMANDS))}"
            )

    def _validate_argument(self, arg: str):
        """Validate individual argument is safe"""
        # Check for command substitution
        if "`" in arg or "$(" in arg:
            raise CommandValidationError(f"Argument contains command substitution: {arg}")

        # Check for shell metacharacters
        dangerous_chars = [";", "|", "&", ">", "<", "$", "`"]
        for char in dangerous_chars:
            if char in arg and self.strict_mode:
                # Allow some chars in specific contexts
                if char == ">" and arg.startswith("--"):
                    continue  # Allow in flags like --output=file.txt
                if char == "$" and arg.startswith("--"):
                    continue  # Allow in flags like --var=$VAR

                raise CommandValidationError(
                    f"Argument contains dangerous character '{char}': {arg}"
                )

    def _validate_paths(self, args: list[str]):
        """Validate file paths are within workspace"""
        for arg in args:
            # Skip flags and non-path arguments
            if arg.startswith("-"):
                continue

            # Check if argument looks like a path
            if "/" in arg or arg.endswith((".py", ".js", ".ts", ".txt", ".md")):
                try:
                    path = Path(arg).resolve()
                    workspace = self.workspace_root.resolve()

                    # Check if path is under workspace
                    if not path.is_relative_to(workspace):
                        raise CommandValidationError(f"Path '{arg}' is outside workspace root")
                except (ValueError, OSError) as e:
                    raise CommandValidationError(f"Invalid path '{arg}': {e}")

    def is_safe(self, command: str | list[str]) -> bool:
        """
        Check if command is safe without raising exception.

        Args:
            command: Command to validate

        Returns:
            True if safe, False otherwise
        """
        try:
            self.validate(command)
            return True
        except CommandValidationError:
            return False


# Global validator instance
_default_validator = CommandValidator(strict_mode=True)


def validate_command(
    command: str | list[str], workspace_root: Path | None = None
) -> tuple[str, list[str]]:
    """
    Validate a command for safe execution (convenience function).

    Args:
        command: Command string or list
        workspace_root: Optional workspace root for path validation

    Returns:
        Tuple of (base_command, args)

    Raises:
        CommandValidationError: If command is invalid
    """
    if workspace_root:
        validator = CommandValidator(workspace_root=workspace_root)
        return validator.validate(command)
    else:
        return _default_validator.validate(command)


def is_safe_command(command: str | list[str]) -> bool:
    """
    Check if command is safe (convenience function).

    Args:
        command: Command to check

    Returns:
        True if safe, False otherwise
    """
    return _default_validator.is_safe(command)
