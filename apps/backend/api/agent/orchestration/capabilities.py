"""
Agent Orchestration - Capabilities Detection

Engine capability checking and feature detection:
- Aider availability and version
- Continue CLI availability
- Codex (builtin)
- Ollama availability
- Feature flags (unified_context, bash_intelligence, etc.)

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

from .models import EngineCapability, CapabilitiesResponse


def get_capabilities_logic() -> CapabilitiesResponse:
    """
    Get agent system capabilities and engine availability.

    Detects:
    - Aider in venv (via --version)
    - Continue CLI on PATH
    - Codex (always available)
    - Ollama CLI

    Returns:
        CapabilitiesResponse with engine list and feature flags
    """
    engines = []

    # Check Aider
    aider_available = False
    aider_error = None
    aider_version = None
    aider_remediation = None

    try:
        # Detect venv from sys.executable or climb to project root
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # Running in venv, use current venv
            venv_path = Path(sys.executable).parent.parent
        else:
            # Not in venv, try project root
            project_root = Path(os.getcwd()).parent.parent.parent
            venv_path = project_root / "venv"

        aider_path = venv_path / "bin" / "aider"

        if aider_path.exists():
            result = subprocess.run(
                [str(aider_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                aider_available = True
                aider_version = result.stdout.strip()
        else:
            aider_error = "Aider not found in venv"
            aider_remediation = f"Install Aider: source {venv_path}/bin/activate && pip install aider-chat"
    except Exception as e:
        aider_error = str(e)
        aider_remediation = "Check Aider installation and ensure venv is properly configured"

    engines.append(EngineCapability(
        name="aider",
        available=aider_available,
        version=aider_version,
        error=aider_error,
        remediation=aider_remediation
    ))

    # Check Continue
    continue_available = False
    continue_error = None
    continue_version = None
    continue_remediation = None

    try:
        cn_path = shutil.which("cn") or shutil.which("continue")
        if cn_path:
            result = subprocess.run(
                [cn_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                continue_available = True
                continue_version = result.stdout.strip()
        else:
            continue_error = "Continue CLI not found on PATH"
            continue_remediation = "Install Continue: npm install -g @continuedev/continue"
    except Exception as e:
        continue_error = str(e)
        continue_remediation = "Install Continue CLI or add it to PATH"

    engines.append(EngineCapability(
        name="continue",
        available=continue_available,
        version=continue_version,
        error=continue_error,
        remediation=continue_remediation
    ))

    # Check Codex (always available - uses subprocess/patch)
    engines.append(EngineCapability(
        name="codex",
        available=True,
        version="builtin"
    ))

    # Check Ollama (for bash intelligence)
    ollama_available = False
    ollama_error = None
    ollama_remediation = None

    try:
        if shutil.which("ollama"):
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            ollama_available = result.returncode == 0
        else:
            ollama_error = "Ollama not found on PATH"
            ollama_remediation = "Install Ollama from https://ollama.ai"
    except Exception as e:
        ollama_error = str(e)
        ollama_remediation = "Ensure Ollama is running and accessible"

    engines.append(EngineCapability(
        name="ollama",
        available=ollama_available,
        error=ollama_error,
        remediation=ollama_remediation
    ))

    # Feature flags
    features = {
        "unified_context": True,
        "bash_intelligence": ollama_available,
        "patch_apply": True,
        "dry_run": True,
        "rollback": True,
        "git_integration": shutil.which("git") is not None
    }

    return CapabilitiesResponse(
        engines=engines,
        features=features
    )
