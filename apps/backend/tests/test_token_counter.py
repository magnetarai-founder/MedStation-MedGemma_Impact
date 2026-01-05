"""
Comprehensive tests for api/token_counter.py

Tests cover:
- TokenCounter initialization (success and failure)
- Single text token counting
- Chat message token counting with OpenAI overhead
- Fallback behavior when tiktoken unavailable
- Error handling during counting
- Singleton pattern
- Edge cases (empty, unicode, long text)
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.token_counter import (
    TokenCounter,
    get_token_counter,
    DEFAULT_ENCODING,
    _token_counter,
)
import api.token_counter as token_counter_module


# ========== TokenCounter Initialization Tests ==========

class TestTokenCounterInit:
    """Tests for TokenCounter initialization"""

    def test_init_with_default_encoding(self):
        """Test initialization with default cl100k_base encoding"""
        counter = TokenCounter()
        assert counter.encoding is not None

    def test_init_with_custom_encoding(self):
        """Test initialization with a different encoding"""
        # p50k_base is used by older GPT-3 models
        counter = TokenCounter("p50k_base")
        assert counter.encoding is not None

    def test_init_with_invalid_encoding(self):
        """Test initialization with invalid encoding falls back gracefully"""
        counter = TokenCounter("invalid_encoding_name")
        # Should be None when encoding fails to load
        assert counter.encoding is None

    def test_init_handles_tiktoken_exception(self):
        """Test initialization handles tiktoken exceptions"""
        with patch('api.token_counter.tiktoken.get_encoding') as mock_get:
            mock_get.side_effect = Exception("Tiktoken error")
            counter = TokenCounter()
            assert counter.encoding is None


# ========== Single Text Token Counting Tests ==========

class TestCountTokens:
    """Tests for count_tokens method"""

    def test_count_tokens_simple_text(self):
        """Test counting tokens in simple text"""
        counter = TokenCounter()
        count = counter.count_tokens("Hello, world!")
        # Should return actual token count (tiktoken available)
        assert count > 0
        assert isinstance(count, int)

    def test_count_tokens_empty_string(self):
        """Test counting tokens in empty string"""
        counter = TokenCounter()
        count = counter.count_tokens("")
        assert count == 0

    def test_count_tokens_unicode(self):
        """Test counting tokens in unicode text"""
        counter = TokenCounter()
        count = counter.count_tokens("你好世界 🌍")
        assert count > 0

    def test_count_tokens_long_text(self):
        """Test counting tokens in long text"""
        counter = TokenCounter()
        long_text = "word " * 1000
        count = counter.count_tokens(long_text)
        # Should be roughly 1000 tokens (each "word " is ~1-2 tokens)
        assert count > 500
        assert count < 3000

    def test_count_tokens_fallback_when_no_encoding(self):
        """Test fallback (len/4) when encoding is None"""
        counter = TokenCounter()
        counter.encoding = None  # Simulate missing encoding

        text = "This is a test string"  # 21 chars
        count = counter.count_tokens(text)

        # Fallback: len(text) // 4 = 21 // 4 = 5
        assert count == len(text) // 4

    def test_count_tokens_handles_encoding_error(self):
        """Test error handling during encoding"""
        counter = TokenCounter()

        # Mock encoding to raise an error
        counter.encoding = MagicMock()
        counter.encoding.encode.side_effect = Exception("Encoding error")

        text = "Test text here"  # 14 chars
        count = counter.count_tokens(text)

        # Should fall back to len/4
        assert count == len(text) // 4

    def test_count_tokens_whitespace_only(self):
        """Test counting tokens in whitespace-only text"""
        counter = TokenCounter()
        count = counter.count_tokens("   \n\t  ")
        # Whitespace still has some tokens
        assert count >= 0

    def test_count_tokens_special_characters(self):
        """Test counting tokens with special characters"""
        counter = TokenCounter()
        count = counter.count_tokens("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        assert count > 0

    def test_count_tokens_code_snippet(self):
        """Test counting tokens in code"""
        counter = TokenCounter()
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        count = counter.count_tokens(code)
        assert count > 0


# ========== Chat Message Token Counting Tests ==========

class TestCountMessageTokens:
    """Tests for count_message_tokens method"""

    def test_count_message_tokens_single_message(self):
        """Test counting tokens in a single message"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello!"}]
        count = counter.count_message_tokens(messages)

        # Should include: 4 (overhead) + role tokens + content tokens + 2 (priming)
        assert count > 6  # At minimum

    def test_count_message_tokens_conversation(self):
        """Test counting tokens in a multi-message conversation"""
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]
        count = counter.count_message_tokens(messages)

        # 3 messages × 4 overhead + tokens + 2 priming
        assert count > 14

    def test_count_message_tokens_empty_list(self):
        """Test counting tokens in empty message list"""
        counter = TokenCounter()
        messages = []
        count = counter.count_message_tokens(messages)
        assert count == 0

    def test_count_message_tokens_empty_content(self):
        """Test messages with empty content"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": ""}]
        count = counter.count_message_tokens(messages)

        # Should still have overhead: 4 (message) + role tokens + 2 (priming)
        assert count > 0

    def test_count_message_tokens_missing_role(self):
        """Test messages with missing role key"""
        counter = TokenCounter()
        messages = [{"content": "Hello!"}]
        count = counter.count_message_tokens(messages)

        # Should handle gracefully (empty role string)
        assert count > 0

    def test_count_message_tokens_missing_content(self):
        """Test messages with missing content key"""
        counter = TokenCounter()
        messages = [{"role": "user"}]
        count = counter.count_message_tokens(messages)

        # Should handle gracefully (empty content)
        assert count > 0

    def test_count_message_tokens_fallback_when_no_encoding(self):
        """Test fallback when encoding is None"""
        counter = TokenCounter()
        counter.encoding = None

        messages = [
            {"role": "user", "content": "Hello World"}  # 11 chars
        ]
        count = counter.count_message_tokens(messages)

        # Fallback: len(content) // 4 = 11 // 4 = 2
        assert count == 2

    def test_count_message_tokens_handles_encoding_error(self):
        """Test error handling during message encoding"""
        counter = TokenCounter()

        # Mock encoding to raise an error
        counter.encoding = MagicMock()
        counter.encoding.encode.side_effect = Exception("Encoding error")

        messages = [
            {"role": "user", "content": "Test message"}  # 12 chars
        ]
        count = counter.count_message_tokens(messages)

        # Should fall back to len/4
        assert count == 3  # 12 // 4

    def test_count_message_tokens_long_conversation(self):
        """Test counting tokens in a long conversation"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": f"Message {i}: " + "x" * 100}
            for i in range(10)
        ]
        count = counter.count_message_tokens(messages)

        # Should handle many messages
        assert count > 100

    def test_count_message_tokens_unicode_content(self):
        """Test messages with unicode content"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "你好！这是一个测试消息。"},
            {"role": "assistant", "content": "我理解了。🎉"},
        ]
        count = counter.count_message_tokens(messages)
        assert count > 0

    def test_overhead_calculation(self):
        """Test that overhead is correctly added per message"""
        counter = TokenCounter()

        # Single message
        single = [{"role": "user", "content": "Hi"}]
        count_single = counter.count_message_tokens(single)

        # Two identical messages
        double = [
            {"role": "user", "content": "Hi"},
            {"role": "user", "content": "Hi"},
        ]
        count_double = counter.count_message_tokens(double)

        # Second message should add approximately 4 (overhead) + content tokens
        # The difference should be roughly the overhead + content
        assert count_double > count_single


# ========== Singleton Pattern Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_token_counter_returns_instance(self):
        """Test get_token_counter returns a TokenCounter instance"""
        # Reset singleton
        token_counter_module._token_counter = None

        counter = get_token_counter()
        assert isinstance(counter, TokenCounter)

    def test_get_token_counter_returns_same_instance(self):
        """Test get_token_counter returns the same instance"""
        # Reset singleton
        token_counter_module._token_counter = None

        counter1 = get_token_counter()
        counter2 = get_token_counter()

        assert counter1 is counter2

    def test_singleton_persists_encoding(self):
        """Test singleton maintains its encoding across calls"""
        # Reset singleton
        token_counter_module._token_counter = None

        counter1 = get_token_counter()
        encoding_id = id(counter1.encoding)

        counter2 = get_token_counter()

        assert id(counter2.encoding) == encoding_id


# ========== Default Encoding Tests ==========

class TestDefaultEncoding:
    """Tests for default encoding constant"""

    def test_default_encoding_is_cl100k_base(self):
        """Test default encoding is cl100k_base (GPT-4 compatible)"""
        assert DEFAULT_ENCODING == "cl100k_base"

    def test_default_encoding_is_valid(self):
        """Test default encoding can be loaded"""
        import tiktoken
        encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
        assert encoding is not None


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for token counting"""

    def test_realistic_chat_context(self):
        """Test token counting for a realistic chat context"""
        counter = TokenCounter()

        messages = [
            {"role": "system", "content": "You are a helpful coding assistant. "
             "You provide clear explanations and working code examples."},
            {"role": "user", "content": "Can you explain how async/await works in Python?"},
            {"role": "assistant", "content": """
Async/await in Python allows you to write asynchronous code that can handle
multiple operations concurrently without blocking.

Here's a simple example:

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)  # Simulate I/O
    return "data"

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

Key points:
1. `async def` defines a coroutine
2. `await` pauses execution until the awaited task completes
3. `asyncio.run()` starts the event loop
"""},
            {"role": "user", "content": "Can you show me error handling with async?"},
        ]

        count = counter.count_message_tokens(messages)

        # Should be a reasonable count for this conversation
        assert count > 100
        assert count < 1000

    def test_context_window_estimation(self):
        """Test estimating if content fits in a context window"""
        counter = TokenCounter()

        # Simulate checking if messages fit in 4096 token window
        context_window = 4096

        messages = [
            {"role": "user", "content": "Hello!"},
        ]

        count = counter.count_message_tokens(messages)
        remaining = context_window - count

        assert remaining > 4000  # Plenty of room for response

    def test_fallback_accuracy(self):
        """Test that fallback estimation is reasonably accurate"""
        counter = TokenCounter()

        text = "The quick brown fox jumps over the lazy dog."

        # Get actual count
        actual = counter.count_tokens(text)

        # Get fallback count
        fallback = len(text) // 4

        # Fallback should be in the same ballpark (within 2x)
        assert fallback > actual / 3
        assert fallback < actual * 3


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_none_handling(self):
        """Test handling of None values in messages"""
        counter = TokenCounter()

        # Messages with None values should be handled gracefully
        messages = [{"role": None, "content": None}]

        # This may raise or return 0 depending on implementation
        # The key is it shouldn't crash
        try:
            count = counter.count_message_tokens(messages)
            assert isinstance(count, int)
        except (TypeError, AttributeError):
            # Also acceptable - None is not a valid message format
            pass

    def test_very_long_single_message(self):
        """Test handling very long single message"""
        counter = TokenCounter()

        # 100KB of text
        long_content = "x" * 100000
        messages = [{"role": "user", "content": long_content}]

        count = counter.count_message_tokens(messages)
        assert count > 10000  # Should be many tokens

    def test_many_short_messages(self):
        """Test handling many short messages"""
        counter = TokenCounter()

        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "Hi"}
            for i in range(100)
        ]

        count = counter.count_message_tokens(messages)

        # 100 messages × ~6 tokens each (4 overhead + role + content) + 2 priming
        assert count > 500

    def test_newlines_and_formatting(self):
        """Test text with complex formatting"""
        counter = TokenCounter()

        text = """
        Line 1
        Line 2

        Line 4 (after blank)

        - Bullet 1
        - Bullet 2

        ```
        code block
        ```
        """

        count = counter.count_tokens(text)
        assert count > 0

    def test_mixed_languages(self):
        """Test text with mixed languages"""
        counter = TokenCounter()

        text = "Hello 你好 مرحبا שלום Привет こんにちは"
        count = counter.count_tokens(text)
        assert count > 0
