"""
Compatibility Shim for Bash Intelligence

The implementation now lives in the `api.bash` package:
- api.bash.intelligence: BashIntelligence class

This shim maintains backward compatibility.
"""

from api.bash.intelligence import BashIntelligence, get_bash_intelligence
from api.bash.patterns import (
    DANGEROUS_PATTERNS,
    NL_TEMPLATES,
    is_dangerous_command,
)

__all__ = [
    "BashIntelligence",
    "get_bash_intelligence",
    "DANGEROUS_PATTERNS",
    "NL_TEMPLATES",
    "is_dangerous_command",
]
