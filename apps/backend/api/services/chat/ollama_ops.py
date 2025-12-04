"""
Chat Ollama Server Operations

Handles Ollama server lifecycle management, configuration, and status monitoring.
"""

import asyncio
import logging
import subprocess
import json
from typing import Dict, Any, List, Optional, AsyncGenerator

logger = logging.getLogger(__name__)


# ========================================================================
# SERVER LIFECYCLE
# ========================================================================

async def get_ollama_server_status() -> Dict[str, Any]:
    """
    Check if Ollama server is running

    Returns:
        Dictionary with running status, loaded_models list, and model_count
    """
    from .core import _get_ollama_client

    ollama_client = _get_ollama_client()

    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ollama_client.base_url}/api/ps")

            if response.status_code == 200:
                data = response.json()
                loaded_models = [model.get("name") for model in data.get("models", [])]

                return {
                    "running": True,
                    "loaded_models": loaded_models,
                    "model_count": len(loaded_models)
                }
            else:
                return {"running": False, "loaded_models": [], "model_count": 0}

    except Exception as e:
        logger.debug(f"Ollama server check failed: {e}")
        return {"running": False, "loaded_models": [], "model_count": 0}


async def shutdown_ollama_server() -> Dict[str, Any]:
    """
    Shutdown Ollama server

    Returns:
        Status dictionary with shutdown confirmation and previously loaded models
    """
    import httpx
    from .core import _get_ollama_client

    ollama_client = _get_ollama_client()

    # Get list of currently loaded models
    loaded_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ollama_client.base_url}/api/ps")
            if response.status_code == 200:
                data = response.json()
                loaded_models = [model.get("name") for model in data.get("models", [])]
    except:
        pass

    # Kill ollama process
    try:
        subprocess.run(["killall", "-9", "ollama"], check=False, capture_output=True)
        logger.info("🔴 Ollama server shutdown requested - all models unloaded")

        return {
            "status": "shutdown",
            "message": "Ollama server stopped successfully",
            "previously_loaded_models": loaded_models,
            "model_count": len(loaded_models)
        }
    except Exception as e:
        logger.error(f"Failed to shutdown Ollama: {e}")
        raise


async def start_ollama_server() -> Dict[str, Any]:
    """
    Start Ollama server in background

    Returns:
        Status dictionary with startup confirmation and process ID

    Raises:
        Exception: If server starts but doesn't respond
    """
    import httpx
    from .core import _get_ollama_client

    ollama_client = _get_ollama_client()

    # Start ollama serve in background
    process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    # Wait a moment for startup
    await asyncio.sleep(2)

    # Check if it started successfully
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{ollama_client.base_url}/api/tags")
            if response.status_code == 200:
                logger.info("🟢 Ollama server started successfully")
                return {
                    "status": "started",
                    "message": "Ollama server started successfully",
                    "pid": process.pid
                }
    except:
        pass

    raise Exception("Ollama server started but not responding. Check logs.")


