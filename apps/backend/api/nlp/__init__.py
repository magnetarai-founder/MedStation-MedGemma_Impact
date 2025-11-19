"""
NLP Template Library - Modular Package
Intent classification and entity extraction for natural language understanding.
"""

# Re-export types
from .types import NLPTemplate, IntentCategory

# Re-export core library
from .core import CoreNLPLibrary

__all__ = [
    'NLPTemplate',
    'IntentCategory',
    'CoreNLPLibrary',
]
