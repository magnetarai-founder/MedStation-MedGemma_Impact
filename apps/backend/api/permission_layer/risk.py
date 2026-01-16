"""
Permission Layer Risk Assessment and Utilities

Pure functions and static data for command risk assessment.
Extracted from permission_layer.py during P2 decomposition.

Contains:
- Risk pattern constants (CRITICAL, HIGH, MEDIUM, LOW)
- Dangerous terms for command highlighting
- Command and flag explanations
- assess_risk() pure function
- matches_pattern() pure function
- highlight_command() pure function
- create_similar_pattern() pure function
"""

import re
from typing import List, Tuple, Optional

# Re-export RiskLevel for convenience (avoid circular imports)
# Users should import RiskLevel from permission_layer.py directly
# This is just for internal use


# ============================================
# RISK PATTERN CONSTANTS
# ============================================

CRITICAL_RISK_PATTERNS: List[str] = [
    "rm -rf /",
    "rm -rf ~",
    "format",
    "mkfs",
    "> /dev/",
    "dd if=",
    "fork bomb",
]
"""Patterns that indicate critical/destructive operations"""

HIGH_RISK_PATTERNS: List[str] = [
    "sudo",
    "rm -rf",
    "chmod 777",
    "chown",
    "kill -9",
    "killall",
    "systemctl stop",
]
"""Patterns that indicate high-risk system modifications"""

MEDIUM_RISK_PATTERNS: List[str] = [
    "rm ",
    "delete",
    "drop",
    "truncate",
    "mv ",
    "cp -f",
    "install",
    "uninstall",
    "git push --force",
    "curl",
    "wget",
]
"""Patterns that indicate medium-risk file or network operations"""

LOW_RISK_PATTERNS: List[str] = [
    "mkdir",
    "touch",
    "echo >",
    "cat >",
    "pip install",
    "npm install",
    "apt-get",
    "git commit",
    "git add",
]
"""Patterns that indicate low-risk file creation operations"""


# ============================================
# COMMAND HIGHLIGHTING
# ============================================

DANGEROUS_TERMS: List[str] = [
    "rm",
    "delete",
    "sudo",
    "kill",
    "format",
    "dd",
    "mkfs",
    "chmod",
    "chown",
]
"""Terms to highlight in red when displaying commands"""


# ============================================
# COMMAND EXPLANATIONS (for help/explain feature)
# ============================================

COMMAND_EXPLANATIONS: dict[str, str] = {
    "rm": "Remove/delete files or directories",
    "ls": "List directory contents",
    "cd": "Change directory",
    "cp": "Copy files or directories",
    "mv": "Move/rename files or directories",
    "mkdir": "Create directories",
    "sudo": "Run command with administrator privileges",
    "kill": "Terminate a process",
    "curl": "Transfer data from/to a server",
    "wget": "Download files from the internet",
    "git": "Version control operations",
    "pip": "Python package management",
    "npm": "Node.js package management",
    "docker": "Container management",
}
"""Explanations for common commands"""

FLAG_EXPLANATIONS: dict[str, str] = {
    "-r": "Recursive (include subdirectories)",
    "-f": "Force (no confirmation)",
    "-rf": "Recursive + Force (DANGEROUS!)",
    "-la": "List all files with details",
    "-i": "Interactive (ask before each action)",
    "-v": "Verbose (show details)",
}
"""Explanations for common command flags"""


# ============================================
# FILE OPERATION COMMANDS (for pattern matching)
# ============================================

FILE_OPERATION_COMMANDS: List[str] = ["rm", "cp", "mv", "ls", "cat", "mkdir"]
"""Commands that operate on files (patterns match command only, not paths)"""

PACKAGE_MANAGER_COMMANDS: List[str] = ["pip", "npm", "apt-get", "brew"]
"""Package manager commands (patterns include first subcommand)"""


# ============================================
# PURE FUNCTIONS
# ============================================

def assess_risk_level(command: str) -> Tuple[int, str]:
    """
    Assess the risk level of a command.

    This is a pure function that returns (risk_level_int, reason_string).
    Use this with RiskLevel enum from permission_layer.py.

    Risk levels:
        0 = SAFE
        1 = LOW
        2 = MEDIUM
        3 = HIGH
        4 = CRITICAL

    Args:
        command: Command string to assess

    Returns:
        Tuple of (risk_level: int, reason: str)
    """
    command_lower = command.lower()

    # Critical risk patterns
    if any(pattern in command_lower for pattern in CRITICAL_RISK_PATTERNS):
        return 4, "Potentially destructive operation"

    # High risk patterns
    if any(pattern in command_lower for pattern in HIGH_RISK_PATTERNS):
        return 3, "System modification or termination"

    # Medium risk patterns
    if any(pattern in command_lower for pattern in MEDIUM_RISK_PATTERNS):
        return 2, "File modification or network operation"

    # Low risk patterns
    if any(pattern in command_lower for pattern in LOW_RISK_PATTERNS):
        return 1, "Creating or modifying user files"

    # Safe operations
    return 0, "Read-only or safe operation"


