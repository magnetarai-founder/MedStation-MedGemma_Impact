"""
Comprehensive tests for api/token_counter.py

Tests token counting utilities using tiktoken for LLM context management.

Coverage targets:
- TokenCounter class initialization
- count_tokens: Single text token counting
- count_message_tokens: Chat message token counting with OpenAI overhead
- Fallback behavior when encoding unavailable
- Singleton pattern via get_token_counter
"""

import pytest
from unittest.mock import patch, MagicMock

from api.token_counter import (
    TokenCounter,
    get_token_counter,
    DEFAULT_ENCODING,
)


# ========== Fixtures ==========

@pytest.fixture
def token_counter():
    """Create a fresh TokenCounter instance"""
    return TokenCounter()


@pytest.fixture
def reset_singleton():
    """Reset singleton between tests"""
    import api.token_counter as module
    module._token_counter = None
    yield
    module._token_counter = None


# ========== TokenCounter Initialization Tests ==========

class TestTokenCounterInit:
    """Tests for TokenCounter initialization"""

    def test_default_encoding(self):
        """Test default encoding is cl100k_base"""
        assert DEFAULT_ENCODING == "cl100k_base"

    def test_init_with_default_encoding(self):
        """Test initialization with default encoding"""
        counter = TokenCounter()

        assert counter.encoding is not None

    def test_init_with_custom_encoding(self):
        """Test initialization with custom encoding"""
        counter = TokenCounter(encoding_name="p50k_base")

        assert counter.encoding is not None

    def test_init_with_invalid_encoding(self):
        """Test initialization with invalid encoding falls back to None"""
        counter = TokenCounter(encoding_name="nonexistent_encoding")

        assert counter.encoding is None

    def test_encoding_is_tiktoken_encoding(self, token_counter):
        """Test encoding is a tiktoken Encoding object"""
        import tiktoken

        assert isinstance(token_counter.encoding, tiktoken.Encoding)


# ========== count_tokens Tests ==========

class TestCountTokens:
    """Tests for count_tokens method"""

    def test_simple_text(self, token_counter):
        """Test counting tokens in simple text"""
        result = token_counter.count_tokens("Hello, world!")

        # Should return positive integer
        assert isinstance(result, int)
        assert result > 0

    def test_empty_string(self, token_counter):
        """Test counting tokens in empty string"""
        result = token_counter.count_tokens("")

        assert result == 0

    def test_unicode_text(self, token_counter):
        """Test counting tokens in unicode text"""
        result = token_counter.count_tokens("こんにちは世界")

        assert isinstance(result, int)
        assert result > 0

    def test_long_text(self, token_counter):
        """Test counting tokens in long text"""
        long_text = "The quick brown fox jumps over the lazy dog. " * 100
        result = token_counter.count_tokens(long_text)

        assert result > 0
        # Should be significantly less than character count / 4
        # (actual tokens are more efficient)
        assert result < len(long_text)

    def test_fallback_when_encoding_none(self):
        """Test fallback to len/4 when encoding unavailable"""
        counter = TokenCounter(encoding_name="invalid_encoding")
        assert counter.encoding is None

        result = counter.count_tokens("Hello world")

        # Should use len // 4 fallback (11 // 4 = 2)
        assert result == len("Hello world") // 4

    def test_fallback_on_encoding_error(self):
        """Test fallback when encoding.encode raises error"""
        counter = TokenCounter()

        # Use patch to temporarily mock the encode method
        with patch.object(counter.encoding, 'encode', side_effect=Exception("Encode error")):
            result = counter.count_tokens("Test text")

        # Should fall back to len // 4 (9 // 4 = 2)
        assert result == len("Test text") // 4

    def test_whitespace_text(self, token_counter):
        """Test counting tokens in whitespace"""
        result = token_counter.count_tokens("   \n\t   ")

        assert isinstance(result, int)

    def test_special_characters(self, token_counter):
        """Test counting tokens with special characters"""
        result = token_counter.count_tokens("!@#$%^&*()[]{}|;':\",./<>?")

        assert isinstance(result, int)
        assert result > 0

    def test_code_snippet(self, token_counter):
        """Test counting tokens in code"""
        code = """
def hello_world():
    print("Hello, World!")
    return 42
"""
        result = token_counter.count_tokens(code)

        assert result > 0


