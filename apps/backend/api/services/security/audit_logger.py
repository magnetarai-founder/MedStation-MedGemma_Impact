"""
Audit Logging for Security-Critical Operations

Logs all security-relevant actions including command execution,
file operations, and authentication attempts.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """
    Audit logger for security-critical operations.

    Logs are written to both application log and separate audit log file.
    """

    def __init__(self, audit_log_path: Path | None = None):
        """
        Initialize audit logger.

        Args:
            audit_log_path: Path to audit log file (defaults to logs/audit.log)
        """
        self.logger = logging.getLogger("magnetarcode.audit")

        # Setup audit log file handler if path provided
        if audit_log_path:
            self.audit_log_path = audit_log_path
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file handler
            file_handler = logging.FileHandler(self.audit_log_path)
            file_handler.setLevel(logging.INFO)

            # JSON format for easy parsing
            file_handler.setFormatter(logging.Formatter("%(message)s"))

            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def _create_audit_entry(
        self,
        event_type: str,
        action: str,
        details: dict[str, Any],
        user: str = "system",
        success: bool = True,
    ) -> dict[str, Any]:
        """Create standardized audit entry"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "action": action,
            "user": user,
            "success": success,
            "details": details,
        }

    def log_command_execution(
        self,
        command: str,
        args: list,
        workspace: str | None = None,
        user: str = "system",
        success: bool = True,
        exit_code: int | None = None,
        error: str | None = None,
    ):
        """
        Log command execution.

        Args:
            command: Base command executed
            args: Command arguments
            workspace: Workspace path
            user: User who executed command
            success: Whether execution succeeded
            exit_code: Command exit code
            error: Error message if failed
        """
        entry = self._create_audit_entry(
            event_type="command_execution",
            action=f"{command} {' '.join(args[:3])}...",  # Truncate long commands
            details={
                "command": command,
                "args": args,
                "workspace": workspace,
                "exit_code": exit_code,
                "error": error,
            },
            user=user,
            success=success,
        )

        self.logger.info(json.dumps(entry))

    def log_file_operation(
        self,
        operation: str,  # "read", "write", "delete"
        file_path: str,
        user: str = "system",
        success: bool = True,
        error: str | None = None,
    ):
        """
        Log file operation.

        Args:
            operation: Type of operation
            file_path: Path to file
            user: User performing operation
            success: Whether operation succeeded
            error: Error message if failed
        """
        entry = self._create_audit_entry(
            event_type="file_operation",
            action=f"{operation} {file_path}",
            details={"operation": operation, "file_path": file_path, "error": error},
            user=user,
            success=success,
        )

        self.logger.info(json.dumps(entry))

    def log_authentication(
        self,
        user: str,
        method: str,  # "jwt", "static_token", "api_key"
        success: bool,
        client_ip: str | None = None,
        error: str | None = None,
    ):
        """
        Log authentication attempt.

        Args:
            user: User attempting authentication
            method: Authentication method used
            success: Whether authentication succeeded
            client_ip: Client IP address
            error: Error message if failed
        """
        entry = self._create_audit_entry(
            event_type="authentication",
            action=f"auth via {method}",
            details={"method": method, "client_ip": client_ip, "error": error},
            user=user,
            success=success,
        )

        self.logger.info(json.dumps(entry))

    def log_custom_tool_execution(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        user: str = "system",
        success: bool = True,
        result: Any | None = None,
        error: str | None = None,
    ):
        """
        Log custom tool execution.

        Args:
            tool_name: Name of custom tool
            parameters: Tool parameters
            user: User executing tool
            success: Whether execution succeeded
            result: Execution result (truncated)
            error: Error message if failed
        """
        entry = self._create_audit_entry(
            event_type="custom_tool_execution",
            action=f"execute {tool_name}",
            details={
                "tool_name": tool_name,
                "parameters": parameters,
                "result": str(result)[:200] if result else None,  # Truncate
                "error": error,
            },
            user=user,
            success=success,
        )

        self.logger.info(json.dumps(entry))

    def log_agent_execution(
        self,
        agent_role: str,
        task: str,
        workspace: str | None = None,
        user: str = "system",
        success: bool = True,
        iterations: int | None = None,
        error: str | None = None,
    ):
        """
        Log agent task execution.

        Args:
            agent_role: Role of agent (code, test, debug, etc.)
            task: Task description
            workspace: Workspace path
            user: User initiating execution
            success: Whether execution succeeded
            iterations: Number of iterations completed
            error: Error message if failed
        """
        entry = self._create_audit_entry(
            event_type="agent_execution",
            action=f"{agent_role} agent: {task[:50]}...",
            details={
                "agent_role": agent_role,
                "task": task,
                "workspace": workspace,
                "iterations": iterations,
                "error": error,
            },
            user=user,
            success=success,
        )

        self.logger.info(json.dumps(entry))


# Global audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger"""
    global _audit_logger
    if _audit_logger is None:
        # Default to logs/audit.log
        log_path = Path("logs/audit.log")
        _audit_logger = AuditLogger(log_path)
    return _audit_logger


def log_command_execution(command: str, args: list, **kwargs):
    """Convenience function for logging command execution"""
    get_audit_logger().log_command_execution(command, args, **kwargs)
