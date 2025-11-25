"""
Ollama Client - Streaming interface for Ollama API.

Handles:
- Model listing
- Model preloading
- Streaming chat responses
- Size formatting
- Server health checking and auto-start
"""

import json
import logging
import subprocess
import asyncio
from typing import List, Dict, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class OllamaModel:
    """Ollama model metadata"""
    def __init__(self, name: str, size: str, modified_at: str):
        self.name = name
        self.size = size
        self.modified_at = modified_at

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "size": self.size,
            "modified_at": self.modified_at
        }


class OllamaClient:
    """Client for Ollama API"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._server_process: Optional[subprocess.Popen] = None

    async def check_server(self) -> bool:
        """Check if Ollama server is running"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/version")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama server not responding: {e}")
            return False

    async def start_server(self) -> bool:
        """Start Ollama server if not running"""
        try:
            # Check if already running
            if await self.check_server():
                logger.info("Ollama server already running")
                return True

            logger.info("Starting Ollama server...")

            # Try to start Ollama serve in background
            self._server_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Wait a few seconds for server to start
            await asyncio.sleep(3)

            # Check if it started successfully
            if await self.check_server():
                logger.info("✓ Ollama server started successfully")
                return True
            else:
                logger.error("Failed to start Ollama server")
                return False

        except FileNotFoundError:
            logger.error("Ollama command not found. Please install Ollama from https://ollama.ai")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama server: {e}")
            return False

    async def list_models(self) -> List[Dict]:
        """List available models"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    models.append({
                        "name": model_data["name"],
                        "size": self._format_size(model_data.get("size", 0)),
                        "modified_at": model_data.get("modified_at", "")
                    })

                logger.info(f"Successfully fetched {len(models)} models from Ollama")
                return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}. Make sure Ollama is running with 'ollama serve'")
            return []

    async def preload_model(self, model: str, keep_alive: str = "1h") -> bool:
        """
        Pre-load a model into memory for instant responses

        Args:
            model: Model name to load
            keep_alive: How long to keep model in memory (e.g., "1h", "30m", "5m")

        Returns:
            True if successful, False otherwise
        """
        try:
            import httpx

            payload = {
                "model": model,
                "prompt": "",  # Empty prompt to just load the model
                "stream": False,
                "keep_alive": keep_alive
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                logger.info(f"✓ Pre-loaded model '{model}' (keep_alive: {keep_alive})")
                return True

        except Exception as e:
            logger.error(f"Failed to pre-load model '{model}': {e}")
            return False

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1
    ) -> AsyncGenerator[str, None]:
        """Send chat request to Ollama with streaming and custom parameters"""
        try:
            import httpx

            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k,
                    "repeat_penalty": repeat_penalty
                }
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.strip():
                            chunk = json.loads(line)

                            # Yield content if present
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    yield content

                            # Check if done
                            if chunk.get("done"):
                                break

        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format size in bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"