def matches_pattern(
    command: str,
    pattern: str,
    command_operation_type: str,
    rule_operation_type: str,
) -> bool:
    """
    Check if a command matches a rule pattern.

    Supports three pattern types:
    - Exact match: pattern is a substring of command
    - Wildcard: pattern is "*" (matches everything)
    - Regex: pattern starts with "regex:" followed by regex

    Args:
        command: The command to check
        pattern: The pattern to match against
        command_operation_type: Operation type of the command
        rule_operation_type: Operation type required by the rule (* = any)

    Returns:
        True if command matches the rule pattern
    """
    # Check operation type
    if rule_operation_type != "*" and rule_operation_type != command_operation_type:
        return False

    # Check command pattern
    if pattern == "*":
        return True
    elif pattern.startswith("regex:"):
        regex_pattern = pattern[6:]
        return bool(re.match(regex_pattern, command))
    else:
        return pattern in command


def highlight_dangerous_terms(
    command: str,
    dangerous_terms: Optional[List[str]] = None,
    red_code: str = "\033[91m",
    reset_code: str = "\033[0m",
) -> str:
    """
    Add color highlighting to dangerous parts of commands.

    Args:
        command: Command string to highlight
        dangerous_terms: List of terms to highlight (defaults to DANGEROUS_TERMS)
        red_code: ANSI escape code for red (default: \033[91m)
        reset_code: ANSI escape code to reset (default: \033[0m)

    Returns:
        Command string with dangerous terms wrapped in color codes
    """
    if dangerous_terms is None:
        dangerous_terms = DANGEROUS_TERMS

    highlighted = command
    for term in dangerous_terms:
        highlighted = highlighted.replace(term, f"{red_code}{term}{reset_code}")

    return highlighted


def create_similar_pattern(command: str) -> str:
    """
    Create a pattern for matching similar commands.

    This is used for "yes to similar" functionality.

    Pattern rules:
    - File operations (rm, cp, mv, ls, cat, mkdir): Match command prefix only
    - Git operations: Match "git <subcommand>"
    - Package managers: Match "<manager> <subcommand>"
    - Other: Match base command only

    Args:
        command: Full command string

    Returns:
        Pattern string for matching similar commands
    """
    parts = command.split()
    if not parts:
        return command

    base = parts[0]

    # For file operations, match the command but not the paths
    if base in FILE_OPERATION_COMMANDS:
        return f"{base} "

    # For git operations
    if base == "git" and len(parts) > 1:
        return f"git {parts[1]}"

    # For package managers
    if base in PACKAGE_MANAGER_COMMANDS and len(parts) > 1:
        return f"{base} {parts[1]}"

    return base


def get_command_explanation(command: str) -> Optional[str]:
    """
    Get explanation for a command.

    Args:
        command: Base command (e.g., "rm", "git", "pip")

    Returns:
        Explanation string or None if not found
    """
    return COMMAND_EXPLANATIONS.get(command)


def get_flag_explanation(flag: str) -> Optional[str]:
    """
    Get explanation for a command flag.

    Args:
        flag: Flag string (e.g., "-r", "-rf", "-v")

    Returns:
        Explanation string or None if not found
    """
    return FLAG_EXPLANATIONS.get(flag)


def extract_command_parts(command: str) -> Tuple[str, List[str], List[str]]:
    """
    Extract parts of a command for analysis.

    Args:
        command: Full command string

    Returns:
        Tuple of (base_command, flags, arguments)
    """
    parts = command.split()
    if not parts:
        return "", [], []

    base_cmd = parts[0]
    flags = [p for p in parts[1:] if p.startswith("-")]
    args = [p for p in parts[1:] if not p.startswith("-")]

    return base_cmd, flags, args


__all__ = [
    # Risk pattern constants
    "CRITICAL_RISK_PATTERNS",
    "HIGH_RISK_PATTERNS",
    "MEDIUM_RISK_PATTERNS",
    "LOW_RISK_PATTERNS",
    # Highlight/explanation constants
    "DANGEROUS_TERMS",
    "COMMAND_EXPLANATIONS",
    "FLAG_EXPLANATIONS",
    # Command type constants
    "FILE_OPERATION_COMMANDS",
    "PACKAGE_MANAGER_COMMANDS",
    # Pure functions
    "assess_risk_level",
    "matches_pattern",
    "highlight_dangerous_terms",
    "create_similar_pattern",
    "get_command_explanation",
    "get_flag_explanation",
    "extract_command_parts",
]
