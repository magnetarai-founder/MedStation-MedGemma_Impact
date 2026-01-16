"""
Token counter utility using tiktoken
Provides accurate token counts for chat context management
"""

import tiktoken
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Default to cl100k_base encoding (GPT-4, GPT-3.5-turbo)
# This is a good approximation for most models
DEFAULT_ENCODING = "cl100k_base"


class TokenCounter:
    """Token counting utility"""

    def __init__(self, encoding_name: str = DEFAULT_ENCODING):
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"✅ Token counter initialized with {encoding_name} encoding")
        except Exception as e:
            logger.error(f"Failed to load tiktoken encoding: {e}")
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in a single text string"""
        if not self.encoding:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4

        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Token counting error: {e}")
            return len(text) // 4

    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens for a list of chat messages
        Follows OpenAI's message formatting overhead
        """
        if not self.encoding:
            # Fallback estimation
            total = 0
            for msg in messages:
                total += len(msg.get("content", "")) // 4
            return total

        try:
            tokens = 0

            # Return 0 for empty message lists
            if not messages:
                return 0

            for message in messages:
                # Message overhead: 4 tokens per message
                tokens += 4

                # Count role tokens
                tokens += len(self.encoding.encode(message.get("role", "")))

                # Count content tokens
                tokens += len(self.encoding.encode(message.get("content", "")))

            # Add 2 tokens for priming (only if there are messages)
            tokens += 2

            return tokens

        except Exception as e:
            logger.error(f"Message token counting error: {e}")
            # Fallback
            total = 0
            for msg in messages:
                total += len(msg.get("content", "")) // 4
            return total


# Singleton instance
_token_counter: TokenCounter = None


def get_token_counter() -> TokenCounter:
    """Get singleton token counter instance"""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
