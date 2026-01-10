"""
Bash Intelligence Patterns and Templates

Static data for bash command safety validation and NL translation.
Extracted from bash_intelligence.py during P2 decomposition.

Contains:
- DANGEROUS_PATTERNS: Regex patterns for dangerous bash commands
- NL_TEMPLATES: Natural language to bash command templates
- BASH_INDICATORS: Patterns that indicate bash commands
- NL_INDICATORS: Words/patterns indicating natural language
- Helper functions for pattern matching and safety checking
"""

import re
from typing import Dict, List, Optional, Tuple


# ============================================
# DANGEROUS COMMAND PATTERNS
# ============================================

DANGEROUS_PATTERNS: List[str] = [
    # Recursive file removal
    r'\brm\s+-rf\s+/',      # rm -rf /
    r'\brm\s+-rf\s+\*',     # rm -rf *
    r'\brm\s+-rf\s+~',      # rm -rf ~
    r'\brm\s+-rf\s+\.',     # rm -rf .
    r'\brm\s+-rf\s+\./',    # rm -rf ./
    r'\brm\s+-r\s+\*',      # rm -r *
    r'\brm\s+.*\*.*\s+-rf?',  # rm */ -rf or rm * -r

    # Disk operations
    r'\bdd\s+if=',          # dd if= (dangerous write)
    r'\bdd\s+.*of=/dev/',   # dd to device
    r'\b(sudo\s+)?mkfs',    # Format filesystem
    r'\bshred',             # Secure deletion
    r'\bwipefs',            # Wipe filesystem signatures
    r'\bformat\b',          # Format command

    # Permission changes
    r'\bchmod\s+-R\s+777',  # Recursive 777
    r'\bchmod\s+777\s+/',   # 777 on root

    # Redirect to device
    r'>\s*/dev/sd[a-z]',    # > /dev/sda
    r'>\s*/dev/disk',       # > /dev/disk*

    # Truncate file
    r'\b:>',                # :> file

    # Fork bomb and malicious patterns
    r':\(\)\s*\{\s*:\|:&\s*\}',        # :(){:|:&};:
    r'\bwhile\s+true.*do.*done',       # Potential infinite loop with destructive commands

    # Sudo with shell command injection
    r"sudo\s+sh\s+-c\s+['\"].*>.*\/dev\/",   # sudo sh -c '... > /dev/*'
    r"sudo\s+bash\s+-c\s+['\"].*>.*\/dev\/", # sudo bash -c '... > /dev/*'

    # Multiple dangerous operations
    r'&&.*\brm\s+-rf?\s+[/~*\.]',  # Chained with rm -rf
    r'\|.*\brm\s+-rf?\s+[/~*\.]',  # Piped to rm -rf
]
"""
Regex patterns for dangerous bash commands that require confirmation.
Each pattern is designed to catch potentially destructive operations.
"""


# ============================================
# NATURAL LANGUAGE TO BASH TEMPLATES
# ============================================

NL_TEMPLATES: Dict[str, str] = {
    # File operations
    r'(list|show|display)\s+(all\s+)?files': 'ls -lah',
    r'find\s+(.+?)\s+files?': r'find . -name "\1"',
    r'search\s+for\s+"?(.+?)"?\s+in\s+files?': r'grep -r "\1" .',
    r'count\s+lines\s+in\s+(.+)': r'wc -l "\1"',
    r'show\s+disk\s+usage': 'df -h',
    r'show\s+directory\s+size': 'du -sh',

    # Git operations
    r'commit\s+(.+)': r'git add -A && git commit -m "\1"',
    r'push\s+to\s+(.+)': r'git push \1',
    r'create\s+branch\s+(.+)': r'git checkout -b "\1"',
    r'git\s+status': 'git status',
    r'show\s+git\s+log': 'git log --oneline -10',
    r'undo\s+last\s+commit': 'git reset --soft HEAD~1',

    # Process management
    r'kill\s+process\s+(.+)': r'pkill -f "\1"',
    r'show\s+running\s+processes': 'ps aux',
    r'find\s+process\s+(.+)': r'ps aux | grep "\1"',

    # Network
    r'check\s+port\s+(\d+)': r'lsof -i :\1',
    r'test\s+connection\s+to\s+(.+)': r'ping -c 4 \1',
    r'download\s+(.+)': r'curl -O "\1"',

    # System
    r'show\s+environment': 'env',
    r'which\s+(.+)': r'which "\1"',
    r'create\s+directory\s+(.+)': r'mkdir -p "\1"',
    r'go\s+to\s+(.+)': r'cd "\1"',
}
"""
Common natural language patterns and their bash command translations.
Patterns use regex capture groups for dynamic substitution.

Examples:
    >>> match_nl_template("list all files")
    'ls -lah'
    >>> match_nl_template("find python files")
    'find . -name "python"'
"""


