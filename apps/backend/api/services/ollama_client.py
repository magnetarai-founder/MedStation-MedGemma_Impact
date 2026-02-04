#!/usr/bin/env python3
"""
Ollama Client for Agent System

Provides a reusable client for interacting with Ollama LLM with circuit breaker protection
"""

import logging
import os

# Import configuration constants
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_MODEL, DEFAULT_TEMPERATURE, OLLAMA_CONNECT_TIMEOUT, OLLAMA_TIMEOUT
from utils.circuit_breaker import get_circuit_breaker
from utils.retry import retry

logger = logging.getLogger(__name__)

# Initialize circuit breaker for Ollama
ollama_circuit_breaker = get_circuit_breaker(
    name="ollama",
    failure_threshold=3,  # Open after 3 failures
    success_threshold=2,  # Close after 2 successes
    timeout=30,  # Try recovery after 30 seconds
    expected_exception=Exception,
)


class OllamaClient:
    """Client for Ollama HTTP API"""

    def __init__(self, base_url: str | None = None, default_model: str | None = None):
        # Get URL from parameter or environment
        url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # SECURITY: Validate URL to prevent SSRF attacks
        from api.utils.path_security import validate_ollama_url

        try:
            self.base_url = validate_ollama_url(url)
        except ValueError as e:
            logger.error(f"Invalid Ollama URL rejected: {e}")
            raise ValueError(f"Invalid Ollama configuration: {e}")

        self.default_model = default_model or DEFAULT_MODEL
        self.timeout = httpx.Timeout(float(OLLAMA_TIMEOUT), connect=float(OLLAMA_CONNECT_TIMEOUT))

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        format: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat request to Ollama (non-streaming)

        Protected by circuit breaker to prevent cascading failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            format: Response format ('json' for JSON mode)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response dict with 'message' and metadata
        """

        @retry(
            max_attempts=3, initial_delay=1.0, retry_on=(httpx.ConnectError, httpx.TimeoutException)
        )
        @ollama_circuit_breaker.call()
        async def _chat_request():
            url = f"{self.base_url}/api/chat"

            payload = {
                "model": model or self.default_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature if temperature is not None else DEFAULT_TEMPERATURE,
                },
            }

            if format == "json":
                payload["format"] = "json"

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()

            except httpx.ConnectError:
                logger.error(f"Cannot connect to Ollama at {self.base_url}")
                raise Exception(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
            except httpx.TimeoutException:
                logger.error("Request to Ollama timed out")
                raise Exception("Request to Ollama timed out")
            except Exception as e:
                logger.error(f"Ollama request failed: {e}")
                raise

        return await _chat_request()

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        format: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a completion from a prompt (non-streaming)

        Protected by circuit breaker to prevent cascading failures.

        Args:
            prompt: Input prompt
            model: Model to use
            format: Response format ('json' for JSON mode)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """

        @retry(
            max_attempts=3, initial_delay=1.0, retry_on=(httpx.ConnectError, httpx.TimeoutException)
        )
        @ollama_circuit_breaker.call()
        async def _generate_request():
            url = f"{self.base_url}/api/generate"

            payload = {
                "model": model or self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            if format == "json":
                payload["format"] = "json"

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data.get("response", "")

            except Exception as e:
                logger.error(f"Ollama generate failed: {e}")
                raise

        return await _generate_request()

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List available models

        Protected by circuit breaker. Returns empty list as fallback.
        """

        @ollama_circuit_breaker.call(fallback=lambda: [])
        async def _list_models_request():
            url = f"{self.base_url}/api/tags"

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    return data.get("models", [])

            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                raise

        return await _list_models_request()


# Global instance
_ollama_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