# ========== count_message_tokens Tests ==========

class TestCountMessageTokens:
    """Tests for count_message_tokens method"""

    def test_single_message(self, token_counter):
        """Test counting tokens for single message"""
        messages = [
            {"role": "user", "content": "Hello!"}
        ]

        result = token_counter.count_message_tokens(messages)

        # Should include message overhead (4) + role + content + priming (2)
        assert result > 0

    def test_multi_message_conversation(self, token_counter):
        """Test counting tokens for multi-message conversation"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."}
        ]

        result = token_counter.count_message_tokens(messages)

        # Should include overhead for all 3 messages
        assert result > 0

    def test_empty_message_list(self, token_counter):
        """Test counting tokens for empty message list"""
        result = token_counter.count_message_tokens([])

        assert result == 0

    def test_message_with_empty_content(self, token_counter):
        """Test counting tokens for message with empty content"""
        messages = [
            {"role": "user", "content": ""}
        ]

        result = token_counter.count_message_tokens(messages)

        # Should still have overhead (4 + role tokens + 2 priming)
        assert result > 0

    def test_message_missing_content_key(self, token_counter):
        """Test handling message missing content key"""
        messages = [
            {"role": "user"}  # No content key
        ]

        result = token_counter.count_message_tokens(messages)

        # Should handle gracefully
        assert isinstance(result, int)

    def test_message_missing_role_key(self, token_counter):
        """Test handling message missing role key"""
        messages = [
            {"content": "Hello!"}  # No role key
        ]

        result = token_counter.count_message_tokens(messages)

        # Should handle gracefully
        assert isinstance(result, int)

    def test_fallback_when_encoding_none(self):
        """Test fallback for messages when encoding unavailable"""
        counter = TokenCounter(encoding_name="invalid_encoding")
        assert counter.encoding is None

        messages = [
            {"role": "user", "content": "Hello world!"}  # 12 chars
        ]

        result = counter.count_message_tokens(messages)

        # Should use len // 4 fallback (12 // 4 = 3)
        assert result == len("Hello world!") // 4

    def test_fallback_on_encoding_error(self):
        """Test fallback when encoding.encode raises error"""
        counter = TokenCounter()

        # Use patch to temporarily mock the encode method
        with patch.object(counter.encoding, 'encode', side_effect=Exception("Encode error")):
            messages = [
                {"role": "user", "content": "Test message"}  # 12 chars
            ]
            result = counter.count_message_tokens(messages)

        # Should fall back to len // 4
        assert result == len("Test message") // 4

    def test_message_overhead_calculation(self, token_counter):
        """Test message overhead is applied correctly"""
        # Single short message
        messages1 = [{"role": "user", "content": "Hi"}]
        result1 = token_counter.count_message_tokens(messages1)

        # Two short messages
        messages2 = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hi"}
        ]
        result2 = token_counter.count_message_tokens(messages2)

        # Second result should be roughly double (with overhead)
        # Each message adds 4 tokens overhead
        assert result2 > result1

    def test_unicode_in_messages(self, token_counter):
        """Test counting tokens with unicode in messages"""
        messages = [
            {"role": "user", "content": "日本語でお願いします"}
        ]

        result = token_counter.count_message_tokens(messages)

        assert result > 0

    def test_long_conversation(self, token_counter):
        """Test counting tokens for long conversation"""
        messages = []
        for i in range(50):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Response {i}"})

        result = token_counter.count_message_tokens(messages)

        # Should be substantial
        assert result > 100


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_token_counter_returns_instance(self, reset_singleton):
        """Test get_token_counter returns TokenCounter instance"""
        result = get_token_counter()

        assert isinstance(result, TokenCounter)

    def test_get_token_counter_returns_same_instance(self, reset_singleton):
        """Test get_token_counter returns same instance on multiple calls"""
        counter1 = get_token_counter()
        counter2 = get_token_counter()

        assert counter1 is counter2

    def test_singleton_encoding_persists(self, reset_singleton):
        """Test encoding persists across singleton calls"""
        counter1 = get_token_counter()
        encoding1 = counter1.encoding

        counter2 = get_token_counter()
        encoding2 = counter2.encoding

        assert encoding1 is encoding2


# ========== Default Encoding Tests ==========

class TestDefaultEncoding:
    """Tests for default encoding behavior"""

    def test_default_encoding_is_cl100k_base(self):
        """Test default encoding constant"""
        assert DEFAULT_ENCODING == "cl100k_base"

    def test_counter_uses_default_encoding(self, token_counter):
        """Test counter uses default encoding when not specified"""
        # cl100k_base is the GPT-4 encoding
        # Should encode "hello" to specific tokens
        result = token_counter.count_tokens("hello")

        assert result > 0


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_realistic_chat_context_estimation(self, token_counter):
        """Test realistic chat context token counting"""
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Can you explain what machine learning is?"},
            {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed."},
            {"role": "user", "content": "Can you give me an example?"},
        ]

        result = token_counter.count_message_tokens(messages)

        # Should be a reasonable count for this conversation
        assert 50 < result < 200

    def test_context_window_fitting(self, token_counter):
        """Test checking if messages fit in context window"""
        max_tokens = 4096  # Example context window

        messages = [
            {"role": "user", "content": "Hello!"}
        ]

        token_count = token_counter.count_message_tokens(messages)

        assert token_count < max_tokens

    def test_fallback_accuracy(self):
        """Test fallback estimation is reasonably accurate"""
        # When encoding fails, use len // 4
        counter = TokenCounter(encoding_name="invalid")

        # Test with known text
        text = "This is a test sentence with multiple words."  # 46 chars
        result = counter.count_tokens(text)

        # Should be len // 4 = 11
        assert result == 46 // 4


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_very_long_message(self, token_counter):
        """Test very long message handling"""
        long_content = "x" * 100000
        messages = [{"role": "user", "content": long_content}]

        result = token_counter.count_message_tokens(messages)

        assert result > 0

    def test_many_short_messages(self, token_counter):
        """Test many short messages"""
        messages = [{"role": "user", "content": "Hi"} for _ in range(100)]

        result = token_counter.count_message_tokens(messages)

        # Should account for overhead of each message
        assert result > 100  # At least overhead per message

    def test_complex_unicode(self, token_counter):
        """Test complex unicode including emojis"""
        text = "Hello 👋 World 🌍! こんにちは 🇯🇵 مرحبا 🇸🇦"
        result = token_counter.count_tokens(text)

        assert result > 0

    def test_mixed_language_messages(self, token_counter):
        """Test messages with mixed languages"""
        messages = [
            {"role": "user", "content": "Hello, 你好, Bonjour, Hola!"},
            {"role": "assistant", "content": "こんにちは! I can help in multiple languages."}
        ]

        result = token_counter.count_message_tokens(messages)

        assert result > 0

    def test_newlines_and_formatting(self, token_counter):
        """Test text with newlines and formatting"""
        text = """
        This is a multi-line
        text with various
        formatting and    spaces.

        And blank lines too.
        """

        result = token_counter.count_tokens(text)

        assert result > 0

    def test_json_in_content(self, token_counter):
        """Test JSON content in messages"""
        messages = [
            {"role": "user", "content": '{"key": "value", "number": 42, "array": [1, 2, 3]}'}
        ]

        result = token_counter.count_message_tokens(messages)

        assert result > 0

    def test_code_in_messages(self, token_counter):
        """Test code snippets in messages"""
        messages = [
            {"role": "user", "content": "```python\ndef hello():\n    print('Hello')\n```"}
        ]

        result = token_counter.count_message_tokens(messages)

        assert result > 0
