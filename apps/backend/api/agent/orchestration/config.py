"""
Agent Orchestration - Configuration Management

Agent configuration loading, updating, and persistence:
- Load agent.config.yaml
- Update configuration safely
- Reload configuration after changes

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Config file path (relative to agent module)
CONFIG_PATH = Path(__file__).parent.parent / "agent.config.yaml"

# Global config cache
_AGENT_CONFIG: Dict[str, Any] = {}


def load_agent_config() -> Dict[str, Any]:
    """
    Load agent configuration from YAML.

    Returns:
        Dict with agent configuration. Falls back to defaults if file missing.
    """
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded agent config from {CONFIG_PATH}")
                return config
        except Exception as e:
            logger.error(f"Failed to load agent config: {e}")

    # Defaults if config missing
    logger.warning("Using default agent config (agent.config.yaml not found)")
    return {
        "engine_order": ["aider"],  # Aider only by default
        "models": {
            "planner": "ollama/deepseek-r1:8b",
            "coder": "ollama/qwen2.5-coder:32b",
            "committer": "ollama/llama3.1:8b"
        },
        "verify": {"enabled": True, "timeout_sec": 120},
        "commit": {"enabled": True, "branch_strategy": "patch-branches"},
        "security": {"strict_workspace": True}
    }


def get_agent_config() -> Dict[str, Any]:
    """
    Get current agent configuration.

    Returns cached config if available, otherwise loads from file.

    Returns:
        Dict with agent configuration
    """
    global _AGENT_CONFIG
    if not _AGENT_CONFIG:
        _AGENT_CONFIG = load_agent_config()
    return _AGENT_CONFIG


def reload_config() -> Dict[str, Any]:
    """
    Reload configuration from file.

    Forces a fresh load from agent.config.yaml, updating the cache.

    Returns:
        Dict with reloaded configuration
    """
    global _AGENT_CONFIG
    _AGENT_CONFIG = load_agent_config()
    return _AGENT_CONFIG


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update agent configuration and persist to file.

    Args:
        updates: Dict of configuration updates to merge

    Returns:
        Updated configuration dict

    Raises:
        Exception if write fails
    """
    global _AGENT_CONFIG

    # Get current config
    config = get_agent_config().copy()

    # Merge updates (deep merge for nested dicts)
    for key, value in updates.items():
        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
            config[key].update(value)
        else:
            config[key] = value

    # Write to file
    try:
        with open(CONFIG_PATH, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        logger.info(f"Updated agent config: {CONFIG_PATH}")

        # Update cache
        _AGENT_CONFIG = config
        return config
    except Exception as e:
        logger.error(f"Failed to write agent config: {e}")
        raise
