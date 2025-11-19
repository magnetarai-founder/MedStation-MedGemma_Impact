"""
Agent Orchestration - Model Settings Management

Model configuration management:
- Get models overview (orchestrator status, preferences, available models)
- Update model settings (orchestrator toggle, user preferences)
- Validate model configuration
- Auto-fix model configuration with intelligent defaults

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
import subprocess
from typing import Dict, Any
from pathlib import Path

try:
    from .config import get_agent_config, update_config, reload_config, CONFIG_PATH
except ImportError:
    from config import get_agent_config, update_config, reload_config, CONFIG_PATH

logger = logging.getLogger(__name__)


def get_models_overview(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get model configuration and orchestrator status.

    Args:
        cfg: Agent configuration dict

    Returns:
        Dict with:
        - orchestrator: {enabled: bool, model: str}
        - user_preferences: Models selected per task
        - recommended_models: Tested models per task type
        - strict_models: Enforced models
        - available_models: All Ollama models on system
        - note: Usage instructions
    """
    # Get available Ollama models
    available_models = []
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]  # First column is model name
                    available_models.append(f"ollama/{model_name}")
    except Exception as e:
        logger.warning(f"Failed to get Ollama models: {e}")

    return {
        "orchestrator": cfg.get("orchestrator", {"enabled": True, "model": "ollama/qwen2.5-coder:1.5b-base"}),
        "user_preferences": cfg.get("user_model_preferences", {}),
        "recommended_models": cfg.get("recommended_models", {}),
        "strict_models": cfg.get("strict_models", {}),
        "available_models": available_models,
        "note": "When orchestrator is enabled, it automatically selects models. When disabled, you choose per task."
    }


def update_model_settings_logic(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update model settings and orchestrator configuration.

    Args:
        body: Dict with optional:
            - orchestrator.enabled: bool (toggle intelligent routing)
            - user_preferences: dict (task-specific model selections)

    Returns:
        Dict with:
        - success: bool
        - message: str
        - orchestrator: updated config
        - user_preferences: updated preferences

    Raises:
        Exception if config file not found or write fails
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Config file not found")

    # Load current config
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    # Update orchestrator if provided
    if "orchestrator" in body:
        if "enabled" in body["orchestrator"]:
            config["orchestrator"]["enabled"] = body["orchestrator"]["enabled"]

    # Update user preferences if provided
    if "user_preferences" in body:
        if "user_model_preferences" not in config:
            config["user_model_preferences"] = {}
        config["user_model_preferences"].update(body["user_preferences"])

    # Write updated config
    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    # Reload config in memory
    reload_config()

    logger.info("Model settings updated")

    return {
        "success": True,
        "message": "Model settings updated successfully",
        "orchestrator": config.get("orchestrator"),
        "user_preferences": config.get("user_model_preferences")
    }


def validate_models_logic(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate model configuration and provide setup guidance.

    Args:
        cfg: Agent configuration dict

    Returns:
        Dict with validation status, errors, warnings, setup_instructions
    """
    try:
        # Try to import model_validator from agent module
        try:
            from ..model_validator import validate_config, get_setup_instructions
        except ImportError:
            from model_validator import validate_config, get_setup_instructions
    except ImportError:
        # Model validator not available, return basic validation
        return {
            "valid": True,
            "warnings": ["Model validator module not available"],
            "setup_instructions": {}
        }

    validation = validate_config(cfg)
    setup = get_setup_instructions()

    return {
        **validation,
        "setup_instructions": setup
    }


def auto_fix_models_logic(current_user: Dict) -> Dict[str, Any]:
    """
    Automatically fix model configuration using intelligent defaults.

    This will:
    1. Auto-select compatible models for each task
    2. Update agent.config.yaml with working models
    3. Validate the fixes

    Args:
        current_user: User dict (for logging)

    Returns:
        Dict with:
        - success: bool
        - fixes_applied: dict of fixes
        - validation: validation result

    Raises:
        ValueError if no Ollama models installed
        Exception if update fails
    """
    try:
        # Try to import model_validator from agent module
        try:
            from ..model_validator import validate_config, auto_select_model, get_installed_models
        except ImportError:
            from model_validator import validate_config, auto_select_model, get_installed_models
    except ImportError:
        raise ImportError("Model validator module not available for auto-fix")

    installed = get_installed_models()
    if not installed:
        raise ValueError("No Ollama models installed. Please install at least one model first.")

    # Load current config
    import yaml
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    fixes_applied = {}

    # Auto-fix orchestrator
    orch_model = auto_select_model(installed, "orchestrator")
    if orch_model:
        config["orchestrator"]["model"] = orch_model
        fixes_applied["orchestrator"] = orch_model

    # Auto-fix user preferences
    prefs = config.get("user_model_preferences", {})
    for task in prefs.keys():
        auto_model = auto_select_model(installed, task)
        if auto_model:
            prefs[task] = auto_model
            fixes_applied[f"user_pref_{task}"] = auto_model

    # Write updated config
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    # Reload
    reload_config()

    # Validate after fixes
    cfg = get_agent_config()
    validation = validate_config(cfg)

    logger.info(f"Auto-fixed models by {current_user.get('username', 'unknown')}: {fixes_applied}")

    return {
        "success": True,
        "fixes_applied": fixes_applied,
        "validation": validation
    }