async def restart_ollama_server(reload_models: bool = False, models_to_load: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Restart Ollama server and optionally reload specific models

    Args:
        reload_models: Whether to reload models after restart
        models_to_load: Specific models to load (if None, uses previously loaded models)

    Returns:
        Dictionary with restart status, PID, and reload results
    """
    import httpx
    from .core import _get_ollama_client

    ollama_client = _get_ollama_client()

    # Get currently loaded models before shutdown
    previous_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ollama_client.base_url}/api/ps")
            if response.status_code == 200:
                data = response.json()
                previous_models = [model.get("name") for model in data.get("models", [])]
    except:
        pass

    # Shutdown first
    subprocess.run(["killall", "-9", "ollama"], check=False, capture_output=True)
    logger.info("🔄 Restarting Ollama server...")

    # Wait a moment
    await asyncio.sleep(1)

    # Start server
    process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    # Wait for startup
    await asyncio.sleep(3)

    # Reload models if requested
    loaded_results = []
    if reload_models:
        models = models_to_load if models_to_load else previous_models

        for model in models:
            try:
                success = await ollama_client.preload_model(model, "1h")
                loaded_results.append({
                    "model": model,
                    "loaded": success
                })
            except Exception as e:
                logger.error(f"Failed to reload model {model}: {e}")
                loaded_results.append({
                    "model": model,
                    "loaded": False,
                    "error": str(e)
                })

    return {
        "status": "restarted",
        "message": "Ollama server restarted successfully",
        "pid": process.pid,
        "models_reloaded": reload_models,
        "reload_results": loaded_results,
        "previously_loaded": previous_models
    }


# ========================================================================
# MODEL MANAGEMENT
# ========================================================================

async def pull_model(model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Pull/download a model from Ollama library with progress streaming

    Args:
        model_name: Name of model to pull (e.g., "qwen2.5-coder:7b")

    Yields:
        Progress updates as JSON dictionaries with status, progress, and completion
    """
    try:
        # Start ollama pull process
        process = await asyncio.create_subprocess_shell(
            f"ollama pull {model_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"📥 Starting model pull: {model_name}")

        # Stream stdout for progress updates
        if process.stdout:
            async for line in process.stdout:
                try:
                    line_str = line.decode('utf-8').strip()
                    if line_str:
                        # Ollama outputs progress lines like:
                        # "pulling manifest"
                        # "pulling sha256:abc123... 100%"
                        # "success"

                        yield {
                            "status": "progress",
                            "message": line_str,
                            "model": model_name
                        }
                except Exception as e:
                    logger.error(f"Error parsing ollama output: {e}")

        # Wait for process to complete
        await process.wait()

        if process.returncode == 0:
            logger.info(f"✅ Model pull completed: {model_name}")
            yield {
                "status": "completed",
                "message": f"Successfully pulled {model_name}",
                "model": model_name
            }
        else:
            stderr = await process.stderr.read() if process.stderr else b""
            error_msg = stderr.decode('utf-8').strip()
            logger.error(f"❌ Model pull failed: {model_name} - {error_msg}")
            yield {
                "status": "error",
                "message": error_msg or "Failed to pull model",
                "model": model_name
            }

    except Exception as e:
        logger.error(f"Exception during model pull: {e}")
        yield {
            "status": "error",
            "message": str(e),
            "model": model_name
        }


async def remove_model(model_name: str) -> Dict[str, Any]:
    """
    Remove/delete a local model

    Args:
        model_name: Name of model to remove (e.g., "qwen2.5-coder:7b")

    Returns:
        Status dictionary with success/failure and message
    """
    try:
        # Run ollama rm command
        process = await asyncio.create_subprocess_shell(
            f"ollama rm {model_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"🗑️  Removing model: {model_name}")

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"✅ Model removed: {model_name}")
            return {
                "status": "success",
                "message": f"Successfully removed {model_name}",
                "model": model_name
            }
        else:
            error_msg = stderr.decode('utf-8').strip()
            logger.error(f"❌ Model removal failed: {model_name} - {error_msg}")
            return {
                "status": "error",
                "message": error_msg or "Failed to remove model",
                "model": model_name
            }

    except Exception as e:
        logger.error(f"Exception during model removal: {e}")
        return {
            "status": "error",
            "message": str(e),
            "model": model_name
        }


async def check_ollama_version() -> Dict[str, Any]:
    """
    Check installed Ollama version

    Returns:
        Dictionary with version info and update availability
    """
    try:
        process = await asyncio.create_subprocess_shell(
            "ollama --version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            version_str = stdout.decode('utf-8').strip()
            logger.info(f"Ollama version: {version_str}")
            return {
                "status": "success",
                "version": version_str,
                "installed": True
            }
        else:
            return {
                "status": "error",
                "message": "Ollama not found or version check failed",
                "installed": False
            }

    except Exception as e:
        logger.error(f"Exception checking Ollama version: {e}")
        return {
            "status": "error",
            "message": str(e),
            "installed": False
        }


# ========================================================================
# CONFIGURATION
# ========================================================================

def get_ollama_configuration() -> Dict[str, Any]:
    """
    Get current Ollama configuration

    Returns:
        Configuration summary dictionary
    """
    from .core import _get_ollama_config

    ollama_config = _get_ollama_config()
    return ollama_config.get_config_summary()


def set_ollama_mode(mode: str) -> Dict[str, Any]:
    """
    Set Ollama performance mode

    Args:
        mode: Performance mode to set

    Returns:
        Status dictionary with mode and configuration details
    """
    from .core import _get_ollama_config

    ollama_config = _get_ollama_config()
    ollama_config.set_mode(mode)
    return {
        "status": "success",
        "mode": mode,
        "config": ollama_config.get_config_summary()
    }


def auto_detect_ollama_config() -> Dict[str, Any]:
    """
    Auto-detect optimal Ollama settings

    Returns:
        Status dictionary with detected optimal configuration
    """
    from .core import _get_ollama_config

    ollama_config = _get_ollama_config()
    optimal_config = ollama_config.detect_optimal_settings()
    ollama_config.config = optimal_config
    ollama_config.save_config()

    return {
        "status": "success",
        "message": "Auto-detected optimal settings",
        "config": ollama_config.get_config_summary()
    }
