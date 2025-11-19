"""
Shared types for NLP Template Library.
Moved from core_nlp_templates.py for modular architecture.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re


class IntentCategory(Enum):
    """Categories of user intent"""
    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    SYSTEM_OPERATION = "system_operation"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    LEARNING = "learning"


@dataclass
class NLPTemplate:
    """Natural Language Processing Template"""
    id: str
    name: str
    category: IntentCategory
    patterns: List[str]  # Regex patterns to match
    keywords: List[str]  # Key words that signal this intent
    entities: List[str]  # Entities to extract (file, function, variable, etc.)
    response_template: str
    tool_suggestions: List[str]
    confidence_threshold: float = 0.7
    examples: List[str] = None

    def match(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if text matches this template"""
        text_lower = text.lower()

        # Check patterns
        for pattern in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
                return True, {"pattern": pattern, "groups": match.groups()}

        # Check keywords (weighted)
        keyword_matches = sum(1 for kw in self.keywords if kw in text_lower)
        if keyword_matches >= len(self.keywords) * 0.5:
            return True, {"keywords": keyword_matches}

        return False, {}
