"""
llama.cpp Inference Service

Provides chat completion via the llama.cpp server's OpenAI-compatible API.
Supports streaming responses.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass

from .config import get_llamacpp_config, LlamaCppConfig
from .server import get_llamacpp_server

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A chat message"""
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatCompletionChunk:
    """A streaming chunk from chat completion"""
    content: str
    finish_reason: Optional[str] = None  # "stop", "length", None
    model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "finish_reason": self.finish_reason,
            "model": self.model,
        }


@dataclass
class ChatCompletion:
    """Non-streaming chat completion response"""
    content: str
    finish_reason: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "finish_reason": self.finish_reason,
            "model": self.model,
            "usage": self.usage,
        }


class LlamaCppInference:
    """
    Chat inference via llama.cpp server

    Uses the OpenAI-compatible API endpoint provided by llama.cpp server.
    Supports both streaming and non-streaming completions.
    """

    def __init__(self, config: Optional[LlamaCppConfig] = None):
        self.config = config or get_llamacpp_config()

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        stream: bool = True
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Generate chat completion with streaming

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            repeat_penalty: Repetition penalty
            stream: Whether to stream (default True)

        Yields:
            ChatCompletionChunk objects as response streams in
        """
        import httpx

        # Build request body (OpenAI-compatible format)
        body = {
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": top_p or self.config.top_p,
            "stream": stream,
        }

        # Optional parameters
        if top_k is not None:
            body["top_k"] = top_k
        if repeat_penalty is not None:
            body["repeat_penalty"] = repeat_penalty

        logger.debug(f"Chat request: {len(messages)} messages, stream={stream}")

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as client:
                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        self.config.completion_url,
                        json=body,
                        headers={"Accept": "text/event-stream"}
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            raise RuntimeError(f"Server error {response.status_code}: {error_text.decode()}")

                        async for line in response.aiter_lines():
                            if not line or line.startswith(":"):
                                continue

                            if line.startswith("data: "):
                                data = line[6:]  # Remove "data: " prefix

                                if data == "[DONE]":
                                    yield ChatCompletionChunk(
                                        content="",
                                        finish_reason="stop"
                                    )
                                    return

                                try:
                                    chunk = json.loads(data)
                                    choices = chunk.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        finish_reason = choices[0].get("finish_reason")

                                        if content or finish_reason:
                                            yield ChatCompletionChunk(
                                                content=content,
                                                finish_reason=finish_reason,
                                                model=chunk.get("model")
                                            )
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse SSE chunk: {e}")
                                    continue

                else:
                    # Non-streaming request
                    response = await client.post(
                        self.config.completion_url,
                        json=body
                    )

                    if response.status_code != 200:
                        raise RuntimeError(f"Server error {response.status_code}: {response.text}")

                    result = response.json()
                    choices = result.get("choices", [])

                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        finish_reason = choices[0].get("finish_reason", "stop")

                        yield ChatCompletionChunk(
                            content=content,
                            finish_reason=finish_reason,
                            model=result.get("model")
                        )

        except httpx.ConnectError:
            raise RuntimeError("Cannot connect to llama.cpp server. Is it running?")
        except httpx.TimeoutException:
            raise RuntimeError("Request to llama.cpp server timed out")
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise

    async def chat_sync(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Generate chat completion without streaming

        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters

        Returns:
            ChatCompletion with full response
        """
        import httpx

        body = {
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": False,
            **kwargs
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout_seconds, connect=10.0)) as client:
            response = await client.post(
                self.config.completion_url,
                json=body
            )

            if response.status_code != 200:
                raise RuntimeError(f"Server error {response.status_code}: {response.text}")

            result = response.json()
            choices = result.get("choices", [])

            if not choices:
                raise RuntimeError("No choices in response")

            choice = choices[0]
            message = choice.get("message", {})
            usage = result.get("usage", {})

            return ChatCompletion(
                content=message.get("content", ""),
                finish_reason=choice.get("finish_reason", "stop"),
                model=result.get("model", "unknown"),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            )

    async def is_available(self) -> bool:
        """Check if the inference endpoint is available"""
        server = get_llamacpp_server()
        status = await server.get_status()
        return status.running and status.health_ok


# Singleton instance
_inference_instance: Optional[LlamaCppInference] = None


def get_llamacpp_inference() -> LlamaCppInference:
    """Get the singleton inference instance"""
    global _inference_instance
    if _inference_instance is None:
        _inference_instance = LlamaCppInference()
    return _inference_instance


__all__ = [
    "LlamaCppInference",
    "ChatMessage",
    "ChatCompletionChunk",
    "ChatCompletion",
    "get_llamacpp_inference",
]
