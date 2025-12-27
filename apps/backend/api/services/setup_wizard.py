"""
Setup Wizard Service

"The Lord is my rock and fortress" - Psalm 18:2

Comprehensive first-run setup wizard for ElohimOS with:
- User account creation (local-only super_admin)
- Ollama detection and installation guidance
- Model recommendations based on system resources
- Model download progress tracking
- Hot slot configuration (1-4 favorite models)
- Database initialization

This extends the existing FounderSetupWizard to provide a complete
onboarding experience for new users.

Architecture:
- Builds on top of founder_setup_wizard.py (founder password)
- Uses recommended_models.json for model recommendations
- Integrates with model_manager.py for hot slots
- Creates local super_admin account (no team)
- Offline-first: all setup happens locally

Phase 1 Implementation:
- Consolidates existing founder_setup functionality
- Adds Ollama detection and model management
- User-driven configuration (no hardcoded defaults)
"""

import json
import logging
import platform
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import httpx

try:
    from api.config import get_settings
except ImportError:
    from config import get_settings

logger = logging.getLogger(__name__)


class SetupWizardService:
    """
    First-run setup wizard for ElohimOS

    Handles:
    - Ollama detection and installation guidance
    - System resource detection (RAM, disk space)
    - Model recommendations based on system tier
    - Model downloads with progress tracking
    - Hot slot configuration (1-4 favorite models)
    - Local account creation (integrated with founder_setup)

    Usage:
        wizard = SetupWizardService()

        # Check Ollama
        ollama_status = await wizard.check_ollama_status()

        # Get recommended models
        recommendations = await wizard.load_model_recommendations()

        # Download model
        await wizard.download_model("qwen2.5-coder:7b-instruct", callback)

        # Configure hot slots
        await wizard.configure_hot_slots({1: "gpt-oss:20b", 2: "qwen2.5-coder:14b"})
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize setup wizard

        Args:
            config_path: Path to recommended_models.json (auto-detected if None)
        """
        if config_path is None:
            # Auto-detect config file
            try:
                from config_paths import get_config_paths
                paths = get_config_paths()
                config_path = paths.api_dir / "config" / "recommended_models.json"
            except ImportError:
                # Fallback to relative path
                config_path = Path(__file__).parent.parent / "config" / "recommended_models.json"

        self.config_path = config_path
        self.ollama_base_url = get_settings().ollama_base_url

        # Platform detection
        self.platform = platform.system()  # Darwin, Linux, Windows

    # ========================================================================
    # Ollama Detection
    # ========================================================================

    async def check_ollama_status(self) -> Dict[str, Any]:
        """
        Detect Ollama installation and service status

        Checks:
        1. Binary existence (ollama command available)
        2. Service running (localhost:11434 responding)
        3. Version information

        Returns:
            OllamaStatus dict:
            {
                "installed": bool,
                "running": bool,
                "version": str | None,
                "base_url": str,
                "install_instructions": dict
            }
        """
        status = {
            "installed": False,
            "running": False,
            "version": None,
            "base_url": self.ollama_base_url,
            "install_instructions": self._get_install_instructions()
        }

        # Check if binary exists
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                status["installed"] = True
                # Parse version (format: "ollama version is X.Y.Z")
                version_line = result.stdout.strip()
                if "version" in version_line:
                    status["version"] = version_line.split()[-1]
                    logger.info(f"✅ Ollama installed: {status['version']}")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.info(f"ℹ️ Ollama binary not found: {e}")

        # Check if service is running
        if status["installed"]:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(f"{self.ollama_base_url}/api/tags")
                    if response.status_code == 200:
                        status["running"] = True
                        logger.info("✅ Ollama service is running")
            except Exception as e:
                logger.info(f"ℹ️ Ollama service not running: {e}")

        return status

    def _get_install_instructions(self) -> Dict[str, str]:
        """
        Get platform-specific Ollama installation instructions

        Returns:
            Dict with installation method, command, and service start
        """
        # Load from recommended_models.json if available
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    install_guide = config.get("ollama_install_guide", {})

                    if self.platform == "Darwin":
                        return install_guide.get("macos", {})
                    elif self.platform == "Linux":
                        return install_guide.get("linux", {})
                    elif self.platform == "Windows":
                        return install_guide.get("windows", {})
        except Exception as e:
            logger.warning(f"Could not load install instructions: {e}")

        # Fallback instructions
        return {
            "method": "manual",
            "url": "https://ollama.com/download",
            "command": "See https://ollama.com/download for instructions"
        }

    # ========================================================================
    # System Resources
    # ========================================================================

    async def detect_system_resources(self) -> Dict[str, Any]:
        """
        Detect system RAM and available disk space

        Returns:
            SystemResources dict:
            {
                "ram_gb": int,
                "disk_free_gb": int,
                "recommended_tier": str (essential|balanced|power_user),
                "tier_info": dict
            }
        """
        # Get RAM
        ram_bytes = psutil.virtual_memory().total
        ram_gb = int(ram_bytes / (1024 ** 3))

        # Get disk space (current directory)
        disk_usage = psutil.disk_usage('/')
        disk_free_gb = int(disk_usage.free / (1024 ** 3))

        # Determine recommended tier
        if ram_gb >= 32:
            tier = "power_user"
        elif ram_gb >= 16:
            tier = "balanced"
        else:
            tier = "essential"

        # Load tier info from config
        tier_info = {}
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    tiers = config.get("tiers", {})
                    if tier in tiers:
                        tier_info = tiers[tier]
        except Exception as e:
            logger.warning(f"Could not load tier info: {e}")

        logger.info(f"💻 System resources: {ram_gb}GB RAM, {disk_free_gb}GB disk free → {tier} tier")

        return {
            "ram_gb": ram_gb,
            "disk_free_gb": disk_free_gb,
            "recommended_tier": tier,
            "tier_info": tier_info
        }

    # ========================================================================
    # Model Recommendations
    # ========================================================================

    async def load_model_recommendations(self, tier: Optional[str] = None) -> Dict[str, Any]:
        """
        Load recommended models from config file

        Args:
            tier: Specific tier to load (essential|balanced|power_user)
                  If None, auto-detects based on system resources

        Returns:
            ModelRecommendations dict:
            {
                "tier": str,
                "models": List[dict],
                "hot_slot_recommendations": dict,
                "total_size_gb": float
            }
        """
        # Auto-detect tier if not provided
        if tier is None:
            resources = await self.detect_system_resources()
            tier = resources["recommended_tier"]

        # Load config
        if not self.config_path.exists():
            logger.error(f"❌ Config file not found: {self.config_path}")
            return {
                "tier": tier,
                "models": [],
                "hot_slot_recommendations": {},
                "total_size_gb": 0.0
            }

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Get tier data
            tiers = config.get("tiers", {})
            tier_data = tiers.get(tier, {})

            models = tier_data.get("models", [])

            # Get hot slot recommendations
            hot_slot_recs = config.get("hot_slot_recommendations", {})
            tier_hot_slots = hot_slot_recs.get(tier, {})

            # Calculate total size
            total_size_gb = sum(m.get("size_gb", 0) for m in models)

            logger.info(f"📋 Loaded {len(models)} recommended models for {tier} tier ({total_size_gb:.1f}GB total)")

            return {
                "tier": tier,
                "models": models,
                "hot_slot_recommendations": tier_hot_slots,
                "total_size_gb": total_size_gb
            }

        except Exception as e:
            logger.error(f"❌ Failed to load model recommendations: {e}")
            return {
                "tier": tier,
                "models": [],
                "hot_slot_recommendations": {},
                "total_size_gb": 0.0
            }

    # ========================================================================
    # Model Downloads
    # ========================================================================

    async def download_model(
        self,
        model_name: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Download a model via Ollama

        Args:
            model_name: Ollama model name (e.g., "qwen2.5-coder:7b-instruct")
            progress_callback: Optional callback(progress_pct: float, status: str)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"⬇️ Downloading model: {model_name}")

        try:
            # Use Ollama CLI to pull model
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output and parse progress
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break

                line = line.strip()
                logger.debug(f"Ollama: {line}")

                # Parse progress (Ollama outputs percentage)
                if "%" in line:
                    try:
                        # Extract percentage (format: "pulling... 45%")
                        percent_str = line.split("%")[0].split()[-1]
                        progress_pct = float(percent_str)

                        if progress_callback:
                            progress_callback(progress_pct, f"Downloading {model_name}")
                    except (ValueError, IndexError):
                        pass  # Progress parsing failed, continue

                # Status updates
                if "success" in line.lower() or "already" in line.lower():
                    if progress_callback:
                        progress_callback(100.0, f"Downloaded {model_name}")

            process.wait()

            if process.returncode == 0:
                logger.info(f"✅ Model downloaded successfully: {model_name}")
                return True
            else:
                logger.error(f"❌ Model download failed: {model_name} (exit code {process.returncode})")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to download model {model_name}: {e}")
            return False

    async def get_installed_models(self) -> List[Dict[str, Any]]:
        """
        Get list of installed Ollama models

        Returns:
            List of model dicts with name, size, modified_at
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    logger.info(f"📦 Found {len(models)} installed models")
                    return models
                else:
                    logger.warning(f"⚠️ Failed to get models: HTTP {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"❌ Failed to get installed models: {e}")
            return []

    # ========================================================================
    # Hot Slots Configuration
    # ========================================================================

    async def configure_hot_slots(self, slots: Dict[int, str]) -> bool:
        """
        Configure hot slots (1-4 favorite models)

        Args:
            slots: Dict mapping slot number (1-4) to model name
                   Example: {1: "gpt-oss:20b", 2: "qwen2.5-coder:14b"}

        Returns:
            True if successful, False otherwise
        """
        try:
            from model_manager import ModelManager

            manager = ModelManager()

            # Assign each slot
            for slot_num, model_name in slots.items():
                if slot_num not in [1, 2, 3, 4]:
                    logger.warning(f"⚠️ Invalid slot number: {slot_num} (must be 1-4)")
                    continue

                if model_name is None:
                    # Remove from slot
                    manager.remove_from_slot(slot_num)
                else:
                    # Assign to slot
                    success = manager.assign_to_slot(slot_num, model_name)
                    if success:
                        logger.info(f"✅ Assigned '{model_name}' to hot slot {slot_num}")
                    else:
                        logger.error(f"❌ Failed to assign '{model_name}' to slot {slot_num}")
                        return False

            return True

        except Exception as e:
            logger.error(f"❌ Failed to configure hot slots: {e}")
            return False

    # ========================================================================
    # Account Creation (integrates with founder_setup)
    # ========================================================================

    async def create_local_account(
        self,
        username: str,
        password: str,
        founder_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create local super_admin account

        This integrates with the existing FounderSetupWizard to:
        1. Initialize founder password (if provided and not already setup)
        2. Create local super_admin user account
        3. Mark setup as completed

        Args:
            username: Username for local account
            password: Password for local account
            founder_password: Optional founder password (for founder_rights setup)

        Returns:
            Result dict with user_id, success, error
        """
        try:
            from founder_setup_wizard import get_founder_wizard
            from auth_middleware import auth_service

            result = {
                "success": False,
                "user_id": None,
                "error": None,
                "founder_setup_complete": False
            }

            # If founder password provided and not already setup, initialize it
            wizard = get_founder_wizard()
            if founder_password and not wizard.is_setup_complete():
                founder_result = wizard.setup_founder_password(
                    password=founder_password,
                    user_id="setup_wizard"
                )

                if not founder_result["success"]:
                    result["error"] = f"Founder setup failed: {founder_result.get('error')}"
                    return result

                result["founder_setup_complete"] = True

            # Create local super_admin account
            # Check if user already exists
            existing_user = auth_service.get_user_by_username(username)
            if existing_user:
                result["error"] = "Username already exists"
                return result

            # Create user with super_admin role (local-only)
            user = auth_service.create_user(
                username=username,
                password=password,
                role="super_admin"  # Default role for local users
            )

            if user:
                result["success"] = True
                result["user_id"] = user["user_id"]
                logger.info(f"✅ Created local super_admin account: {username}")
            else:
                result["error"] = "Failed to create user account"

            return result

        except Exception as e:
            logger.error(f"❌ Failed to create local account: {e}")
            return {
                "success": False,
                "user_id": None,
                "error": str(e),
                "founder_setup_complete": False
            }

    # ========================================================================
    # Complete Setup
    # ========================================================================

    async def complete_setup(self) -> bool:
        """
        Mark setup wizard as completed

        This is called after all setup steps are finished.
        Uses the existing founder_setup table.

        Returns:
            True if successful, False otherwise
        """
        try:
            from founder_setup_wizard import get_founder_wizard

            wizard = get_founder_wizard()

            # Check if already completed
            if wizard.is_setup_complete():
                logger.info("ℹ️ Setup already marked as complete")
                return True

            # Note: founder_setup.setup_completed is set when founder password is configured
            # For users who don't set founder password during setup, we need a separate flag
            # For now, we'll rely on the founder_setup table

            logger.info("✅ Setup wizard completed")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to complete setup: {e}")
            return False


# ===== Singleton Instance =====

_setup_wizard: Optional[SetupWizardService] = None


def get_setup_wizard() -> SetupWizardService:
    """Get singleton setup wizard instance"""
    global _setup_wizard
    if _setup_wizard is None:
        _setup_wizard = SetupWizardService()
    return _setup_wizard


# Export
__all__ = [
    'SetupWizardService',
    'get_setup_wizard'
]
