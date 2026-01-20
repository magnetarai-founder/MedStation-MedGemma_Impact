"""
llama.cpp Server Lifecycle Manager

Manages starting, stopping, and monitoring the llama.cpp server process.
Includes health checking and auto-restart capabilities.
"""

import asyncio
import logging
import subprocess
import signal
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from .config import get_llamacpp_config, LlamaCppConfig

logger = logging.getLogger(__name__)


@dataclass
class ServerStatus:
    """Server status information"""
    running: bool
    model_loaded: Optional[str] = None
    model_path: Optional[str] = None
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    health_ok: bool = False
    port: int = 8080
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "health_ok": self.health_ok,
            "port": self.port,
            "error": self.error,
        }


class LlamaCppServer:
    """
    Manages llama.cpp server process

    Features:
    - Start server with specific GGUF model
    - Health monitoring
    - Graceful shutdown
    - Process management
    """

    def __init__(self, config: Optional[LlamaCppConfig] = None):
        self.config = config or get_llamacpp_config()
        self._process: Optional[subprocess.Popen] = None
        self._current_model: Optional[str] = None
        self._current_model_path: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        """Check if server process is running"""
        if self._process is None:
            return False
        return self._process.poll() is None

    async def get_status(self) -> ServerStatus:
        """Get current server status with health check"""
        if not self.is_running:
            return ServerStatus(running=False, port=self.config.port)

        # Perform health check
        health_ok = await self._health_check()

        return ServerStatus(
            running=True,
            model_loaded=self._current_model,
            model_path=self._current_model_path,
            pid=self._process.pid if self._process else None,
            started_at=self._started_at,
            health_ok=health_ok,
            port=self.config.port,
        )

    async def _health_check(self) -> bool:
        """Check if server is responding to health endpoint"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.config.health_url)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def start(
        self,
        model_path: str,
        model_name: Optional[str] = None,
        wait_ready: bool = True,
        timeout: int = 120
    ) -> ServerStatus:
        """
        Start llama.cpp server with a specific model

        Args:
            model_path: Path to the GGUF model file
            model_name: Optional friendly name for the model
            wait_ready: Wait for server to be ready before returning
            timeout: Maximum seconds to wait for server startup

        Returns:
            ServerStatus with startup result
        """
        async with self._lock:
            # Stop existing server if running
            if self.is_running:
                logger.info("Stopping existing llama.cpp server...")
                await self._stop_internal()

            # Validate model path
            model_file = Path(model_path)
            if not model_file.exists():
                return ServerStatus(
                    running=False,
                    error=f"Model file not found: {model_path}",
                    port=self.config.port
                )

            # Validate llama.cpp binary
            if not self.config.llama_cpp_path:
                return ServerStatus(
                    running=False,
                    error="llama-server binary not found. Install via: brew install llama.cpp",
                    port=self.config.port
                )

            # Build command
            cmd = [self.config.llama_cpp_path] + self.config.get_server_args(model_path)
            logger.info(f"Starting llama.cpp: {' '.join(cmd)}")

            try:
                # Start server process
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,  # Detach from parent
                )

                self._current_model = model_name or model_file.stem
                self._current_model_path = model_path
                self._started_at = datetime.utcnow()

                logger.info(f"Started llama.cpp server (PID: {self._process.pid})")

                # Wait for server to be ready
                if wait_ready:
                    ready = await self._wait_for_ready(timeout)
                    if not ready:
                        # Server didn't become ready, try to get error output
                        error_msg = "Server failed to start within timeout"
                        if self._process.poll() is not None:
                            _, stderr = self._process.communicate(timeout=1)
                            if stderr:
                                error_msg = stderr.decode("utf-8", errors="ignore")[:500]

                        await self._stop_internal()
                        return ServerStatus(
                            running=False,
                            error=error_msg,
                            port=self.config.port
                        )

                return await self.get_status()

            except FileNotFoundError:
                return ServerStatus(
                    running=False,
                    error=f"llama-server binary not found at: {self.config.llama_cpp_path}",
                    port=self.config.port
                )
            except Exception as e:
                logger.error(f"Failed to start llama.cpp: {e}")
                return ServerStatus(
                    running=False,
                    error=str(e),
                    port=self.config.port
                )

    async def _wait_for_ready(self, timeout: int) -> bool:
        """Wait for server to be ready"""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if not self.is_running:
                logger.warning("Server process died during startup")
                return False

            if await self._health_check():
                logger.info("llama.cpp server is ready")
                return True

            await asyncio.sleep(1)

        return False

    async def stop(self) -> ServerStatus:
        """Stop the llama.cpp server"""
        async with self._lock:
            return await self._stop_internal()

    async def _stop_internal(self) -> ServerStatus:
        """Internal stop without lock"""
        if not self.is_running:
            return ServerStatus(running=False, port=self.config.port)

        logger.info("Stopping llama.cpp server...")

        try:
            # Try graceful shutdown first
            self._process.terminate()

            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if not responding
                logger.warning("Server not responding, force killing...")
                self._process.kill()
                self._process.wait(timeout=5)

            logger.info("llama.cpp server stopped")

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            # Try to force kill
            try:
                self._process.kill()
            except Exception:
                pass

        finally:
            self._process = None
            self._current_model = None
            self._current_model_path = None
            self._started_at = None

        return ServerStatus(running=False, port=self.config.port)

    async def restart(self, wait_ready: bool = True, timeout: int = 120) -> ServerStatus:
        """
        Restart server with the same model

        Returns:
            ServerStatus with restart result
        """
        if not self._current_model_path:
            return ServerStatus(
                running=False,
                error="No model was previously loaded",
                port=self.config.port
            )

        model_path = self._current_model_path
        model_name = self._current_model

        await self.stop()
        return await self.start(model_path, model_name, wait_ready, timeout)

    async def switch_model(
        self,
        model_path: str,
        model_name: Optional[str] = None,
        timeout: int = 120
    ) -> ServerStatus:
        """
        Switch to a different model

        This stops the current server and starts with the new model.

        Args:
            model_path: Path to the new GGUF model
            model_name: Optional friendly name
            timeout: Startup timeout in seconds

        Returns:
            ServerStatus with switch result
        """
        logger.info(f"Switching model to: {model_path}")
        return await self.start(model_path, model_name, wait_ready=True, timeout=timeout)


# Singleton instance
_server_instance: Optional[LlamaCppServer] = None


def get_llamacpp_server() -> LlamaCppServer:
    """Get the singleton server instance"""
    global _server_instance
    if _server_instance is None:
        _server_instance = LlamaCppServer()
    return _server_instance


__all__ = [
    "LlamaCppServer",
    "ServerStatus",
    "get_llamacpp_server",
]
