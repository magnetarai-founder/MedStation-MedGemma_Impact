"""
Continue Autocomplete Integration

Provides fast autocomplete suggestions using local models.
Optimized for low-latency inline completions.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from .bridge import AutocompleteRequest, AutocompleteResult

logger = logging.getLogger(__name__)


@dataclass
class AutocompleteConfig:
    """Configuration for autocomplete service"""

    # Model settings
    model: str = "qwen2.5-coder:1.5b"  # Small, fast model
    api_base: str = "http://localhost:11434"

    # Completion settings
    max_tokens: int = 64
    temperature: float = 0.2
    stop_tokens: list[str] | None = None

    # Performance settings
    timeout_ms: int = 500  # Aggressive timeout for responsiveness
    debounce_ms: int = 100  # Debounce rapid requests

    # Context settings
    max_prefix_lines: int = 50
    max_suffix_lines: int = 10


class AutocompleteService:
    """
    Fast autocomplete using local LLMs.

    Features:
    - Low-latency completions via Ollama
    - FIM (Fill-in-the-Middle) support
    - Debouncing for rapid typing
    - Caching for repeated contexts
    """

    def __init__(self, config: AutocompleteConfig | None = None):
        """
        Initialize autocomplete service.

        Args:
            config: Autocomplete configuration
        """
        self._config = config or AutocompleteConfig()
        self._cache: dict[str, list[AutocompleteResult]] = {}
        self._cache_max_size = 100
        self._last_request_time = 0.0
        self._pending_request: asyncio.Task | None = None

    async def get_completions(
        self,
        request: AutocompleteRequest,
    ) -> list[AutocompleteResult]:
        """
        Get autocomplete suggestions.

        Args:
            request: Autocomplete request with context

        Returns:
            List of completion suggestions
        """
        start_time = time.time()

        # Check cache
        cache_key = self._make_cache_key(request)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Debounce rapid requests
        current_time = time.time() * 1000
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._config.debounce_ms:
            await asyncio.sleep((self._config.debounce_ms - time_since_last) / 1000)
        self._last_request_time = time.time() * 1000

        try:
            # Build prompt for FIM
            prompt = self._build_fim_prompt(request)

            # Get completion from model
            completion_text = await self._get_model_completion(prompt)

            if not completion_text:
                return []

            # Parse and clean completion
            results = self._parse_completion(
                completion_text,
                request,
                int((time.time() - start_time) * 1000),
            )

            # Cache results
            self._update_cache(cache_key, results)

            return results

        except asyncio.TimeoutError:
            logger.debug("Autocomplete timeout")
            return []
        except Exception as e:
            logger.warning(f"Autocomplete error: {e}")
            return []

    def _build_fim_prompt(self, request: AutocompleteRequest) -> str:
        """
        Build Fill-in-the-Middle prompt.

        FIM format: <prefix><fim_middle><suffix>
        """
        # Trim context to configured limits
        prefix_lines = request.prefix.split("\n")
        suffix_lines = request.suffix.split("\n")

        prefix = "\n".join(prefix_lines[-self._config.max_prefix_lines:])
        suffix = "\n".join(suffix_lines[:self._config.max_suffix_lines])

        # Use standard FIM tokens (model-specific, but most support these)
        fim_prefix = "<fim_prefix>"
        fim_middle = "<fim_middle>"
        fim_suffix = "<fim_suffix>"

        # Build prompt
        prompt = f"{fim_prefix}{prefix}{fim_suffix}{suffix}{fim_middle}"

        return prompt

    async def _get_model_completion(self, prompt: str) -> str:
        """
        Get completion from Ollama.

        Uses HTTP API for low-latency inference.
        """
        import aiohttp

        url = f"{self._config.api_base}/api/generate"

        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self._config.max_tokens,
                "temperature": self._config.temperature,
                "stop": self._config.stop_tokens or ["\n\n", "```", "<fim_"],
            },
        }

        timeout = aiohttp.ClientTimeout(
            total=self._config.timeout_ms / 1000
        )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        logger.warning(f"Ollama returned {response.status}")
                        return ""
        except aiohttp.ClientError as e:
            logger.debug(f"Ollama connection error: {e}")
            return ""

    def _parse_completion(
        self,
        completion: str,
        request: AutocompleteRequest,
        latency_ms: int,
    ) -> list[AutocompleteResult]:
        """
        Parse and clean model completion.

        Handles multi-line completions and extracts usable suggestions.
        """
        results: list[AutocompleteResult] = []

        # Clean up completion
        completion = completion.strip()

        # Remove FIM tokens if present
        for token in ["<fim_prefix>", "<fim_suffix>", "<fim_middle>", "</fim>"]:
            completion = completion.replace(token, "")

        if not completion:
            return results

        # Split into lines for multi-line completions
        lines = completion.split("\n")

        # Primary completion: first meaningful line
        primary = lines[0].rstrip()
        if primary:
            results.append(AutocompleteResult(
                text=primary,
                display_text=primary[:50] + "..." if len(primary) > 50 else primary,
                range_start_line=request.cursor_line,
                range_start_col=request.cursor_column,
                range_end_line=request.cursor_line,
                range_end_col=request.cursor_column,
                confidence=0.9,
                model=self._config.model,
                latency_ms=latency_ms,
            ))

        # Multi-line completion if available
        if len(lines) > 1:
            full_completion = "\n".join(lines[:5])  # Limit to 5 lines
            if full_completion != primary:
                results.append(AutocompleteResult(
                    text=full_completion,
                    display_text=f"{primary[:30]}... ({len(lines)} lines)",
                    range_start_line=request.cursor_line,
                    range_start_col=request.cursor_column,
                    range_end_line=request.cursor_line + len(lines) - 1,
                    range_end_col=len(lines[-1]),
                    confidence=0.7,
                    model=self._config.model,
                    latency_ms=latency_ms,
                ))

        return results

    def _make_cache_key(self, request: AutocompleteRequest) -> str:
        """Create cache key from request"""
        # Use last N chars of prefix + first N chars of suffix
        prefix_key = request.prefix[-100:] if len(request.prefix) > 100 else request.prefix
        suffix_key = request.suffix[:50] if len(request.suffix) > 50 else request.suffix
        return f"{prefix_key}|||{suffix_key}"

    def _update_cache(
        self, key: str, results: list[AutocompleteResult]
    ) -> None:
        """Update cache with new results"""
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entries (simple LRU approximation)
            keys_to_remove = list(self._cache.keys())[:self._cache_max_size // 4]
            for k in keys_to_remove:
                del self._cache[k]

        self._cache[key] = results

    def clear_cache(self) -> None:
        """Clear the completion cache"""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics"""
        return {
            "model": self._config.model,
            "cache_size": len(self._cache),
            "cache_max": self._cache_max_size,
            "timeout_ms": self._config.timeout_ms,
        }


