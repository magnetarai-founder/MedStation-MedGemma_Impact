"""
Compatibility Shim for Token Counter

The implementation now lives in the `api.llm` package:
- api.llm.tokens: TokenCounter class

This shim maintains backward compatibility.
"""

from api.llm.tokens import (
    TokenCounter,
    get_token_counter,
    DEFAULT_ENCODING,
)

__all__ = [
    "TokenCounter",
    "get_token_counter",
    "DEFAULT_ENCODING",
]
