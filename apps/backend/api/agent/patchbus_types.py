"""
PatchBus Types - Dataclass for change proposals

Extracted from patchbus.py during P2 decomposition.
Contains:
- ChangeProposal (unified change proposal format)
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChangeProposal:
    """Unified Change Proposal Format (UCPF)"""
    description: str
    diff: str  # unified diff text
    affected_files: List[str] = field(default_factory=list)
    confidence: float = 0.6
    rationale: Optional[str] = None
    test_hints: List[str] = field(default_factory=list)
    dry_run: bool = False


__all__ = [
    "ChangeProposal",
]
