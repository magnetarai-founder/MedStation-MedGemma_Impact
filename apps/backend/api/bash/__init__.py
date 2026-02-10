"""
Bash Intelligence Package

Bash command intelligence for MedStation terminal:
- Natural language to bash translation
- Command safety validation
- Context-aware suggestions
"""

from api.bash.patterns import (
    DANGEROUS_PATTERNS,
    NL_TEMPLATES,
    NL_INDICATOR_WORDS,
    is_dangerous_command,
    match_nl_template,
    has_nl_indicators,
    get_command_improvements,
    check_root_operation,
    check_sudo_rm,
)
from api.bash.intelligence import BashIntelligence, get_bash_intelligence

__all__ = [
    # Patterns
    "DANGEROUS_PATTERNS",
    "NL_TEMPLATES",
    "NL_INDICATOR_WORDS",
    # Helper functions
    "is_dangerous_command",
    "match_nl_template",
    "has_nl_indicators",
    "get_command_improvements",
    "check_root_operation",
    "check_sudo_rm",
    # Intelligence class
    "BashIntelligence",
    "get_bash_intelligence",
]