# ============================================
# CLASSIFICATION INDICATORS
# ============================================

NL_INDICATOR_WORDS: List[str] = [
    'please',
    'can you',
    'could you',
    'how do i',
    'show me',
    'help me',
    'i want to',
    'i need to',
]
"""Words/phrases that indicate natural language input (not a direct command)."""


IMPROVEMENT_PATTERNS: Dict[str, str] = {
    r'\bfind\b.*\|\s*grep': "Consider using 'find -name' instead of piping to grep",
    r'\bcat\b.*\|\s*grep': "Consider using 'grep' directly instead of 'cat | grep'",
    r'\bls\s+\|': "Consider using ls options instead of piping",
}
"""Patterns for suggesting command improvements."""


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_dangerous_command(command: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a command matches any dangerous patterns.

    Args:
        command: Bash command to check

    Returns:
        Tuple of (is_dangerous, matched_pattern)

    Examples:
        >>> is_dangerous_command("rm -rf /")
        (True, '\\brm\\s+-rf\\s+/')
        >>> is_dangerous_command("ls -la")
        (False, None)
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, pattern
    return False, None


def match_nl_template(text: str) -> Optional[str]:
    """
    Try to match text against NL templates.

    Args:
        text: Natural language input

    Returns:
        Bash command if matched, None otherwise

    Examples:
        >>> match_nl_template("list all files")
        'ls -lah'
        >>> match_nl_template("hello world")
        None
    """
    text_lower = text.lower().strip()

    for pattern, template in NL_TEMPLATES.items():
        match = re.search(pattern, text_lower)
        if match:
            # Replace capture groups if present
            if '\\1' in template:
                cmd = re.sub(pattern, template, text_lower)
            else:
                cmd = template
            return cmd

    return None


def has_nl_indicators(text: str) -> bool:
    """
    Check if text contains natural language indicators.

    Args:
        text: Input text to check

    Returns:
        True if text appears to be natural language

    Examples:
        >>> has_nl_indicators("please show me the files")
        True
        >>> has_nl_indicators("ls -la")
        False
    """
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in NL_INDICATOR_WORDS)


def get_command_improvements(command: str) -> List[str]:
    """
    Get suggestions for improving a bash command.

    Args:
        command: Bash command to analyze

    Returns:
        List of improvement suggestions

    Examples:
        >>> get_command_improvements("cat file.txt | grep pattern")
        ["Consider using 'grep' directly instead of 'cat | grep'"]
    """
    suggestions = []

    for pattern, suggestion in IMPROVEMENT_PATTERNS.items():
        if re.search(pattern, command):
            suggestions.append(f"💡 {suggestion}")

    # Special case for rm -r
    if 'rm' in command and '-r' in command:
        suggestions.append("⚠️  Use 'rm -r' carefully - specify explicit paths to avoid accidents")

    return suggestions


def check_root_operation(command: str) -> bool:
    """
    Check if command operates on root directory.

    Args:
        command: Bash command to check

    Returns:
        True if command appears to operate on root

    Examples:
        >>> check_root_operation("rm -rf /")
        True
        >>> check_root_operation("rm -rf ./temp")
        False
    """
    return bool(re.search(r'[/\s](/+|~)\s*$', command))


def check_sudo_rm(command: str) -> bool:
    """
    Check if command uses sudo with rm.

    Args:
        command: Bash command to check

    Returns:
        True if command uses sudo + rm

    Examples:
        >>> check_sudo_rm("sudo rm -rf /tmp")
        True
        >>> check_sudo_rm("rm file.txt")
        False
    """
    return command.strip().startswith('sudo') and 'rm' in command


__all__ = [
    # Pattern data
    "DANGEROUS_PATTERNS",
    "NL_TEMPLATES",
    "NL_INDICATOR_WORDS",
    "IMPROVEMENT_PATTERNS",
    # Helper functions
    "is_dangerous_command",
    "match_nl_template",
    "has_nl_indicators",
    "get_command_improvements",
    "check_root_operation",
    "check_sudo_rm",
]
