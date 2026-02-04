"""
LSP (Language Server Protocol) Client for MagnetarCode

Manages language server processes and proxies LSP requests.
Supports multiple language servers:
- pyright (Python)
- typescript-language-server (TypeScript/JavaScript)
- rust-analyzer (Rust)
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LSPServer:
    """Represents a running language server process"""

    def __init__(self, language: str, workspace_path: str):
        self.language = language
        self.workspace_path = workspace_path
        self.process: subprocess.Popen | None = None
        self.message_id = 0
        self.pending_requests: dict[int, asyncio.Future] = {}

    async def start(self):
        """Start the language server process"""
        command = self._get_server_command()
        if not command:
            raise ValueError(f"No language server configured for {self.language}")

        logger.info(f"Starting LSP server for {self.language}: {' '.join(command)}")

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.workspace_path,
        )

        # Send initialize request
        await self._initialize()

        # Start reading responses in background
        asyncio.create_task(self._read_responses())

    def _get_server_command(self) -> list[str] | None:
        """Get the command to start the language server"""
        commands = {
            "python": ["pyright-langserver", "--stdio"],
            "typescript": ["typescript-language-server", "--stdio"],
            "javascript": ["typescript-language-server", "--stdio"],
            "rust": ["rust-analyzer"],
            "go": ["gopls"],
        }
        return commands.get(self.language)

    async def _initialize(self):
        """Send initialize request to language server"""
        init_params = {
            "processId": None,
            "clientInfo": {"name": "MagnetarCode", "version": "0.1.0"},
            "rootUri": f"file://{self.workspace_path}",
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": True,
                            "documentationFormat": ["markdown", "plaintext"],
                        }
                    },
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "signatureHelp": {
                        "signatureInformation": {"documentationFormat": ["markdown", "plaintext"]}
                    },
                    "definition": {"linkSupport": True},
                    "references": {},
                    "documentHighlight": {},
                    "documentSymbol": {},
                    "formatting": {},
                    "rangeFormatting": {},
                    "rename": {},
                    "publishDiagnostics": {},
                },
                "workspace": {"workspaceFolders": True, "configuration": True},
            },
            "workspaceFolders": [
                {"uri": f"file://{self.workspace_path}", "name": Path(self.workspace_path).name}
            ],
        }

        result = await self.request("initialize", init_params)

        # Send initialized notification
        await self.notify("initialized", {})

        logger.info(f"LSP server initialized: {result}")

    async def request(self, method: str, params: Any) -> Any:
        """Send a request and wait for response"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server not running")

        self.message_id += 1
        msg_id = self.message_id

        message = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[msg_id] = future

        # Send request
        await self._write_message(message)

        # Wait for response (with timeout)
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            del self.pending_requests[msg_id]
            raise TimeoutError(f"LSP request timed out: {method}")

    async def notify(self, method: str, params: Any):
        """Send a notification (no response expected)"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server not running")

        message = {"jsonrpc": "2.0", "method": method, "params": params}

        await self._write_message(message)

    async def _write_message(self, message: dict[str, Any]):
        """Write a JSON-RPC message to the server"""
        content = json.dumps(message)
        content_bytes = content.encode("utf-8")

        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        self.process.stdin.write(header.encode("utf-8"))
        self.process.stdin.write(content_bytes)
        self.process.stdin.flush()

    async def _read_responses(self):
        """Read responses from the language server"""
        while self.process and self.process.stdout:
            try:
                # Read headers
                headers = {}
                while True:
                    line = self.process.stdout.readline().decode("utf-8").strip()
                    if not line:
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip()] = value.strip()

                # Read content
                content_length = int(headers.get("Content-Length", 0))
                if content_length == 0:
                    continue

                content = self.process.stdout.read(content_length).decode("utf-8")
                message = json.loads(content)

                # Handle response
                if "id" in message:
                    # This is a response to a request
                    msg_id = message["id"]
                    if msg_id in self.pending_requests:
                        future = self.pending_requests.pop(msg_id)
                        if "result" in message:
                            future.set_result(message["result"])
                        elif "error" in message:
                            future.set_exception(Exception(message["error"]))
                elif "method" in message:
                    # This is a notification from server
                    await self._handle_notification(message)

            except Exception as e:
                logger.error(f"Error reading LSP response: {e}")
                break

    async def _handle_notification(self, message: dict[str, Any]):
        """Handle notifications from the language server"""
        method = message.get("method")
        params = message.get("params", {})

        if method == "textDocument/publishDiagnostics":
            # Store diagnostics for this file
            uri = params.get("uri")
            diagnostics = params.get("diagnostics", [])
            logger.info(f"Received {len(diagnostics)} diagnostics for {uri}")
            # TODO: Store diagnostics in memory or database

    async def shutdown(self):
        """Shutdown the language server"""
        if self.process:
            try:
                await self.request("shutdown", {})
                await self.notify("exit", {})
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"LSP shutdown failed, forcing kill: {e}")
                self.process.kill()
            finally:
                self.process = None


class LSPManager:
    """Manages multiple language server instances"""

    def __init__(self):
        self.servers: dict[str, dict[str, LSPServer]] = {}

    async def get_server(self, language: str, workspace_path: str) -> LSPServer:
        """Get or create a language server for the given workspace"""
        workspace_path = str(Path(workspace_path).resolve())

        if language not in self.servers:
            self.servers[language] = {}

        if workspace_path not in self.servers[language]:
            server = LSPServer(language, workspace_path)
            await server.start()
            self.servers[language][workspace_path] = server

        return self.servers[language][workspace_path]

    async def shutdown_all(self):
        """Shutdown all language servers"""
        for language_servers in self.servers.values():
            for server in language_servers.values():
                await server.shutdown()
        self.servers.clear()

    async def completion(
        self,
        language: str,
        workspace_path: str,
        file_path: str,
        line: int,
        character: int,
        text: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get completions at cursor position"""
        server = await self.get_server(language, workspace_path)

        # If text is provided, send didChange notification
        if text is not None:
            await server.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": f"file://{file_path}", "version": 1},
                    "contentChanges": [{"text": text}],
                },
            )

        result = await server.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": character},
            },
        )

        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return result or []

    async def goto_definition(
        self, language: str, workspace_path: str, file_path: str, line: int, character: int
    ) -> dict[str, Any] | None:
        """Go to definition"""
        server = await self.get_server(language, workspace_path)

        result = await server.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": character},
            },
        )

        return result

    async def find_references(
        self, language: str, workspace_path: str, file_path: str, line: int, character: int
    ) -> list[dict[str, Any]]:
        """Find all references"""
        server = await self.get_server(language, workspace_path)

        result = await server.request(
            "textDocument/references",
            {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": True},
            },
        )

        return result or []

    async def hover(
        self, language: str, workspace_path: str, file_path: str, line: int, character: int
    ) -> dict[str, Any] | None:
        """Get hover information"""
        server = await self.get_server(language, workspace_path)

        result = await server.request(
            "textDocument/hover",
            {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": character},
            },
        )

        return result


# Global LSP manager instance
lsp_manager = LSPManager()
