"""
Model Validator for MedStation Agent
Validates model availability and provides intelligent defaults
"""

import subprocess
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def get_installed_models() -> List[str]:
    """Get list of installed Ollama models"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            models = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(f"ollama/{model_name}")
            return models
    except Exception as e:
        logger.warning(f"Failed to get Ollama models: {e}")
    return []


def validate_model_exists(model: str, installed: List[str]) -> bool:
    """Check if a model is installed"""
    return model in installed


def get_compatible_models(installed: List[str], task_type: str) -> List[str]:
    """
    Get compatible models for a task type based on naming patterns

    Task types and compatible patterns:
    - orchestrator: Small, fast models (1.5b, 3b)
    - coder: Code-specialized models (coder, code, starcoder)
    - reasoning: Reasoning models (deepseek, r1, thinking)
    - chat: General purpose (gpt, llama, mistral, qwen)
    - data_engine: Only phi3.5 (strict enforcement)
    """
    if task_type == "data_engine":
        # STRICT: Only phi3.5 allowed
        return [m for m in installed if "phi3.5" in m.lower()]

    if task_type == "orchestrator":
        # Small, fast models
        patterns = ["1.5b", "3b", "1b", "base"]
        return [m for m in installed if any(p in m.lower() for p in patterns)]

    if task_type == "coder":
        # Code-specialized
        patterns = ["coder", "code", "starcoder", "codellama"]
        return [m for m in installed if any(p in m.lower() for p in patterns)]

    if task_type == "reasoning":
        # Reasoning models
        patterns = ["deepseek", "r1", "thinking", "reason"]
        return [m for m in installed if any(p in m.lower() for p in patterns)]

    # Default: any model works
    return installed


def auto_select_model(installed: List[str], task_type: str, preferred: Optional[str] = None) -> Optional[str]:
    """
    Auto-select a model for a task

    Priority:
    1. Preferred model (if installed)
    2. First compatible model
    3. First available model
    """
    if preferred and validate_model_exists(preferred, installed):
        return preferred

    compatible = get_compatible_models(installed, task_type)
    if compatible:
        return compatible[0]

    if installed:
        return installed[0]

    return None


def validate_config(config: Dict) -> Dict:
    """
    Validate agent config and provide intelligent defaults

    Returns:
    {
        "valid": bool,
        "errors": List[str],
        "warnings": List[str],
        "suggested_fixes": Dict[str, str]
    }
    """
    installed = get_installed_models()
    errors = []
    warnings = []
    suggested_fixes = {}

    # CRITICAL: Data engine MUST be phi3.5
    data_engine = config.get("strict_models", {}).get("data_engine")
    if not data_engine or "phi3.5" not in data_engine.lower():
        errors.append("Data engine must be phi3.5:3.8b for SQL reliability")
        phi_models = get_compatible_models(installed, "data_engine")
        if phi_models:
            suggested_fixes["data_engine"] = phi_models[0]
        else:
            errors.append("CRITICAL: phi3.5 not installed. Run: ollama pull phi3.5:3.8b")
    elif not validate_model_exists(data_engine, installed):
        errors.append(f"Data engine model not installed: {data_engine}")
        suggested_fixes["data_engine"] = "ollama pull phi3.5:3.8b"

    # Check orchestrator model
    orch_model = config.get("orchestrator", {}).get("model")
    if orch_model and not validate_model_exists(orch_model, installed):
        warnings.append(f"Orchestrator model not installed: {orch_model}")
        auto_orch = auto_select_model(installed, "orchestrator")
        if auto_orch:
            suggested_fixes["orchestrator"] = auto_orch

    # Check user preferences (if orchestrator disabled)
    if not config.get("orchestrator", {}).get("enabled", True):
        prefs = config.get("user_model_preferences", {})
        for task, model in prefs.items():
            if model and not validate_model_exists(model, installed):
                warnings.append(f"Model for {task} not installed: {model}")
                auto_model = auto_select_model(installed, task)
                if auto_model:
                    suggested_fixes[f"user_pref_{task}"] = auto_model

    # Check if ANY models available
    if not installed:
        errors.append("CRITICAL: No Ollama models installed")
        errors.append("Install at least one model: ollama pull qwen2.5-coder:7b")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggested_fixes": suggested_fixes,
        "installed_count": len(installed),
        "installed_models": installed
    }


def get_setup_instructions() -> Dict:
    """Get setup instructions for first-time users"""
    return {
        "required": {
            "phi3.5:3.8b": {
                "command": "ollama pull phi3.5:3.8b",
                "reason": "Required for SQL data engine",
                "size": "2.2 GB"
            }
        },
        "recommended": {
            "qwen2.5-coder:7b": {
                "command": "ollama pull qwen2.5-coder:7b",
                "reason": "Excellent for code generation",
                "size": "4.7 GB"
            },
            "deepseek-r1:8b": {
                "command": "ollama pull deepseek-r1:8b",
                "reason": "Best for reasoning tasks",
                "size": "5.2 GB"
            }
        },
        "optional": {
            "qwen2.5-coder:1.5b": {
                "command": "ollama pull qwen2.5-coder:1.5b",
                "reason": "Fast for quick fixes",
                "size": "986 MB"
            }
        }
    }