class SmartAutocompleteService(AutocompleteService):
    """
    Enhanced autocomplete with context awareness.

    Features:
    - Language-specific completions
    - Import/symbol awareness
    - Bracket/quote matching
    """

    def __init__(self, config: AutocompleteConfig | None = None):
        super().__init__(config)
        self._language_configs = self._init_language_configs()

    def _init_language_configs(self) -> dict[str, dict[str, Any]]:
        """Initialize language-specific configurations"""
        return {
            "python": {
                "stop_tokens": ["\n\n", "def ", "class ", "import ", "from "],
                "indent_triggers": [":", "(", "[", "{"],
            },
            "typescript": {
                "stop_tokens": ["\n\n", "function ", "class ", "interface ", "import "],
                "indent_triggers": ["{", "(", "[", "=>"],
            },
            "javascript": {
                "stop_tokens": ["\n\n", "function ", "class ", "import "],
                "indent_triggers": ["{", "(", "[", "=>"],
            },
            "go": {
                "stop_tokens": ["\n\n", "func ", "type ", "import "],
                "indent_triggers": ["{", "("],
            },
            "rust": {
                "stop_tokens": ["\n\n", "fn ", "struct ", "impl ", "use "],
                "indent_triggers": ["{", "(", "["],
            },
        }

    async def get_completions(
        self,
        request: AutocompleteRequest,
    ) -> list[AutocompleteResult]:
        """Get language-aware completions"""
        # Apply language-specific stop tokens
        if request.language and request.language in self._language_configs:
            lang_config = self._language_configs[request.language]
            original_stops = self._config.stop_tokens
            self._config.stop_tokens = lang_config.get("stop_tokens", original_stops)

        # Check for simple completions we can handle without LLM
        simple_result = self._try_simple_completion(request)
        if simple_result:
            return simple_result

        # Fall back to LLM completion
        return await super().get_completions(request)

    def _try_simple_completion(
        self,
        request: AutocompleteRequest,
    ) -> list[AutocompleteResult] | None:
        """
        Try to provide simple completions without LLM.

        Handles bracket matching, quote completion, etc.
        """
        prefix = request.prefix
        if not prefix:
            return None

        last_char = prefix[-1] if prefix else ""
        completions: list[str] = []

        # Bracket completion
        bracket_pairs = {
            "(": ")",
            "[": "]",
            "{": "}",
            "<": ">",
        }

        if last_char in bracket_pairs:
            # Check if closing bracket is needed
            open_count = prefix.count(last_char)
            close_count = prefix.count(bracket_pairs[last_char])
            if open_count > close_count:
                completions.append(bracket_pairs[last_char])

        # Quote completion
        quote_chars = ["'", '"', "`"]
        if last_char in quote_chars:
            quote_count = prefix.count(last_char)
            if quote_count % 2 == 1:  # Odd number means unclosed
                completions.append(last_char)

        if completions:
            return [
                AutocompleteResult(
                    text=c,
                    display_text=c,
                    range_start_line=request.cursor_line,
                    range_start_col=request.cursor_column,
                    range_end_line=request.cursor_line,
                    range_end_col=request.cursor_column,
                    confidence=1.0,
                    model="simple",
                    latency_ms=0,
                )
                for c in completions
            ]

        return None


def create_autocomplete_service(
    model: str = "qwen2.5-coder:1.5b",
    api_base: str = "http://localhost:11434",
    smart: bool = True,
) -> AutocompleteService:
    """
    Create configured autocomplete service.

    Args:
        model: Model to use for completions
        api_base: Ollama API base URL
        smart: Whether to use smart (language-aware) completions

    Returns:
        Configured autocomplete service
    """
    config = AutocompleteConfig(
        model=model,
        api_base=api_base,
    )

    if smart:
        return SmartAutocompleteService(config)
    else:
        return AutocompleteService(config)
