"""
Ollama model initialization.

Handles per-user model storage initialization and model preloading on startup.
"""

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


async def initialize_ollama() -> None:
    """
    Initialize Ollama-related services at startup.

    This includes:
    - Per-user model catalog initialization
    - Model preferences storage setup
    - Hot slots storage setup
    - Model catalog sync from Ollama
    - Auto-load favorite models from per-user hot slots (Phase 1.6)

    Note: Failures in model initialization do not prevent app startup.
    Endpoints will handle missing storage gracefully.
    """
    # Phase 1.5: Initialize per-user model storage
    try:
        from config_paths import PATHS

        # Prefer relative imports when running as a package
        try:
            from api.services.model_catalog import init_model_catalog, get_model_catalog
            from api.services.model_preferences_storage import init_model_preferences_storage
            from api.services.hot_slots_storage import init_hot_slots_storage
        except Exception:
            import sys as _sys
            from pathlib import Path as _Path
            # Ensure 'apps/backend' is on sys.path so 'api.services' is importable
            _sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
            from api.services.model_catalog import init_model_catalog, get_model_catalog
            from api.services.model_preferences_storage import init_model_preferences_storage
            from api.services.hot_slots_storage import init_hot_slots_storage

        # Initialize storage singletons
        init_model_catalog(PATHS.app_db, ollama_base_url="http://localhost:11434")
        init_model_preferences_storage(PATHS.app_db)

        # Determine config directory for legacy JSON
        cfg_dir = getattr(PATHS, 'backend_dir', None)
        if cfg_dir is not None:
            config_dir = cfg_dir / "config"
        else:
            config_dir = PATHS.data_dir
        init_hot_slots_storage(PATHS.app_db, config_dir)

        # Sync model catalog from Ollama on startup
        catalog = get_model_catalog()
        await catalog.sync_from_ollama()

        logger.info("✓ Per-user model storage initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize per-user model storage: {e}")
        # Don't fail startup - endpoints will handle missing storage gracefully
        return

    # Phase 1.6: Auto-load favorite models from per-user hot slots
    try:
        from chat_service import ollama_client
        from api.services.hot_slots_storage import get_hot_slots_storage

        # Step 1: Find preload user (founder first, then first active user)
        preload_user_id = None
        try:
            conn = sqlite3.connect(str(PATHS.app_db))
            cursor = conn.cursor()

            # Try founder user first
            cursor.execute(
                "SELECT user_id FROM users WHERE role='founder_rights' AND is_active=1 LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                preload_user_id = row[0]
                logger.debug(f"Found founder user for preload: {preload_user_id}")
            else:
                # Fallback to first active user
                cursor.execute(
                    "SELECT user_id FROM users WHERE is_active=1 ORDER BY created_at ASC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    preload_user_id = row[0]
                    logger.debug(f"Using first active user for preload: {preload_user_id}")

            conn.close()
        except Exception as db_error:
            logger.debug(f"Could not query preload user: {db_error}")

        # Step 2: Load hot slots from DB or fallback to JSON
        favorites = []

        if preload_user_id:
            # Try per-user hot slots from DB
            try:
                hot_slots_storage = get_hot_slots_storage()
                slots = hot_slots_storage.get_slots(preload_user_id)

                # Extract non-null model names from slots
                favorites = [
                    slots[slot_key]
                    for slot_key in ['slot_1', 'slot_2', 'slot_3', 'slot_4']
                    if slots.get(slot_key)
                ]

                if favorites:
                    logger.info(
                        f"Preloading {len(favorites)} model(s) from per-user hot slots: "
                        f"user_id={preload_user_id}, models={favorites}"
                    )
            except Exception as slot_error:
                logger.debug(f"Could not load per-user hot slots: {slot_error}")

        # Step 3: Fallback to legacy JSON if no DB slots found
        if not favorites:
            json_path = PATHS.data_dir / "model_hot_slots.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        legacy_data = json.load(f)
                        favorites = [
                            legacy_data.get(f'slot_{i}')
                            for i in range(1, 5)
                            if legacy_data.get(f'slot_{i}')
                        ]

                    if favorites:
                        logger.warning(
                            f"Deprecated JSON hot slots used for preload; migrate to per-user hot slots. "
                            f"Models: {favorites}"
                        )
                except Exception as json_error:
                    logger.debug(f"Could not read legacy JSON hot slots: {json_error}")

        # Step 4: Preload models
        if favorites:
            for model_name in favorites:
                try:
                    # Preload model by sending a minimal request
                    # This warms up the model without blocking startup
                    await ollama_client.generate(model_name, prompt="", stream=False)
                    logger.debug(f"✓ Preloaded model: {model_name}")
                except Exception as model_error:
                    # Don't fail startup if a model can't be loaded
                    logger.warning(f"Could not preload model '{model_name}': {model_error}")

            logger.info("✓ Model preloading completed")
        else:
            logger.debug("No per-user hot slots found; skipping startup preload")

    except Exception as e:
        # Don't fail startup if model preloading fails entirely
        logger.warning(f"Model auto-loading disabled: {e}")
