"""
Message Building Utilities

Provides utilities for building chat messages and conversation events.
Eliminates duplication across chat, agent, and memory APIs.

Usage:
    from api.utils.message_builder import MessageBuilder

    # Build a chat message
    message = MessageBuilder.chat_message("user", "Hello!")

    # Build a conversation event
    event = MessageBuilder.conversation_event("assistant", "Hi there!", model="qwen2.5-coder:3b")

    # Build system context message
    context_msg = MessageBuilder.context_message("Here is the workspace context...")
"""

from datetime import datetime
from typing import Any


class MessageBuilder:
    """
    Builder class for creating standardized messages and events.

    Provides consistent message creation across the application.
    """

    @staticmethod
    def chat_message(
        role: str,
        content: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Build a chat message dict (Ollama format).

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            **kwargs: Additional fields

        Returns:
            Dict compatible with Ollama chat API

        Example:
            >>> msg = MessageBuilder.chat_message("user", "Hello!")
            >>> msg
            {'role': 'user', 'content': 'Hello!'}
        """
        message = {
            "role": role,
            "content": content,
        }

        # Add any additional fields
        message.update(kwargs)

        return message

    @staticmethod
    def conversation_event(
        role: str,
        content: str,
        model: str | None = None,
        tokens: int | None = None,
        files: list[str] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a conversation event for storage.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            model: Model used (for assistant messages)
            tokens: Token count
            files: Associated files
            timestamp: ISO timestamp (generated if None)

        Returns:
            Dict compatible with ConversationEvent

        Example:
            >>> event = MessageBuilder.conversation_event(
            ...     "assistant",
            ...     "Response text",
            ...     model="qwen2.5-coder:3b",
            ...     tokens=150
            ... )
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        event = {
            "timestamp": timestamp,
            "role": role,
            "content": content,
        }

        if model:
            event["model"] = model

        if tokens:
            event["tokens"] = tokens

        if files:
            event["files"] = files

        return event

    @staticmethod
    def system_message(content: str) -> dict[str, Any]:
        """
        Build a system message.

        Args:
            content: System message content

        Returns:
            System message dict

        Example:
            >>> msg = MessageBuilder.system_message("You are a helpful assistant")
        """
        return MessageBuilder.chat_message("system", content)

    @staticmethod
    def user_message(content: str) -> dict[str, Any]:
        """
        Build a user message.

        Args:
            content: User message content

        Returns:
            User message dict
        """
        return MessageBuilder.chat_message("user", content)

    @staticmethod
    def assistant_message(content: str, model: str | None = None) -> dict[str, Any]:
        """
        Build an assistant message.

        Args:
            content: Assistant message content
            model: Model used

        Returns:
            Assistant message dict
        """
        message = MessageBuilder.chat_message("assistant", content)
        if model:
            message["model"] = model
        return message

    @staticmethod
    def context_message(
        context: str,
        prefix: str = "Here is the relevant context from the workspace:",
        suffix: str = "Use this context to answer the user's question.",
    ) -> dict[str, Any]:
        """
        Build a context injection system message.

        Args:
            context: Context content to inject
            prefix: Prefix text
            suffix: Suffix text

        Returns:
            System message with context

        Example:
            >>> msg = MessageBuilder.context_message("File contents: ...")
        """
        content = f"{prefix}\n\n{context}\n\n{suffix}"
        return MessageBuilder.system_message(content)

    @staticmethod
    def error_message(error: str, details: str | None = None) -> dict[str, Any]:
        """
        Build an error message for display.

        Args:
            error: Error message
            details: Additional error details

        Returns:
            System message with error

        Example:
            >>> msg = MessageBuilder.error_message("API rate limit exceeded")
        """
        content = f"Error: {error}"
        if details:
            content += f"\n\nDetails: {details}"

        return MessageBuilder.system_message(content)

    @staticmethod
    def combine_messages(
        messages: list[dict[str, Any]],
        context: str | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Combine messages with optional context and system prompt.

        Args:
            messages: Existing messages
            context: Context to inject (added as system message)
            system_prompt: System prompt (added at start)

        Returns:
            Combined message list

        Example:
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> combined = MessageBuilder.combine_messages(
            ...     messages,
            ...     context="File: main.py",
            ...     system_prompt="You are a code expert"
            ... )
        """
        result = []

        # Add system prompt first
        if system_prompt:
            result.append(MessageBuilder.system_message(system_prompt))

        # Add context injection
        if context:
            result.append(MessageBuilder.context_message(context))

        # Add original messages
        result.extend(messages)

        return result

    @staticmethod
    def format_tool_result(
        tool_name: str,
        result: Any,
        success: bool = True,
        error: str | None = None,
    ) -> dict[str, Any]:
        """
        Format tool execution result as a message.

        Args:
            tool_name: Name of tool that was executed
            result: Tool result
            success: Whether execution succeeded
            error: Error message if failed

        Returns:
            System message with tool result

        Example:
            >>> msg = MessageBuilder.format_tool_result(
            ...     "read_file",
            ...     {"content": "file contents..."},
            ...     success=True
            ... )
        """
        if success:
            content = f"Tool '{tool_name}' executed successfully.\n\nResult: {result}"
        else:
            content = f"Tool '{tool_name}' failed.\n\nError: {error}"

        return MessageBuilder.system_message(content)

    @staticmethod
    def build_conversation_summary(
        messages: list[dict[str, Any]],
        max_length: int = 500,
    ) -> str:
        """
        Build a conversation summary from messages.

        Args:
            messages: List of messages
            max_length: Maximum summary length

        Returns:
            Summary string

        Example:
            >>> messages = [
            ...     {"role": "user", "content": "What is Python?"},
            ...     {"role": "assistant", "content": "Python is a programming language..."}
            ... ]
            >>> summary = MessageBuilder.build_conversation_summary(messages)
        """
        parts = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Truncate long messages
            if len(content) > 100:
                content = content[:97] + "..."

            parts.append(f"{role.capitalize()}: {content}")

        summary = " | ".join(parts)

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."

        return summary
